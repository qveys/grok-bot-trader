#!/usr/bin/env python3
"""Stateful FAKE revx client for tests. No network, no real orders. State in $FAKE_REVX_STATE."""
import json, os, sys

SP = os.environ["FAKE_REVX_STATE"]
st = json.load(open(SP))
args = sys.argv[1:]
with open(SP + ".calls", "a") as f:
    f.write(" ".join(args) + "\n")


def save():
    json.dump(st, open(SP, "w"), indent=1)


def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default


def bal(cur):
    b = st["balances"].setdefault(cur, {"total": 0.0, "reserved": 0.0})
    return b


def out(x):
    print(json.dumps(x)); save(); sys.exit(0)


def fill(o, q):
    base = o["symbol"].split("/")[0]
    px = float(o["price"]); q = min(q, float(o["quantity"]) - float(o["filled_quantity"]))
    if q <= 0:
        return
    if o["side"] == "sell":
        bal(base)["total"] -= q; bal(base)["reserved"] -= q
        bal("EUR")["total"] += q * px
    else:
        bal(base)["total"] += q; bal("EUR")["total"] -= q * px; bal("EUR")["reserved"] -= q * px
    o["filled_quantity"] = str(float(o["filled_quantity"]) + q)
    o["filled_amount"] = str(float(o["filled_amount"]) + q * px)
    o["status"] = "filled" if float(o["filled_quantity"]) >= float(o["quantity"]) - 1e-12 else "partially_filled"


cmd = " ".join(args[:2])
if cmd == "market ticker":
    pair = args[2]; t = st["ticker"].get(pair)
    if not t:
        sys.exit(1)
    out({"data": [{"symbol": pair.replace("-", "/"), "bid": str(t["bid"]), "ask": str(t["ask"]),
                   "mid": str((t["bid"] + t["ask"]) / 2)}]})
if cmd == "account balances":
    if st.get("fail_balances"):
        sys.exit(1)
    curs = (opt("--currencies") or "").split(",")
    rows = [{"currency": c, "total": str(round(b["total"], 12)), "reserved": str(round(b["reserved"], 12)),
             "available": str(round(b["total"] - b["reserved"], 12))}
            for c, b in st["balances"].items() if not curs[0] or c in curs]
    out(rows)
if cmd in ("order open", "order active"):
    sym = opt("--symbols")
    rows = [o for o in st["orders"].values() if o["status"] in ("new", "partially_filled")
            and (not sym or o["symbol"].replace("/", "-") in sym.split(","))]
    out({"data": rows})
if cmd == "order get":
    o = st["orders"].get(args[2])
    if not o:
        sys.exit(1)
    # a resting order may fill later ("fill_on_get" = fill this order on next get)
    if o["id"] in st.get("fill_on_get", []):
        fill(o, float(o["quantity"])); st["fill_on_get"].remove(o["id"])
    out({"data": o})
if cmd == "order cancel":
    o = st["orders"].get(args[2])
    if not o or o["status"] not in ("new", "partially_filled"):
        sys.exit(1)
    rem = float(o["quantity"]) - float(o["filled_quantity"])
    base = o["symbol"].split("/")[0]
    if o["side"] == "sell":
        bal(base)["reserved"] -= rem
    else:
        bal("EUR")["reserved"] -= rem * float(o["price"])
    o["status"] = "cancelled"; save(); print("cancelled"); sys.exit(0)
if cmd == "order place":
    pair, side = args[2], args[3]
    px = float(opt("--limit"))
    q = float(opt("--qty")) if opt("--qty") else float(opt("--quote")) / px
    base = pair.split("-")[0]
    post = "--post-only" in args
    if side == "sell":
        if bal(base)["total"] - bal(base)["reserved"] < q - 1e-12:
            print("insufficient balance", file=sys.stderr); sys.exit(1)
        bal(base)["reserved"] += q
    else:
        if bal("EUR")["total"] - bal("EUR")["reserved"] < q * px - 1e-9:
            print("insufficient EUR", file=sys.stderr); sys.exit(1)
        bal("EUR")["reserved"] += q * px
    st["seq"] = st.get("seq", 0) + 1
    oid = f"fake-{st['seq']}"
    o = {"id": oid, "client_order_id": opt("--client-order-id"), "symbol": pair.replace("-", "/"), "side": side,
         "quantity": str(q), "price": str(px), "status": "new", "filled_quantity": "0", "filled_amount": "0",
         "post_only": post}
    st["orders"][oid] = o
    mode = st.get("entry_fill", "immediate") if post else st.get("fill_mode", "immediate")
    if mode == "immediate":
        fill(o, q)
    elif mode == "half":
        fill(o, q / 2)
    out({"data": o})
if cmd in ("order history", "trade private"):
    out([])
sys.exit(2)
