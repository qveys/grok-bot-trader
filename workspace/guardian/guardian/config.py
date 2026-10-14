"""Constantes du jeu (source : regles-jeu-grok-trading.md) et chargement de la configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------- Vie et mort
INITIAL_CAPITAL = Decimal("50.00")
DEATH_THRESHOLD = Decimal("20.00")
DANGER_THRESHOLD = Decimal("30.00")
VICTORY_THRESHOLD = Decimal("1000.00")

ADOPT_MIN_EUR = Decimal("1.00")             # poussière : soldes initiaux en dessous ignorés

# ---------------------------------------------------------------- Métabolisme
METABOLISM_BASE = Decimal("0.005")          # 0,50 %/jour mois 1
METABOLISM_MONTHLY_STEP = Decimal("0.001")  # +0,10 % par mois
METABOLISM_MISSED_MILESTONE = Decimal("0.002")
INACTION_DAYS = 3                           # jours sans position ni ordre -> x2

# ---------------------------------------------------------------- Paliers (seuil, deadline en jours)
MILESTONES: tuple[tuple[Decimal, int], ...] = (
    (Decimal("100"), 90),
    (Decimal("250"), 180),
    (Decimal("500"), 270),
    (Decimal("1000"), 365),
)

# ---------------------------------------------------------------- Limites de trading
@dataclass(frozen=True)
class Tier:
    name: str
    risk_per_trade: Decimal       # fraction du capital score
    max_positions: int
    stop_pct: Decimal             # fraction, ex 0.08 = -8 %
    max_crypto_exposure: Decimal  # fraction
    max_orders_per_wake: int


TIER_DANGER = Tier("danger", Decimal("0.03"), 1, Decimal("0.05"), Decimal("0.60"), 2)
TIER_BASE = Tier("base", Decimal("0.05"), 2, Decimal("0.08"), Decimal("0.80"), 3)
TIER_100 = Tier("100", Decimal("0.10"), 3, Decimal("0.08"), Decimal("0.80"), 3)
TIER_250 = Tier("250", Decimal("0.15"), 4, Decimal("0.08"), Decimal("0.80"), 3)

DAILY_LOSS_FREEZE = Decimal("0.06")   # -6 % sur 24 h -> gel des achats
POSITION_MOVE_TRIGGER = Decimal("0.03")
MILESTONE_NEAR_PCT = Decimal("0.05")
MILESTONE_NEAR_DAYS = 7
WAKE_CAP_24H = 12
SCHEDULED_WAKE_HOURS = (0, 6, 12, 18)
LIMIT_ORDER_TTL_HOURS = 6

# ---------------------------------------------------------------- Frais par exchange
FEES = {
    "revolutx": {"maker": Decimal("0"), "taker": Decimal("0.0009")},
    "bitvavo": {"maker": Decimal("0.0015"), "taker": Decimal("0.0025")},
}

# ---------------------------------------------------------------- Dilemmes hebdomadaires
DILEMMAS: tuple[dict, ...] = (
    {"id": 1, "label": "Frais x2 (simulés)", "fee_mult": 2},
    {"id": 2, "label": "Une position doit être fermée avant la fin du dilemme", "force_close_one": True},
    {"id": 3, "label": "Aucun nouvel achat sur BTC-EUR", "no_buy": ["BTC-EUR"]},
    {"id": 4, "label": "Métabolisme x2 pendant 48 h", "metabolism_mult": 2},
    {"id": 5, "label": "Une seule position autorisée", "max_positions": 1},
    {"id": 6, "label": "Stop-loss resserré à -4 %", "stop_pct": "0.04"},
    {"id": 7, "label": "Semaine calme : aucun dilemme"},
)
DILEMMA_DURATION_HOURS = 48

ALWAYS_WHITELISTED = ("BTC-EUR", "ETH-EUR", "SOL-EUR")


# ---------------------------------------------------------------- Settings (env)
@dataclass(frozen=True)
class Settings:
    mode: str                     # dry_run | live | halt
    exchange: str                 # revolutx | bitvavo
    data_dir: Path
    revx_key: str
    revx_private_key_path: str
    bitvavo_key: str
    bitvavo_secret: str
    api_token: str                # token Bearer que le Grok Bot présente au gardien
    api_host: str
    api_port: int
    wake_timeout_minutes: int     # réveil sans réponse -> hold
    whitelist: tuple[str, ...]
    tick_seconds: int
    game_start: str               # ISO 8601, J+0

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def journal_path(self) -> Path:
        return self.data_dir / "journal.log"

    @property
    def prompt_path(self) -> Path:
        return Path(__file__).parent / "prompt_system.txt"


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Variable d'environnement manquante : {name}")
    return value


def load_settings() -> Settings:
    mode = os.environ.get("GUARDIAN_MODE", "dry_run").strip()
    if mode not in ("dry_run", "live", "halt"):
        raise SystemExit(f"GUARDIAN_MODE invalide : {mode}")
    exchange = os.environ.get("EXCHANGE", "revolutx").strip()
    if exchange not in FEES:
        raise SystemExit(f"EXCHANGE invalide : {exchange}")

    extra = tuple(
        p.strip().upper()
        for p in os.environ.get("WHITELIST_EXTRA", "").split(",")
        if p.strip()
    )
    if len(extra) > 4:
        raise SystemExit("WHITELIST_EXTRA : 4 paires maximum")

    if exchange == "revolutx":
        revx_key, revx_pk = _require("REVX_API_KEY"), _require("REVX_PRIVATE_KEY_PATH")
        bv_key = bv_secret = ""
    else:
        revx_key = revx_pk = ""
        bv_key, bv_secret = _require("BITVAVO_API_KEY"), _require("BITVAVO_API_SECRET")

    return Settings(
        mode=mode,
        exchange=exchange,
        data_dir=Path(os.environ.get("GUARDIAN_DATA_DIR", "/var/lib/grok-bot")),
        revx_key=revx_key,
        revx_private_key_path=revx_pk,
        bitvavo_key=bv_key,
        bitvavo_secret=bv_secret,
        api_token=_require("GUARDIAN_API_TOKEN"),
        api_host=os.environ.get("GUARDIAN_API_HOST", "127.0.0.1"),
        api_port=int(os.environ.get("GUARDIAN_API_PORT", "8750")),
        wake_timeout_minutes=int(os.environ.get("GUARDIAN_WAKE_TIMEOUT_MINUTES", "30")),
        whitelist=ALWAYS_WHITELISTED + extra,
        tick_seconds=int(os.environ.get("GUARDIAN_TICK_SECONDS", "60")),
        game_start=_require("GAME_START"),
    )
