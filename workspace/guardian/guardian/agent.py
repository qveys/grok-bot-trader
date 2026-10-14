"""Construction du contexte de réveil et validation de forme des décisions.

Architecture Grok Bot (plateforme d'agents always-on, bêta 2026) : le gardien
n'appelle personne. Le bot vient chercher son réveil sur GET /wake et dépose
sa décision sur POST /decision (voir api.py). Ce module ne fait aucun réseau.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal

from . import config as C
from . import rules
from .state import State, utcnow

REQUIRED_KEYS = ("decision_id", "situation", "threats", "options", "decision", "why_better", "orders")


class AgentError(RuntimeError):
    pass


def build_context(trigger: str, state: State, tier: C.Tier, prices: dict[str, Decimal],
                  eur_balance: Decimal, journal_tail: list[str], whitelist: tuple[str, ...],
                  markets: dict[str, dict]) -> str:
    now = utcnow()
    nm = rules.next_milestone(state)
    lines = [
        f"RÉVEIL : {trigger} — {now.isoformat(timespec='seconds')}",
        f"Jour de jeu : J+{rules.game_day(state, now)}",
        "",
        "ÉTAT",
        f"- capital_score : {state.score:.2f} EUR",
        f"- distance au seuil de mort ({C.DEATH_THRESHOLD} EUR) : {state.score - C.DEATH_THRESHOLD:.2f} EUR",
        f"- solde EUR disponible : {eur_balance:.2f}",
        f"- métabolisme actuel : {Decimal(state.metabolism_rate) * 100:.2f} %/jour, cumul prélevé {Decimal(state.metabolism_cumulative):.2f} EUR",
        f"- exposition crypto : {rules.crypto_exposure(eur_balance, state, prices):.0%} (max {tier.max_crypto_exposure:.0%})",
        f"- tier : {tier.name} — risque/trade {tier.risk_per_trade:.0%}, positions max {tier.max_positions}, stop max -{tier.stop_pct:.0%}, ordres max {tier.max_orders_per_wake}",
        f"- achats gelés : {state.purchases_frozen_until or 'non'}",
        f"- paliers atteints : {state.milestones_reached() or 'aucun'} ; manqués : {state.missed_milestones}",
    ]
    if nm:
        threshold, deadline = nm
        lines.append(f"- prochain palier : {threshold} EUR avant J+{deadline} (reste {deadline - rules.game_day(state, now)} jours, {threshold - state.score:.2f} EUR)")
    if state.active_dilemma:
        lines.append(f"- DILEMME ACTIF jusqu'au {state.active_dilemma['until']} : {state.active_dilemma['label']}")

    lines += ["", "POSITIONS"]
    positions = state.position_objs()
    if not positions:
        lines.append("- aucune")
    for p in positions:
        px = prices.get(p.pair, Decimal("0"))
        pnl = (px / p.entry_d - 1) if p.entry_d else Decimal("0")
        lines.append(f"- {p.pair} : {p.qty_d.normalize():f} @ {p.entry_d} → {px} ({pnl:+.2%}), stop {p.stop_d}, valeur {p.qty_d * px:.2f} EUR")

    lines += ["", "ORDRES OUVERTS"]
    orders = state.order_objs()
    lines.append("- aucun" if not orders else "")
    for o in orders:
        lines.append(f"- {o.side} {o.pair} {o.amount} @ {o.price} (placé {o.placed_at})")

    lines += ["", "MARCHÉ (prix mid, paires autorisées)"]
    for pair in whitelist:
        m = markets.get(pair, {})
        lines.append(f"- {pair} : {prices.get(pair, 'n/a')} EUR — ordre min {m.get('minOrderInQuoteAsset', '?')} EUR")

    if state.refused_orders:
        lines += ["", "ORDRES REFUSÉS PAR LE GARDIEN (derniers)"]
        lines += [f"- {r}" for r in state.refused_orders[-5:]]

    lines += ["", "JOURNAL (30 dernières entrées)"]
    lines += journal_tail or ["- vide"]
    lines += [
        "",
        "Réponds en envoyant UNIQUEMENT le JSON décrit dans tes instructions sur POST /decision.",
    ]
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise AgentError("Aucun JSON dans la réponse")
        return json.loads(text[start:end + 1])


def _check_shape(d: dict) -> dict:
    missing = [k for k in REQUIRED_KEYS if k not in d]
    if missing:
        raise AgentError(f"Clés manquantes : {missing}")
    if not isinstance(d["orders"], list) or not isinstance(d["options"], list):
        raise AgentError("orders et options doivent être des listes")
    if len(d["options"]) < 3 or not any(str(o.get("label", "")).lower() == "hold" for o in d["options"]):
        raise AgentError("Au moins 3 options, dont 'hold'")
    return d


def parse_decision(raw: dict) -> dict:
    """Valide la forme d'une décision reçue via l'API. Lève AgentError si invalide."""
    return _check_shape(raw)


def hold_decision(decision_id: str, reason: str) -> dict:
    return {
        "decision_id": decision_id,
        "situation": "fallback",
        "threats": [reason],
        "options": [{"label": "hold"}],
        "decision": "hold",
        "why_better": reason,
        "orders": [],
        "_usage": {},
    }
