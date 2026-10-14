"""Contrôles V1..V10 (section 3.4 des règles). Un seul échec = ordre refusé."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from . import config as C
from . import rules
from .state import State, utcnow


@dataclass
class ProposedOrder:
    pair: str
    side: str
    price: Decimal
    amount_eur: Decimal
    stop_pct: Decimal | None   # fraction positive, ex 0.08

    @classmethod
    def from_agent(cls, raw: dict) -> "ProposedOrder":
        try:
            pair = str(raw["pair"]).upper()
            side = str(raw["side"]).lower()
            price = Decimal(str(raw["price"]))
            amount_eur = Decimal(str(raw["amount_eur"]))
            stop_raw = raw.get("stop_pct")
            stop_pct = abs(Decimal(str(stop_raw))) / 100 if stop_raw is not None else None
        except (KeyError, InvalidOperation, TypeError) as exc:
            raise ValueError(f"Ordre mal formé : {raw} ({exc})") from exc
        if raw.get("type", "limit") != "limit":
            raise ValueError("Seuls les ordres limit sont acceptés")
        return cls(pair, side, price, amount_eur, stop_pct)


@dataclass
class Verdict:
    ok: bool
    check: str
    reason: str


def validate(order: ProposedOrder, state: State, tier: C.Tier, markets: dict[str, dict],
             prices: dict[str, Decimal], eur_balance: Decimal, whitelist: tuple[str, ...],
             orders_this_wake: int) -> Verdict:
    now = utcnow()
    d = state.active_dilemma or {}
    positions = {p.pair: p for p in state.position_objs()}

    # V1 — liste blanche
    if order.pair not in whitelist:
        return Verdict(False, "V1", f"{order.pair} hors liste blanche")

    # V2 — limit uniquement : garanti par ProposedOrder.from_agent

    # V3 — minimum Bitvavo
    m = markets.get(order.pair)
    if not m or m.get("status") != "trading":
        return Verdict(False, "V3", f"{order.pair} indisponible au trading")
    min_quote = Decimal(str(m.get("minOrderInQuoteAsset", "0")))
    if order.amount_eur < min_quote:
        return Verdict(False, "V3", f"montant {order.amount_eur} < minimum {min_quote} EUR")

    if order.side == "buy":
        # V4 — risque max par trade, plancher = minimum Bitvavo (sinon aucun trade possible à 50 EUR)
        max_eur = max((state.score * tier.risk_per_trade).quantize(Decimal("0.01")), min_quote)
        if order.amount_eur > max_eur:
            return Verdict(False, "V4", f"{order.amount_eur} EUR > risque max {max_eur} EUR ({tier.name})")
        if order.amount_eur > eur_balance:
            return Verdict(False, "V4", f"solde EUR insuffisant ({eur_balance})")

        # V5 — nombre de positions
        new_pairs = set(positions) | {o.pair for o in state.order_objs() if o.side == "buy"}
        if order.pair not in new_pairs and len(new_pairs) + 1 > tier.max_positions:
            return Verdict(False, "V5", f"{len(new_pairs) + 1} positions > max {tier.max_positions}")

        # V6 — exposition crypto
        gross = rules.gross_value(eur_balance, state, prices)
        crypto_after = rules.crypto_value(state, prices) + order.amount_eur
        if gross > 0 and crypto_after / gross > tier.max_crypto_exposure:
            return Verdict(False, "V6", f"exposition {crypto_after / gross:.0%} > max {tier.max_crypto_exposure:.0%}")

        # V7 — gel des achats
        if state.purchases_frozen_until and state.purchases_frozen_until > now.isoformat():
            return Verdict(False, "V7", f"achats gelés jusqu'à {state.purchases_frozen_until}")

        # V9 — stop-loss
        if order.stop_pct is None:
            order.stop_pct = tier.stop_pct   # le gardien pose le stop lui-même
        if order.stop_pct > tier.stop_pct:
            return Verdict(False, "V9", f"stop -{order.stop_pct:.0%} plus large que max -{tier.stop_pct:.0%}")
        # Un stop qui ne protège pas du seuil de mort est refusé
        worst = state.score - order.amount_eur * order.stop_pct
        if worst < C.DEATH_THRESHOLD:
            return Verdict(False, "V9", f"pire cas {worst:.2f} EUR < seuil de mort")

        # V10 — dilemme
        if order.pair in d.get("no_buy", []):
            return Verdict(False, "V10", f"dilemme actif : pas d'achat sur {order.pair}")

    else:  # sell
        pos = positions.get(order.pair)
        if not pos:
            return Verdict(False, "V4", f"aucune position sur {order.pair}")
        price = prices.get(order.pair, order.price)
        if order.amount_eur > pos.qty_d * price * Decimal("1.01"):
            return Verdict(False, "V4", "vente supérieure à la position détenue")

    # V8 — ordres par réveil
    if orders_this_wake + 1 > tier.max_orders_per_wake:
        return Verdict(False, "V8", f"plus de {tier.max_orders_per_wake} ordres ce réveil")

    # Cohérence prix : un limit à plus de 5 % du marché est une erreur du bot, pas une stratégie
    mkt = prices.get(order.pair)
    if mkt and abs(order.price - mkt) / mkt > Decimal("0.05"):
        return Verdict(False, "V2", f"prix limit {order.price} à plus de 5 % du marché {mkt}")

    return Verdict(True, "OK", "validé")
