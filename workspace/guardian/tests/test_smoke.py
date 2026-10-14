"""Test de fumée hors ligne : python -m pytest tests/ (ou python tests/test_smoke.py)."""
from __future__ import annotations

import os
import random
import sys
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.update({
    "GUARDIAN_MODE": "live", "EXCHANGE": "bitvavo", "BITVAVO_API_KEY": "k", "BITVAVO_API_SECRET": "s",
    "GUARDIAN_API_TOKEN": "t", "GAME_START": "2026-09-01T00:00:00Z",
})

random.seed(7)
from fake_client import FakeClient  # noqa: E402
from guardian import agent, config as C, rules  # noqa: E402
from guardian.api import Mailbox  # noqa: E402
from guardian.guardian import Guardian, Halt  # noqa: E402
from guardian.state import Journal, State, utcnow  # noqa: E402
from guardian.validator import ProposedOrder, validate  # noqa: E402


def make(tmp: Path, prices: dict[str, Decimal]):
    os.environ["GUARDIAN_DATA_DIR"] = str(tmp)
    settings = C.load_settings()
    client = FakeClient(prices)
    state = State.load_or_create(settings.state_path, settings.game_start)
    g = Guardian(settings, client, state, Journal(settings.journal_path), Mailbox(token="t"))
    g.startup_checks()
    return g, client, state


PRICES = {"BTC-EUR": Decimal("40000"), "ETH-EUR": Decimal("2000"), "SOL-EUR": Decimal("100")}


def test_validator_limits():
    with tempfile.TemporaryDirectory() as d:
        g, client, state = make(Path(d), PRICES)
        g.tick()
        tier = rules.current_tier(state)
        assert tier.name.startswith("base")
        ok = validate(ProposedOrder("ETH-EUR", "buy", Decimal("2000"), Decimal("5"), Decimal("0.08")),
                      state, tier, g.markets, g.prices, g.eur, g.s.whitelist, 0)
        assert ok.ok, ok
        too_big = validate(ProposedOrder("ETH-EUR", "buy", Decimal("2000"), Decimal("10"), Decimal("0.08")),
                           state, tier, g.markets, g.prices, g.eur, g.s.whitelist, 0)
        assert too_big.check == "V4"
        off_list = validate(ProposedOrder("DOGE-EUR", "buy", Decimal("1"), Decimal("5"), None),
                            state, tier, g.markets, g.prices, g.eur, g.s.whitelist, 0)
        assert off_list.check == "V1"
        too_small = validate(ProposedOrder("ETH-EUR", "buy", Decimal("2000"), Decimal("1"), None),
                             state, tier, g.markets, g.prices, g.eur, g.s.whitelist, 0)
        assert too_small.check == "V3"


def test_fill_stop_and_death():
    with tempfile.TemporaryDirectory() as d:
        g, client, state = make(Path(d), PRICES)
        g.tick()
        # achat validé et exécuté
        g._execute(ProposedOrder("ETH-EUR", "buy", Decimal("2000"), Decimal("5"), Decimal("0.08")), "t", "test")
        assert len(state.open_orders) == 1
        client.fill(state.open_orders[0]["order_id"])
        g.tick()
        assert len(state.positions) == 1 and not state.open_orders
        pos = state.position_objs()[0]
        assert pos.stop_d == Decimal("1840")
        # le prix touche le stop -> ordre de vente au bid
        client.prices["ETH-EUR"] = Decimal("1800")
        g.tick()
        assert any(o["reason"] == "stop_loss" for o in state.open_orders)
        assert len(state.wakes) >= 1  # réveil stop_hit consommé dans le même tick
        # mort : métabolisme cumulé énorme
        state.metabolism_cumulative = "40"
        try:
            g.tick()
            assert False, "la mort aurait dû être constatée"
        except Halt:
            pass
        assert not state.alive


def test_adopt_initial_holdings():
    with tempfile.TemporaryDirectory() as d:
        os.environ["GUARDIAN_DATA_DIR"] = d
        settings = C.load_settings()
        client = FakeClient(PRICES, eur=Decimal("15.71"))
        client.crypto = {"ETH": Decimal("0.02"), "SOL": Decimal("0.24"), "BTC": Decimal("0.00000656"),
                         "USDC": Decimal("0.03")}
        state = State.load_or_create(settings.state_path, settings.game_start)
        g = Guardian(settings, client, state, Journal(settings.journal_path), Mailbox(token="t"))
        g.startup_checks()
        pos = {p.pair: p for p in state.position_objs()}
        assert set(pos) == {"ETH-EUR", "SOL-EUR"}  # BTC = poussière, USDC hors whitelist
        assert pos["ETH-EUR"].stop_d == Decimal("2000") * (1 - rules.current_tier(state).stop_pct)
        g.tick()
        assert abs(state.score - Decimal("15.71") - Decimal("40") - Decimal("24")) < Decimal("1")
        assert state.alive
        state.save(settings.state_path)
        # état existant (tick déjà fait) : aucune reprise
        state2 = State.load_or_create(settings.state_path, settings.game_start)
        state2.positions = []
        g2 = Guardian(settings, client, state2, Journal(settings.journal_path), Mailbox(token="t"))
        g2.startup_checks()
        assert not state2.positions


def test_metabolism_and_milestone():
    with tempfile.TemporaryDirectory() as d:
        g, client, state = make(Path(d), PRICES)
        g.tick()
        assert Decimal(state.metabolism_cumulative) > 0
        assert Decimal(state.metabolism_rate) == Decimal("0.005")
        state.set_score(Decimal("101"))
        events = rules.check_milestones(state, utcnow())
        assert events == ["milestone_reached:100"]
        assert rules.current_tier(state).name == "100"


def test_wake_and_decision_flow():
    with tempfile.TemporaryDirectory() as d:
        g, client, state = make(Path(d), PRICES)
        g.tick()
        state.active_dilemma = None  # le tirage aléatoire du lundi ne doit pas influencer ce test
        g._open_wake("scheduled", utcnow())
        wake_id = g.mailbox.current_wake()
        assert wake_id and "capital_score" in g.mailbox.snapshot()[1]
        g.mailbox.decisions.put({
            "decision_id": wake_id, "situation": "s", "threats": [],
            "options": [{"label": "hold"}, {"label": "a"}, {"label": "b"}],
            "decision": "buy_eth", "why_better": "w",
            "orders": [{"pair": "ETH-EUR", "side": "buy", "type": "limit",
                        "price": 2000, "amount_eur": 5, "stop_pct": -8}],
        })
        g.tick()
        assert g.mailbox.current_wake() is None
        assert len(state.open_orders) == 1 and state.open_orders[0]["side"] == "buy"


def test_agent_json_parsing():
    raw = '```json\n{"decision_id":"x","situation":"s","threats":[],"options":[{"label":"hold"},{"label":"a"},{"label":"b"}],"decision":"hold","why_better":"w","orders":[]}\n```'
    d = agent._check_shape(agent._extract_json(raw))
    assert d["decision"] == "hold"


def test_revolutx_signature():
    """La signature Ed25519 doit être vérifiable avec la clé publique et suivre le format documenté."""
    import base64
    import tempfile as tf
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from guardian.revolutx import API_PREFIX, RevolutXClient

    sk = Ed25519PrivateKey.generate()
    pem = sk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    with tf.NamedTemporaryFile(suffix=".pem", delete=False) as fh:
        fh.write(pem)
        path = fh.name
    client = RevolutXClient("k" * 64, path)
    ts, method, p_, q, body = 1785313433816, "POST", "/1.0/orders", "", '{"a":"b"}'
    sig = client._sign(ts, method, p_, q, body)
    message = f"{ts}{method}{API_PREFIX}{p_}{q}{body}".encode()
    sk.public_key().verify(base64.b64decode(sig), message)  # lève si invalide


def test_revolutx_endpoint_whitelist():
    from guardian.revolutx import ForbiddenEndpoint, RevolutXClient
    import tempfile as tf
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    sk = Ed25519PrivateKey.generate()
    pem = sk.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                           serialization.NoEncryption())
    with tf.NamedTemporaryFile(suffix=".pem", delete=False) as fh:
        fh.write(pem)
        path = fh.name
    client = RevolutXClient("k" * 64, path)
    try:
        client._request("POST", "/1.0/withdrawals", "/1.0/withdrawals")
        assert False, "endpoint hors liste blanche accepté"
    except ForbiddenEndpoint:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
