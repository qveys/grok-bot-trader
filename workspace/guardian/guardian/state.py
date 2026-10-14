"""État persistant du jeu et journal append-only."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Position:
    pair: str
    qty: str          # Decimal sérialisé
    entry: str        # prix moyen d'entrée
    stop: str         # prix de stop
    opened_at: str

    @property
    def qty_d(self) -> Decimal:
        return Decimal(self.qty)

    @property
    def entry_d(self) -> Decimal:
        return Decimal(self.entry)

    @property
    def stop_d(self) -> Decimal:
        return Decimal(self.stop)


@dataclass
class TrackedOrder:
    order_id: str
    pair: str
    side: str
    amount: str       # base asset
    price: str
    placed_at: str
    stop_pct: str     # fraction demandée par le bot (buy uniquement)
    reason: str       # "agent" | "stop_loss" | "death" | "dilemma"


@dataclass
class State:
    started_at: str
    alive: bool = True
    victory: bool = False
    capital_score: str = "50.00"
    metabolism_cumulative: str = "0"
    metabolism_rate: str = "0.005"
    last_metabolism_date: str = ""          # YYYY-MM-DD
    day_start_score: str = "50.00"
    milestones: dict = field(default_factory=lambda: {"100": None, "250": None, "500": None, "1000": None})
    missed_milestones: int = 0
    positions: list = field(default_factory=list)      # list[Position as dict]
    open_orders: list = field(default_factory=list)    # list[TrackedOrder as dict]
    purchases_frozen_until: str | None = None
    active_dilemma: dict | None = None                 # {..., "until": iso}
    last_dilemma_week: str = ""                        # YYYY-WW
    wakes: list = field(default_factory=list)          # ISO timestamps
    last_scheduled_wake: str = ""                      # YYYY-MM-DDTHH
    last_milestone_wake: str = ""
    last_decision_prices: dict = field(default_factory=dict)
    in_danger: bool = False
    last_activity_date: str = ""                       # dernier jour avec position ou ordre
    last_stop_hit_pending: bool = False
    refused_orders: list = field(default_factory=list) # derniers refus, transmis au bot

    # ------------------------------------------------------------ helpers
    @property
    def score(self) -> Decimal:
        return Decimal(self.capital_score)

    def set_score(self, value: Decimal) -> None:
        self.capital_score = str(value.quantize(Decimal("0.01")))

    def position_objs(self) -> list[Position]:
        return [Position(**p) for p in self.positions]

    def order_objs(self) -> list[TrackedOrder]:
        return [TrackedOrder(**o) for o in self.open_orders]

    def milestones_reached(self) -> list[int]:
        return [int(k) for k, v in self.milestones.items() if v]

    # ------------------------------------------------------------ persistence
    @classmethod
    def load_or_create(cls, path: Path, started_at: str) -> "State":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(**data)
        st = cls(started_at=started_at, last_activity_date=started_at[:10])
        st.save(path)
        return st

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


class Journal:
    HEADER = "timestamp | trigger | capital_score | decision_id | action | pair | amount | validated | reason"

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(self.HEADER + "\n", encoding="utf-8")

    def write(self, trigger: str, capital: Decimal, decision_id: str, action: str,
              pair: str = "-", amount: str = "-", validated: str = "-", reason: str = "-") -> None:
        reason = reason.replace("\n", " ").replace("|", "/")
        line = f"{iso(utcnow())} | {trigger} | {capital:.2f} | {decision_id} | {action} | {pair} | {amount} | {validated} | {reason}\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def tail(self, n: int = 30) -> list[str]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        return lines[-n:] if len(lines) > 1 else []
