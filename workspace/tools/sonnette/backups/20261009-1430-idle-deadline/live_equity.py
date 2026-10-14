#!/usr/bin/env python3
"""Capital réel (argent) for the sonnette Risk bell — read-only.

Writes /workspace/predict-market-bot/state/live_equity.json every ~5 min.

Méthode hors_bot (crypto déjà détenue par Quentin, hors bot) :
  Au premier appel réussi à `revx account balances`, on enregistre les quantités
  BTC / ETH / SOL (disponible + réservé + staké) comme référence hors_bot.
  Ensuite, la quantité « bot » d'un actif = max(0, solde_actuel − hors_bot),
  seulement sur une paire où le bot a une position ouverte (idée à la hausse =
  achat net, OU idée à la baisse = vente d'ouverture via idea_type/cycle_id).
  Un rachat de cycle baisse ne compte pas comme nouvel achat ouvert.
  Le crypto déjà détenu n'entre jamais dans capital_reel.
  Seuls EUR (dispo + réservé) + valeur du crypto bot (long) comptent.

Ajustements EUR (dépôts / retraits hors bot) :
  Si le cash EUR change sans nouvel ordre bot (live_orders.jsonl), on décale
  ref_jour.valeur et plus_haut du même montant, et on journalise l'ajustement.

Peak (plus_haut) : max depuis le 1er achat réel du bot ; null tant qu'aucun.
Référence du jour : première valeur après minuit Europe/Brussels.

Si revx échoue : on garde les dernières valeurs, stale=true, pas de sonnerie equity.

Vue complète de l'argent réel (affichage du tableau de bord, aucune sonnerie n'en dépend) :
  soldes_revolut_x : par devise disponible / réservé / staké / total, prix et valeur en euros ;
  metamask : solde ETH (Arbitrum One, eth_getBalance public, lecture seule) et valeur en euros ;
  total_reel_eur : Revolut X (EUR + toutes les pièces, bot et hors bot) + MetaMask.
Lectures seulement : `revx account balances` et `eth_getBalance`. Jamais d'ordre.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Brussels")
ALLOWED = ("BTC", "ETH", "SOL")
EUR_ADJ_MIN = 0.05  # ignore noise below 5 cents


def _now() -> datetime:
    return datetime.now(TZ)


def _load(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return default


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _f(x, default=None):
    if x is None or x == "":
        return default
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_balances(raw) -> dict:
    """Return {currency: {available, reserved, staked, total}}."""
    rows = raw
    if isinstance(raw, dict):
        for k in ("data", "balances", "results", "items"):
            if isinstance(raw.get(k), list):
                rows = raw[k]
                break
        else:
            rows = [raw]
    out = {}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        cur = str(r.get("currency") or r.get("asset") or "").upper()
        if not cur:
            continue
        avail = _f(r.get("available"), 0.0) or 0.0
        reserved = _f(r.get("reserved"), 0.0) or 0.0
        staked = _f(r.get("staked"), 0.0) or 0.0
        total = _f(r.get("total"))
        if total is None:
            total = avail + reserved + staked
        out[cur] = {"available": avail, "reserved": reserved, "staked": staked, "total": total}
    return out


def fetch_balances_revx(revx_bin: str, proxy: str, timeout_s: float = 30.0) -> dict:
    """READ-ONLY. Raises on failure."""
    env = dict(os.environ, HTTPS_PROXY=proxy, HTTP_PROXY=proxy, ALL_PROXY=proxy,
               PATH="/home/box/.local/bin:" + os.environ.get("PATH", ""))
    proc = subprocess.run(
        [revx_bin, "account", "balances", "--json"],
        capture_output=True, text=True, timeout=timeout_s, env=env,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"revx balances code {proc.returncode}")
    raw = (proc.stdout or "").strip()
    starts = [i for i in (raw.find("["), raw.find("{")) if i >= 0]
    if not starts:
        raise RuntimeError("revx balances: réponse vide")
    data = json.loads(raw[min(starts):])
    bal = parse_balances(data)
    if "EUR" not in bal:
        raise RuntimeError("revx balances: EUR manquant")
    return bal


def fetch_metamask_eth(address: str, rpc: str, proxy: str, timeout_s: float = 20.0) -> float:
    """READ-ONLY: eth_getBalance (solde ETH) sur un RPC public Arbitrum. Raises on failure."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": [address, "latest"]}).encode()
    handlers = [urllib.request.ProxyHandler({"https": proxy, "http": proxy})] if proxy else [urllib.request.ProxyHandler({})]
    op = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(rpc, data=body, headers={"Content-Type": "application/json", "User-Agent": "sonnette/1"})
    with op.open(req, timeout=timeout_s) as r:
        res = json.loads(r.read().decode())
    if not isinstance(res, dict) or not isinstance(res.get("result"), str):
        raise RuntimeError("eth_getBalance: réponse inattendue")
    return int(res["result"], 16) / 1e18


def _bot_rows(live_orders_path: Path) -> list[dict]:
    """Successful, non-dry live_place rows (incl. idea_type / cycle_id for idée à la baisse)."""
    try:
        lines = Path(live_orders_path).read_text().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(row, dict) or not row.get("ok") or row.get("dry_run"):
            continue
        order = row.get("order") if isinstance(row.get("order"), dict) else row
        idea = str(order.get("idea_type") or order.get("kind") or row.get("kind") or "").lower()
        out.append({
            "at": str(row.get("at") or ""),
            "side": str(order.get("side") or "").lower(),
            "pair": str(order.get("pair") or "").upper().replace("/", "-"),
            "amount": _f(order.get("amount_eur"), 0.0) or 0.0,
            "idea_type": idea,
            "kind": str(row.get("kind") or order.get("kind") or "").lower(),
            "cycle_id": str(order.get("cycle_id") or order.get("linked_position_id")
                            or order.get("exit_for") or ""),
            "oid": str(order.get("id") or row.get("client_order_id") or ""),
            "rebuy_reason": order.get("rebuy_reason"),
            "purpose": str(order.get("purpose") or "").lower(),
            "target_for": order.get("target_for"),
        })
    return out


def bot_orders_signature(live_orders_path: Path) -> str:
    rows = _bot_rows(live_orders_path)
    return str(len(rows)) + ":" + (rows[-1]["at"] if rows else "")


def bot_open_pairs(live_orders_path: Path) -> set[str]:
    """Pairs with an open bot position (hausse long OR idée à la baisse short).

    Longs = buys − plain sells (EUR netting). Idée à la baisse = opening sell
    (idea_type/kind=baisse, no cycle_id) until a linked rebuy or auto_exit closes it.
    auto_exit rows and objectif (target) sells are not treated as opening buys/sells.
    """
    shorts_open: set[str] = set()  # position ids still open
    short_pair: dict[str, str] = {}
    closed_shorts: set[str] = set()
    buys: dict[str, tuple[str, float]] = {}  # oid -> (pair, amount)
    sells_by_pair: dict[str, float] = {}
    for r in _bot_rows(live_orders_path):
        if r["kind"] == "auto_exit":
            cid = r["cycle_id"]
            if cid:
                closed_shorts.add(cid)
                # also close a long identified by exit_for / linked id
            continue
        idea = r["idea_type"]
        linked = r["cycle_id"]
        pair, side, amount = r["pair"], r["side"], r["amount"]
        if not pair:
            continue
        # Idée à la baisse: opening sale (sell held coins) — never "vendre d'abord"
        if side == "sell" and idea == "baisse" and not linked:
            oid = r["oid"] or f"live-{pair}-{r['at'] or 'x'}"
            sid = oid if oid.startswith(("rx-live", "live-")) else f"rx-live-{oid}"
            shorts_open.add(sid)
            short_pair[sid] = pair
            continue
        # Closing rebuy of a baisse cycle
        if side == "buy" and linked and (idea == "baisse" or r.get("rebuy_reason")):
            closed_shorts.add(linked)
            continue
        if side == "buy" and amount > 0:
            oid = r["oid"] or f"live-{pair}-{r['at'] or 'x'}"
            buys[oid] = (pair, amount)
        elif side == "sell" and amount > 0:
            if r.get("target_for") or r["purpose"] in ("target", "objectif"):
                continue
            sells_by_pair[pair] = sells_by_pair.get(pair, 0.0) + amount
    open_pairs: set[str] = set()
    remaining = dict(sells_by_pair)
    for oid, (pair, cost) in buys.items():
        if oid in closed_shorts:
            continue
        left = remaining.get(pair, 0.0)
        if left >= cost - 1e-9:
            remaining[pair] = left - cost
            continue
        if left > 0:
            remaining[pair] = 0.0
        open_pairs.add(pair)
    for sid in shorts_open:
        if sid not in closed_shorts:
            open_pairs.add(short_pair[sid])
    return open_pairs


def _local_date(at: str) -> str | None:
    try:
        return datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone(TZ).date().isoformat()
    except ValueError:
        return at[:10] if len(at) >= 10 else None


def has_real_buy_today(live_orders_path: Path, today: str) -> bool:
    """True if a live bot entry (hausse buy OR baisse opening sell) happened today."""
    for r in _bot_rows(live_orders_path):
        if _local_date(r["at"]) != today:
            continue
        if r["kind"] == "auto_exit":
            continue
        if r["side"] == "buy" and not (r["cycle_id"] and (r["idea_type"] == "baisse" or r.get("rebuy_reason"))):
            return True
        if r["side"] == "sell" and r["idea_type"] == "baisse" and not r["cycle_id"]:
            return True
    return False


def first_real_buy_at(live_orders_path: Path) -> str | None:
    """First live bot entry (hausse buy or baisse opening sell)."""
    ats = []
    for r in _bot_rows(live_orders_path):
        if not r["at"] or r["kind"] == "auto_exit":
            continue
        if r["side"] == "buy" and not (r["cycle_id"] and (r["idea_type"] == "baisse" or r.get("rebuy_reason"))):
            ats.append(r["at"])
        elif r["side"] == "sell" and r["idea_type"] == "baisse" and not r["cycle_id"]:
            ats.append(r["at"])
    return sorted(ats)[0] if ats else None


class LiveEquity:
    """Stateful equity tracker. Fetchers are injectable for --simulate."""

    def __init__(
        self,
        out_path: Path,
        live_orders_path: Path,
        revx_bin: str = "/home/box/.local/bin/revx",
        proxy: str = "http://127.0.0.1:8791",
        every_s: float = 300.0,
        fetch_balances=None,
        log=None,
        metamask_address: str | None = None,
        arbitrum_rpc: str = "https://arb1.arbitrum.io/rpc",
        fetch_metamask=None,
    ):
        self.out_path = Path(out_path)
        self.live_orders_path = Path(live_orders_path)
        self.revx_bin = revx_bin
        self.proxy = proxy
        self.every_s = every_s
        self.fetch_balances = fetch_balances  # () -> balances dict
        self.metamask_address = metamask_address
        self.arbitrum_rpc = arbitrum_rpc
        self.fetch_metamask = fetch_metamask  # () -> ETH quantity (tests)
        self.log = log or (lambda level, msg: None)
        self._last_mono = -1e18

    def read(self) -> dict | None:
        d = _load(self.out_path, None)
        return d if isinstance(d, dict) else None

    def maybe_update(self, now: datetime, prices: dict[str, float], force: bool = False,
                     now_mono: float | None = None) -> dict:
        """Refresh at most every `every_s`, or on a new Brussels day, or when forced."""
        mono = time.monotonic() if now_mono is None else now_mono
        prev = self.read() or {}
        due = force or not prev or (mono - self._last_mono) >= self.every_s
        new_day = (prev.get("ref_jour") or {}).get("date") not in (None, now.date().isoformat())
        if not due and not new_day:
            return prev
        return self.update(now, prices, prev, mono)

    def update(self, now: datetime, prices: dict[str, float], prev: dict | None = None,
               now_mono: float | None = None) -> dict:
        prev = prev if isinstance(prev, dict) else (self.read() or {})
        mono = time.monotonic() if now_mono is None else now_mono
        track = dict(prev.get("_track") or {})
        today = now.date().isoformat()

        try:
            if self.fetch_balances is not None:
                bal = self.fetch_balances()
            else:
                bal = fetch_balances_revx(self.revx_bin, self.proxy)
        except Exception as e:  # noqa: BLE001
            self.log("WARN", f"live_equity: lecture revx échouée ({type(e).__name__}) — on garde les dernières valeurs, stale=true")
            if not prev:
                out = {
                    "ts": now.isoformat(),
                    "eur_available": None, "eur_reserved": None,
                    "bot_positions_value": None, "capital_reel": None,
                    "hors_bot": {}, "ref_jour": None, "plus_haut": None,
                    "perte_jour_pct": None, "baisse_depuis_plus_haut_pct": None,
                    "ajustements": [], "stale": True,
                    "notes_fr": "Aucune valeur encore : Revolut X n'a pas répondu. Pas de sonnerie sur la perte/baisse.",
                    "_track": track,
                }
                _save(self.out_path, out)
                self._last_mono = mono
                return out
            stale = dict(prev)
            stale["stale"] = True
            stale["ts"] = now.isoformat()
            stale["notes_fr"] = (
                "Valeurs figées : Revolut X n'a pas répondu. "
                "On garde le dernier capital connu. Pas de sonnerie sur la perte/baisse tant que c'est périmé."
            )
            stale.setdefault("ajustements", [])
            _save(self.out_path, stale)
            self._last_mono = mono
            return stale

        eur_av = float(bal.get("EUR", {}).get("available") or 0.0)
        eur_rs = float(bal.get("EUR", {}).get("reserved") or 0.0)
        eur = eur_av + eur_rs

        # hors_bot baseline (first successful run) — see module docstring
        hors_prev = prev.get("hors_bot") or {}
        open_pairs = bot_open_pairs(self.live_orders_path)
        sig = bot_orders_signature(self.live_orders_path)
        base: dict[str, float] = {}
        if not track.get("hors_bot_locked"):
            for a in ALLOWED:
                base[a] = float(bal.get(a, {}).get("total") or 0.0)
            track["hors_bot_locked"] = True
            track["hors_bot_depuis"] = now.isoformat()
            self.log("INFO", "live_equity: baseline hors_bot enregistrée (crypto déjà détenu, hors bot)")
        else:
            for a in ALLOWED:
                base[a] = float((hors_prev.get(a) or {}).get("qty") or 0.0)

        # bot qty = solde − baseline, only for pairs where the bot has an open position
        # (hausse long OR baisse short). No bot position → personal change: baseline follows.
        bot_pos, bot_value, hors = {}, 0.0, {}
        bot_qty_now: dict[str, float] = {}
        missing_px: list[str] = []
        for a in ALLOWED:
            tot = float(bal.get(a, {}).get("total") or 0.0)
            pair = f"{a}-EUR"
            px = prices.get(pair)
            if pair in open_pairs:
                qty = max(0.0, tot - base[a])
                if tot < base[a]:
                    base[a] = tot  # personal sell while bot open: baseline can only shrink
            else:
                if abs(tot - base[a]) > 1e-9:
                    if abs(tot - base[a]) * (px or 0) >= 0.5:
                        self.log("INFO", f"live_equity: solde {a} hors bot changé "
                                         f"({base[a]:.8f} → {tot:.8f}), baseline mise à jour")
                    base[a] = tot
                qty = 0.0
            bot_qty_now[a] = qty
            hors[a] = {"qty": round(base[a], 10),
                       "eur": round(base[a] * px, 2) if px is not None else (hors_prev.get(a) or {}).get("eur"),
                       "solde_total": round(tot, 10)}
            if qty > 0:
                if px is None:
                    missing_px.append(pair)
                val = round(qty * px, 4) if px is not None else 0.0
                bot_pos[a] = {"qty": round(qty, 10), "prix": px, "eur": val}
                bot_value += val
        bot_value = round(bot_value, 4)
        capital = round(eur + bot_value, 4)

        # EUR change without bot activity (no new live order row, no change in bot crypto qty)
        # = deposit / withdrawal / personal trade → shift ref_jour and plus_haut by the same amount.
        ajustements = list(prev.get("ajustements") or [])
        adj = 0.0
        eur_prev = track.get("eur_prev")
        qty_prev = track.get("bot_qty") or {}
        bot_activity = (sig != track.get("bot_orders_sig")) or any(
            abs(bot_qty_now[a] - float(qty_prev.get(a) or 0.0)) > 1e-10 for a in ALLOWED)
        if eur_prev is not None:
            delta = round(eur - float(eur_prev), 4)
            if abs(delta) >= EUR_ADJ_MIN:
                if bot_activity:
                    self.log("INFO", f"live_equity: EUR {delta:+.2f} € avec activité bot — pas d'ajustement")
                else:
                    adj = delta
                    ajustements.append({
                        "ts": now.isoformat(), "delta_eur": adj,
                        "raison_fr": (f"Le cash EUR a changé de {adj:+.2f} € sans ordre du bot "
                                      f"(dépôt, retrait ou opération perso). Référence du jour et "
                                      f"plus-haut décalés du même montant : pas compté comme gain/perte."),
                    })
                    ajustements = ajustements[-30:]
                    self.log("INFO", f"live_equity: ajustement {adj:+.2f} € (EUR hors bot)")

        # Day reference
        ref = dict(prev.get("ref_jour") or {}) if prev.get("ref_jour") else {}
        if ref.get("date") != today:
            ref = {"date": today, "valeur": capital}
            self.log("INFO", f"live_equity: nouvelle référence du jour = {capital} €")
        else:
            # apply deposit shift to existing ref
            if adj:
                ref["valeur"] = round(float(ref["valeur"]) + adj, 4)

        # Peak since first real buy
        first_buy = track.get("first_real_buy_at") or first_real_buy_at(self.live_orders_path)
        if first_buy:
            track["first_real_buy_at"] = first_buy
        plus_haut = prev.get("plus_haut")
        if first_buy:
            if plus_haut is None:
                plus_haut = capital
            else:
                plus_haut = float(plus_haut)
                if adj:
                    plus_haut = round(plus_haut + adj, 4)
                if capital > plus_haut:
                    plus_haut = capital
            plus_haut = round(float(plus_haut), 4)
        else:
            plus_haut = None  # no drawdown until first bot buy

        ref_v = float(ref["valeur"]) if ref.get("valeur") is not None else capital
        perte = max(0.0, (ref_v - capital) / ref_v) if ref_v > 0 else 0.0
        if plus_haut and plus_haut > 0:
            dd = max(0.0, (plus_haut - capital) / plus_haut)
        else:
            dd = None

        track.update({
            "eur_prev": eur,
            "last_ok_ts": now.isoformat(),
            "bot_orders_sig": sig,
            "bot_qty": bot_qty_now,
            "capital_prev": capital,
        })

        notes = (
            "Capital réel = EUR (dispo+réservé) + valeur du crypto acheté par le bot. "
            "Le crypto déjà détenu (hors_bot) est une photo prise au premier lancement ; "
            "les achats bot = solde actuel − hors_bot. "
            "Les dépôts/retraits EUR hors bot décalent la référence du jour et le plus-haut."
        )
        if missing_px:
            notes += (f" ATTENTION : pas de prix frais pour {', '.join(missing_px)} — valeur bot incomplète, "
                      f"marqué périmé (pas de sonnerie perte/baisse).")
            self.log("WARN", f"live_equity: prix manquant pour {missing_px} — capital marqué périmé")
        vue = self._full_view(now, bal, prices, prev)
        out = {
            "ts": now.isoformat(),
            "eur_available": round(eur_av, 4),
            "eur_reserved": round(eur_rs, 4),
            "bot_positions": bot_pos,
            "bot_positions_value": bot_value,
            "capital_reel": capital,
            "hors_bot": hors,
            "ref_jour": ref,
            "plus_haut": plus_haut,
            "perte_jour_pct": round(perte * 100, 4),
            "baisse_depuis_plus_haut_pct": None if dd is None else round(dd * 100, 4),
            "ajustements": ajustements,
            "stale": bool(missing_px),
            **vue,
            "source": "revx account balances (lecture seule) + live_orders.jsonl + prix du collecteur + MetaMask eth_getBalance (lecture seule)",
            "notes_fr": notes,
            "_track": track,
        }
        _save(self.out_path, out)
        self._last_mono = mono
        return out

    def _full_view(self, now: datetime, bal: dict, prices: dict[str, float], prev: dict) -> dict:
        """Soldes Revolut X détaillés + MetaMask + total réel. Affichage seulement (aucune sonnerie n'en dépend)."""
        soldes, rx_total, manque = {}, 0.0, []
        for cur in sorted(bal):
            b = bal[cur]
            tot = float(b.get("total") or 0.0)
            if cur != "EUR" and tot <= 0:
                continue
            px = 1.0 if cur == "EUR" else prices.get(f"{cur}-EUR")
            val = round(tot * px, 4) if px is not None else None
            soldes[cur] = {"disponible": round(float(b.get("available") or 0.0), 10),
                           "reserve": round(float(b.get("reserved") or 0.0), 10),
                           "stake": round(float(b.get("staked") or 0.0), 10),
                           "total": round(tot, 10), "prix_eur": None if cur == "EUR" else px, "eur": val}
            if val is None:
                manque.append(cur)
            else:
                rx_total += val
        mm_prev = prev.get("metamask") if isinstance(prev.get("metamask"), dict) else None
        mm = None
        if self.metamask_address or self.fetch_metamask is not None:
            px = prices.get("ETH-EUR")
            try:
                eth = self.fetch_metamask() if self.fetch_metamask is not None else fetch_metamask_eth(
                    self.metamask_address, self.arbitrum_rpc, self.proxy)
                mm = {"adresse": self.metamask_address, "reseau": "Arbitrum One", "eth": round(float(eth), 12),
                      "prix_eur": px, "eur": round(float(eth) * px, 4) if px is not None else None,
                      "lu_a": now.isoformat(), "stale": False, "source": "eth_getBalance (RPC public Arbitrum, lecture seule)"}
            except Exception as e:  # noqa: BLE001
                self.log("WARN", f"live_equity: lecture MetaMask échouée ({type(e).__name__}) — dernière valeur gardée")
                if mm_prev:
                    mm = dict(mm_prev, stale=True)
                    if mm.get("eth") is not None and px is not None:
                        mm.update(prix_eur=px, eur=round(float(mm["eth"]) * px, 4))
            if mm is not None and mm.get("eur") is None:
                manque.append("MetaMask ETH")
        mm_eur = (mm or {}).get("eur") or 0.0
        return {
            "soldes_revolut_x": soldes,
            "metamask": mm,
            "total_revolut_x_eur": round(rx_total, 4),
            "total_reel_eur": round(rx_total + mm_eur, 4),
            "total_reel_complet": not manque and not (mm or {}).get("stale", False),
            "total_reel_manque": manque,
            "total_reel_note_fr": ("Tout l'argent réel : Revolut X (euros + toutes les pièces, du bot et hors bot) "
                                   "+ MetaMask. Valeurs au prix du collecteur au moment de la lecture."),
        }

    def ring_eligible(self, open_real_positions: list, today: str) -> bool:
        """Ring 12/15 and 6/8 only if a real position is open OR a live entry was made today."""
        if open_real_positions:
            return True
        return has_real_buy_today(self.live_orders_path, today)
