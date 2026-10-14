"""Moteur de règles : capital score, tier en vigueur, métabolisme, paliers, dilemmes."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from . import config as C
from .state import State, iso, parse_iso, utcnow


# ---------------------------------------------------------------- valorisation
def crypto_value(state: State, prices: dict[str, Decimal]) -> Decimal:
    total = Decimal("0")
    for p in state.position_objs():
        price = prices.get(p.pair)
        if price is None:
            raise RuntimeError(f"Prix manquant pour {p.pair}")
        total += p.qty_d * price
    return total


def gross_value(eur_balance: Decimal, state: State, prices: dict[str, Decimal]) -> Decimal:
    return eur_balance + crypto_value(state, prices)


def capital_score(eur_balance: Decimal, state: State, prices: dict[str, Decimal]) -> Decimal:
    return gross_value(eur_balance, state, prices) - Decimal(state.metabolism_cumulative)


def crypto_exposure(eur_balance: Decimal, state: State, prices: dict[str, Decimal]) -> Decimal:
    gross = gross_value(eur_balance, state, prices)
    if gross <= 0:
        return Decimal("0")
    return crypto_value(state, prices) / gross


# ---------------------------------------------------------------- tier
def current_tier(state: State) -> C.Tier:
    score = state.score
    reached = state.milestones_reached()
    if score < C.DANGER_THRESHOLD:
        tier = C.TIER_DANGER
    elif 250 in reached:
        tier = C.TIER_250
    elif 100 in reached:
        tier = C.TIER_100
    else:
        tier = C.TIER_BASE

    d = state.active_dilemma or {}
    if "max_positions" in d:
        tier = C.Tier(tier.name + "+d5", tier.risk_per_trade, min(tier.max_positions, int(d["max_positions"])),
                      tier.stop_pct, tier.max_crypto_exposure, tier.max_orders_per_wake)
    if "stop_pct" in d:
        tier = C.Tier(tier.name + "+d6", tier.risk_per_trade, tier.max_positions,
                      min(tier.stop_pct, Decimal(d["stop_pct"])), tier.max_crypto_exposure, tier.max_orders_per_wake)
    return tier


def game_day(state: State, now: datetime | None = None) -> int:
    now = now or utcnow()
    return max(0, (now - parse_iso(state.started_at)).days)


# ---------------------------------------------------------------- métabolisme
def metabolism_rate(state: State, now: datetime | None = None) -> Decimal:
    now = now or utcnow()
    month_index = game_day(state, now) // 30
    rate = C.METABOLISM_BASE + C.METABOLISM_MONTHLY_STEP * month_index
    rate += C.METABOLISM_MISSED_MILESTONE * state.missed_milestones
    d = state.active_dilemma or {}
    if "metabolism_mult" in d:
        rate *= Decimal(d["metabolism_mult"])
    if inactive_for_days(state, now) >= C.INACTION_DAYS:
        rate *= 2
    return rate


def inactive_for_days(state: State, now: datetime) -> int:
    if state.positions or state.open_orders:
        return 0
    last = state.last_activity_date or state.started_at[:10]
    return (now.date() - datetime.fromisoformat(last).date()).days


def apply_daily_metabolism(state: State, now: datetime) -> Decimal | None:
    """Appelé à chaque tick ; prélève une fois par jour UTC. Retourne le montant prélevé ou None."""
    today = now.strftime("%Y-%m-%d")
    if state.last_metabolism_date == today:
        return None
    rate = metabolism_rate(state, now)
    amount = (state.score * rate).quantize(Decimal("0.0001"))
    state.metabolism_cumulative = str(Decimal(state.metabolism_cumulative) + amount)
    state.metabolism_rate = str(rate)
    state.last_metabolism_date = today
    return amount


# ---------------------------------------------------------------- paliers
def check_milestones(state: State, now: datetime) -> list[str]:
    """À la clôture 00:00 UTC. Retourne les événements (atteint / manqué)."""
    events: list[str] = []
    day = game_day(state, now)
    for threshold, deadline in C.MILESTONES:
        key = str(int(threshold))
        if state.milestones.get(key):
            continue
        if state.score >= threshold:
            state.milestones[key] = iso(now)
            events.append(f"milestone_reached:{key}")
            if threshold >= C.VICTORY_THRESHOLD:
                state.victory = True
        elif day > deadline and not state.milestones.get(key + "_missed"):
            state.milestones[key + "_missed"] = iso(now)
            state.missed_milestones += 1
            events.append(f"milestone_missed:{key}")
    return events


def next_milestone(state: State) -> tuple[Decimal, int] | None:
    for threshold, deadline in C.MILESTONES:
        if not state.milestones.get(str(int(threshold))):
            return threshold, deadline
    return None


def milestone_is_near(state: State, now: datetime) -> bool:
    nm = next_milestone(state)
    if not nm:
        return False
    threshold, deadline = nm
    close_in_value = state.score >= threshold * (1 - C.MILESTONE_NEAR_PCT)
    close_in_time = (deadline - game_day(state, now)) <= C.MILESTONE_NEAR_DAYS
    return close_in_value or close_in_time


# ---------------------------------------------------------------- dilemmes
def maybe_draw_dilemma(state: State, now: datetime) -> dict | None:
    """Lundi 00:00 UTC : tirage. Retourne le dilemme s'il vient d'être tiré."""
    week = now.strftime("%G-%V")
    if now.weekday() != 0 or state.last_dilemma_week == week:
        return None
    state.last_dilemma_week = week
    d = dict(random.choice(C.DILEMMAS))
    d["until"] = iso(now + timedelta(hours=C.DILEMMA_DURATION_HOURS))
    state.active_dilemma = d
    return d


def expire_dilemma(state: State, now: datetime) -> bool:
    d = state.active_dilemma
    if d and parse_iso(d["until"]) <= now:
        state.active_dilemma = None
        return True
    return False


def fee_multiplier(state: State) -> Decimal:
    d = state.active_dilemma or {}
    return Decimal(d.get("fee_mult", 1))
