"""Gardien : boucle du veilleur, réconciliation, stop-loss, réveils, exécution, mort."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from . import config as C
from . import rules
from .agent import AgentError, build_context, hold_decision, parse_decision
from .api import Mailbox
from .bitvavo import BitvavoClient, BitvavoError
from .state import Journal, Position, State, TrackedOrder, iso, parse_iso, utcnow
from .validator import ProposedOrder, validate

log = logging.getLogger("guardian")

STOP_ORDER_REPRICE_SECONDS = 300
PRIORITY_TRIGGERS = {"danger_zone", "stop_hit"}


class Halt(Exception):
    """Levée pour sortir proprement de la boucle."""


class Guardian:
    def __init__(self, settings: C.Settings, client: BitvavoClient, state: State, journal: Journal,
                 mailbox: Mailbox):
        self.s = settings
        self.client = client
        self.state = state
        self.journal = journal
        self.mailbox = mailbox
        self.markets: dict[str, dict] = {}
        self.prices: dict[str, Decimal] = {}
        self.eur: Decimal = Decimal("0")
        self._pending_dilemma_wake = False
        self._wake_opened_at: datetime | None = None
        self._wake_trigger: str = ""

    # ================================================================ démarrage
    def startup_checks(self) -> None:
        skew = abs(self.client.server_time_ms() - int(time.time() * 1000))
        if skew > 2000:
            raise SystemExit(f"Décalage d'horloge {skew} ms > 2 s : corriger NTP")
        self.markets = self.client.markets()
        for pair in self.s.whitelist:
            if pair not in self.markets:
                raise SystemExit(f"Paire inconnue sur Bitvavo : {pair}")
        balances = self.client.balances()
        self.eur = balances.get("EUR", Decimal("0"))
        self._adopt_initial_holdings(balances)
        self._reconcile_positions(balances)
        log.info("Démarrage OK — mode=%s EUR=%.2f positions=%d", self.s.mode, self.eur, len(self.state.positions))

    def _adopt_initial_holdings(self, balances: dict[str, Decimal]) -> None:
        """État neuf (aucun tick, position ni ordre) : reprend les cryptos déjà détenues, stop standard."""
        st = self.state
        if st.positions or st.open_orders or st.last_metabolism_date:
            return
        prices = self.client.ticker_prices(self.s.whitelist)
        stop_pct = rules.current_tier(st).stop_pct
        for pair in self.s.whitelist:
            held = balances.get(pair.split("-")[0], Decimal("0"))
            price = prices.get(pair, Decimal("0"))
            if held * price < C.ADOPT_MIN_EUR:
                continue
            st.positions.append(Position(pair, str(held), str(price),
                                         str((price * (1 - stop_pct)).quantize(Decimal("0.00000001"))),
                                         iso(utcnow())).__dict__)
            self.journal.write("startup", st.score, "-", "adopt_holding", pair, str(held), "-",
                               f"entry={price} valeur={held * price:.2f} EUR")

    def _reconcile_positions(self, balances: dict[str, Decimal]) -> None:
        prices = self.client.ticker_prices(self.s.whitelist)
        for p in self.state.position_objs():
            base = p.pair.split("-")[0]
            held = balances.get(base, Decimal("0"))
            diff_eur = abs(held - p.qty_d) * prices.get(p.pair, Decimal("0"))
            if diff_eur > Decimal("1"):
                self.journal.write("startup", self.state.score, "-", "reconcile_fail", p.pair, str(held), "-",
                                   f"état={p.qty} solde={held} écart={diff_eur:.2f} EUR")
                raise SystemExit(f"Divergence {p.pair} : état {p.qty} vs solde {held}. Arrêt.")

    # ================================================================ boucle
    def run(self) -> None:
        if self.s.mode == "halt":
            self._cancel_all_open_orders("halt")
            raise Halt("mode halt")
        while True:
            started = time.monotonic()
            try:
                self.tick()
            except Halt:
                self.state.save(self.s.state_path)
                raise
            except (BitvavoError, OSError) as exc:
                log.warning("Tick échoué (réessai au prochain) : %s", exc)
            finally:
                self.state.save(self.s.state_path)
            time.sleep(max(1, self.s.tick_seconds - (time.monotonic() - started)))

    def tick(self) -> None:
        now = utcnow()
        self.prices = self.client.ticker_prices(self.s.whitelist)
        balances = self.client.balances()
        self.eur = balances.get("EUR", Decimal("0"))

        self._reconcile_orders(now)
        self._daily_rollover(now)
        self.state.set_score(rules.capital_score(self.eur, self.state, self.prices))

        if self.state.score < C.DEATH_THRESHOLD:
            self._die()
        if self.state.victory:
            self.journal.write("tick", self.state.score, "-", "VICTORY")
            self._cancel_all_open_orders("victory")
            raise Halt("victoire")

        self._check_stops(now)
        self._check_daily_loss(now)
        self._update_danger_flag()

        self._process_decisions(now)
        self._check_wake_timeout(now)

        if not self.mailbox.current_wake():
            trigger = self._pick_trigger(now)
            if trigger and self._wake_allowed(now, trigger):
                self._open_wake(trigger, now)

    # ================================================================ réconciliation des ordres
    def _reconcile_orders(self, now: datetime) -> None:
        remaining: list[dict] = []
        for o in self.state.order_objs():
            if o.order_id.startswith("dry-"):
                continue  # dry_run : jamais envoyé
            try:
                info = self.client.get_order(o.pair, o.order_id)
            except BitvavoError as exc:
                log.warning("get_order %s : %s", o.order_id, exc)
                remaining.append(o.__dict__)
                continue
            status = info.get("status", "")
            filled = Decimal(str(info.get("filledAmount", "0")))
            filled_quote = Decimal(str(info.get("filledAmountQuote", "0")))
            age = now - parse_iso(o.placed_at)

            if status in ("filled", "canceled", "cancelled", "expired", "rejected"):
                if filled > 0:
                    self._apply_fill(o, filled, filled_quote)
                self.journal.write("tick", self.state.score, "-", f"order_{status}", o.pair, str(filled), "-", o.reason)
                continue

            # Stop-loss / mort : rechasser le bid si non rempli après 5 min
            if o.reason in ("stop_loss", "death") and age.total_seconds() > STOP_ORDER_REPRICE_SECONDS:
                self._cancel(o, "reprice")
                if filled > 0:
                    self._apply_fill(o, filled, filled_quote)
                self._place_sell_at_bid(o.pair, o.reason)
                continue

            # Limit du bot non rempli après 6 h : annulé
            if o.reason == "agent" and age > timedelta(hours=C.LIMIT_ORDER_TTL_HOURS):
                self._cancel(o, "ttl_6h")
                if filled > 0:
                    self._apply_fill(o, filled, filled_quote)
                continue

            remaining.append(o.__dict__)
        self.state.open_orders = remaining

    def _apply_fill(self, o: TrackedOrder, filled: Decimal, filled_quote: Decimal) -> None:
        positions = self.state.position_objs()
        pos = next((p for p in positions if p.pair == o.pair), None)
        avg_price = (filled_quote / filled) if filled else Decimal(o.price)
        if o.side == "buy":
            stop_pct = Decimal(o.stop_pct or rules.current_tier(self.state).stop_pct)
            if pos:
                total_qty = pos.qty_d + filled
                entry = (pos.qty_d * pos.entry_d + filled * avg_price) / total_qty
                pos.qty, pos.entry = str(total_qty), str(entry)
                pos.stop = str((entry * (1 - stop_pct)).quantize(Decimal("0.00000001")))
            else:
                positions.append(Position(o.pair, str(filled), str(avg_price),
                                          str((avg_price * (1 - stop_pct)).quantize(Decimal("0.00000001"))), iso(utcnow())))
        else:
            if pos:
                pos.qty = str(pos.qty_d - filled)
                if pos.qty_d <= Decimal("0.00000001"):
                    positions.remove(pos)
        self.state.positions = [p.__dict__ for p in positions]
        self.state.last_activity_date = utcnow().strftime("%Y-%m-%d")

    # ================================================================ journée
    def _daily_rollover(self, now: datetime) -> None:
        rules.expire_dilemma(self.state, now)
        amount = rules.apply_daily_metabolism(self.state, now)
        if amount is None:
            return
        self.state.set_score(rules.capital_score(self.eur, self.state, self.prices))
        self.journal.write("daily", self.state.score, "-", "metabolism", "-", f"{amount:.4f}", "-",
                           f"taux {Decimal(self.state.metabolism_rate) * 100:.2f} %")
        for ev in rules.check_milestones(self.state, now):
            self.journal.write("daily", self.state.score, "-", ev)
            self._pending_dilemma_wake = True  # un palier atteint/manqué justifie un réveil
        self.state.day_start_score = self.state.capital_score
        self.state.purchases_frozen_until = None
        d = rules.maybe_draw_dilemma(self.state, now)
        if d:
            self.journal.write("daily", self.state.score, "-", "dilemma", "-", str(d["id"]), "-", d["label"])
            self._pending_dilemma_wake = True
            if d.get("force_close_one") and not self.state.positions:
                self.state.active_dilemma = None  # rien à fermer : dilemme sans objet

    # ================================================================ protections
    def _check_stops(self, now: datetime) -> None:
        pending_sells = {o.pair for o in self.state.order_objs() if o.side == "sell"}
        for p in self.state.position_objs():
            price = self.prices.get(p.pair)
            if price is None or p.pair in pending_sells:
                continue
            if price <= p.stop_d:
                self.journal.write("tick", self.state.score, "-", "stop_hit", p.pair, p.qty, "-",
                                   f"prix {price} <= stop {p.stop_d}")
                self._place_sell_at_bid(p.pair, "stop_loss")
                self.state.last_stop_hit_pending = True

    def _check_daily_loss(self, now: datetime) -> None:
        if self.state.purchases_frozen_until:
            return
        floor = Decimal(self.state.day_start_score) * (1 - C.DAILY_LOSS_FREEZE)
        if self.state.score < floor:
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            self.state.purchases_frozen_until = iso(tomorrow)
            self.journal.write("tick", self.state.score, "-", "purchases_frozen", "-", "-", "-",
                               f"score {self.state.score} < {floor:.2f}")

    def _update_danger_flag(self) -> None:
        if self.state.score >= C.DANGER_THRESHOLD:
            self.state.in_danger = False

    # ================================================================ réveils
    def _pick_trigger(self, now: datetime) -> str | None:
        st = self.state
        if st.score < C.DANGER_THRESHOLD and not st.in_danger:
            st.in_danger = True
            return "danger_zone"
        if st.last_stop_hit_pending:
            st.last_stop_hit_pending = False
            return "stop_hit"
        if self._pending_dilemma_wake:
            self._pending_dilemma_wake = False
            return "dilemma_start"
        for p in st.position_objs():
            ref = st.last_decision_prices.get(p.pair)
            px = self.prices.get(p.pair)
            if ref and px and abs(px / Decimal(ref) - 1) >= C.POSITION_MOVE_TRIGGER:
                return "position_move"
        slot = now.strftime("%Y-%m-%dT%H")
        if now.hour in C.SCHEDULED_WAKE_HOURS and st.last_scheduled_wake != slot:
            st.last_scheduled_wake = slot
            return "scheduled"
        if rules.milestone_is_near(st, now):
            last = parse_iso(st.last_milestone_wake) if st.last_milestone_wake else None
            if not last or now - last > timedelta(hours=6):
                st.last_milestone_wake = iso(now)
                return "milestone_near"
        return None

    def _wake_allowed(self, now: datetime, trigger: str) -> bool:
        cutoff = now - timedelta(hours=24)
        self.state.wakes = [w for w in self.state.wakes if parse_iso(w) > cutoff]
        if trigger in PRIORITY_TRIGGERS or len(self.state.wakes) < C.WAKE_CAP_24H:
            return True
        self.journal.write(trigger, self.state.score, "-", "wake_capped")
        return False

    def _open_wake(self, trigger: str, now: datetime) -> None:
        """Publie un réveil ; le Grok Bot le récupérera sur GET /wake (latence = sa cadence de polling)."""
        self.state.wakes.append(iso(now))
        tier = rules.current_tier(self.state)
        wake_id = f"{now.isoformat(timespec='seconds')}-{trigger}"
        context = build_context(trigger, self.state, tier, self.prices, self.eur,
                                self.journal.tail(30), self.s.whitelist, self.markets)
        context += f'\ndecision_id à utiliser : "{wake_id}"\n'
        self.mailbox.open_wake(wake_id, context)
        self._wake_opened_at, self._wake_trigger = now, trigger
        self.journal.write(trigger, self.state.score, wake_id, "wake_opened")

    def _check_wake_timeout(self, now: datetime) -> None:
        wake_id = self.mailbox.current_wake()
        if not wake_id or not self._wake_opened_at:
            return
        if now - self._wake_opened_at > timedelta(minutes=self.s.wake_timeout_minutes):
            self.mailbox.close_wake()
            self.journal.write(self._wake_trigger, self.state.score, wake_id, "agent_timeout", "-", "-", "-",
                               f"aucune décision en {self.s.wake_timeout_minutes} min -> hold")
            self._wake_opened_at = None

    def _process_decisions(self, now: datetime) -> None:
        wake_id = self.mailbox.current_wake()
        while not self.mailbox.decisions.empty():
            raw = self.mailbox.decisions.get_nowait()
            if not wake_id or raw.get("decision_id") != wake_id:
                self.journal.write("api", self.state.score, str(raw.get("decision_id")), "decision_stale")
                continue
            try:
                decision = parse_decision(raw)
            except (AgentError, ValueError) as exc:
                decision = hold_decision(wake_id, f"décision invalide : {exc}")
                self.journal.write(self._wake_trigger, self.state.score, wake_id, "agent_error", "-", "-", "-", str(exc))
            self._apply_decision(decision, wake_id, self._wake_trigger, now)
            self.mailbox.close_wake()
            self._wake_opened_at = None
            wake_id = None

    def _apply_decision(self, decision: dict, decision_id: str, trigger: str, now: datetime) -> None:
        tier = rules.current_tier(self.state)
        self.journal.write(trigger, self.state.score, decision_id, f"decision:{decision['decision']}",
                           "-", "-", "-", str(decision["why_better"]))
        executed = 0
        for raw in decision["orders"]:
            try:
                order = ProposedOrder.from_agent(raw)
            except ValueError as exc:
                self._refuse(trigger, decision_id, str(raw), "FORMAT", str(exc))
                continue
            verdict = validate(order, self.state, tier, self.markets, self.prices, self.eur,
                               self.s.whitelist, executed)
            if not verdict.ok:
                self._refuse(trigger, decision_id, f"{order.side} {order.pair} {order.amount_eur} EUR",
                             verdict.check, verdict.reason)
                continue
            self._execute(order, decision_id, trigger)
            executed += 1

        # Dilemme "fermer une position" : si le bot ne l'a pas fait à la dernière heure, le gardien ferme la plus petite
        self._enforce_force_close(now)
        self.state.last_decision_prices = {k: str(v) for k, v in self.prices.items()}

    def _refuse(self, trigger: str, decision_id: str, desc: str, check: str, reason: str) -> None:
        self.journal.write(trigger, self.state.score, decision_id, "order_refused", desc, "-", check, reason)
        self.state.refused_orders = (self.state.refused_orders + [f"{decision_id} {desc} → {check}: {reason}"])[-10:]

    # ================================================================ exécution
    def _base_amount(self, pair: str, amount_eur: Decimal, price: Decimal) -> Decimal:
        min_base = str(self.markets[pair].get("minOrderInBaseAsset", "0.00000001"))
        decimals = len(min_base.split(".")[1]) if "." in min_base else 0
        return (amount_eur / price).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_DOWN)

    def _execute(self, order: ProposedOrder, decision_id: str, trigger: str) -> None:
        if order.side == "buy":
            amount = self._base_amount(order.pair, order.amount_eur, order.price)
        else:
            pos = next(p for p in self.state.position_objs() if p.pair == order.pair)
            amount = min(pos.qty_d, self._base_amount(order.pair, order.amount_eur, order.price))
        self._submit(order.pair, order.side, amount, order.price, "agent", decision_id, trigger,
                     stop_pct=str(order.stop_pct or ""))

    def _place_sell_at_bid(self, pair: str, reason: str) -> None:
        pos = next((p for p in self.state.position_objs() if p.pair == pair), None)
        if not pos:
            return
        bid, _ = self.client.ticker_book(pair)
        self._submit(pair, "sell", pos.qty_d, bid, reason, "-", "tick")

    def _submit(self, pair: str, side: str, amount: Decimal, price: Decimal, reason: str,
                decision_id: str, trigger: str, stop_pct: str = "") -> None:
        if amount <= 0:
            self.journal.write(trigger, self.state.score, decision_id, "order_skipped", pair, "0", "-", "montant nul après arrondi")
            return
        if self.s.mode == "dry_run":
            order_id = f"dry-{int(time.time() * 1000)}"
            self.journal.write(trigger, self.state.score, decision_id, f"DRY_{side}", pair,
                               f"{amount.normalize():f}@{price}", "OK", reason)
            return
        # Ordres du bot : post_only (0 % maker, rejet si le prix croise le carnet).
        # Ordres de protection : exécution immédiate acceptée, la survie prime sur les frais.
        post_only = reason == "agent"
        try:
            resp = self.client.create_limit_order(pair, side, amount, price, post_only=post_only)
            order_id = str(resp["orderId"])
        except (BitvavoError, KeyError) as exc:
            self.journal.write(trigger, self.state.score, decision_id, "order_error", pair, str(amount), "ERR", str(exc))
            return
        self.state.open_orders.append(TrackedOrder(order_id, pair, side, str(amount), str(price),
                                                   iso(utcnow()), stop_pct, reason).__dict__)
        self.state.last_activity_date = utcnow().strftime("%Y-%m-%d")
        self.journal.write(trigger, self.state.score, decision_id, f"order_{side}", pair,
                           f"{amount.normalize():f}@{price}", "OK", f"{reason} id={order_id}")

    def _cancel(self, o: TrackedOrder, why: str) -> None:
        if self.s.mode != "dry_run":
            try:
                self.client.cancel_order(o.pair, o.order_id)
            except BitvavoError as exc:
                log.warning("cancel %s : %s", o.order_id, exc)
        self.journal.write("tick", self.state.score, "-", "order_cancelled", o.pair, o.amount, "-", f"{why} id={o.order_id}")

    def _cancel_all_open_orders(self, why: str) -> None:
        for o in self.state.order_objs():
            self._cancel(o, why)
        self.state.open_orders = []

    def _enforce_force_close(self, now: datetime) -> None:
        d = self.state.active_dilemma
        if not d or not d.get("force_close_one") or d.get("enforced"):
            return
        if parse_iso(d["until"]) - now > timedelta(hours=1):
            return
        positions = self.state.position_objs()
        if positions and not any(o.side == "sell" for o in self.state.order_objs()):
            smallest = min(positions, key=lambda p: p.qty_d * self.prices.get(p.pair, Decimal("0")))
            self.journal.write("dilemma", self.state.score, "-", "force_close", smallest.pair, smallest.qty, "-", "dilemme non honoré par le bot")
            self._place_sell_at_bid(smallest.pair, "dilemma")
        d["enforced"] = True

    # ================================================================ mort
    def _die(self) -> None:
        self.state.alive = False
        self.journal.write("tick", self.state.score, "-", "DEATH", "-", "-", "-",
                           f"capital score {self.state.score} < {C.DEATH_THRESHOLD}")
        self._cancel_all_open_orders("death")
        for p in self.state.position_objs():
            self._place_sell_at_bid(p.pair, "death")
        self.state.save(self.s.state_path)
        raise Halt("mort constatée — liquidation lancée, révoquer la clé API")
