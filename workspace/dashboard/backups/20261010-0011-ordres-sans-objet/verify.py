#!/usr/bin/env python3
"""Vérifie la protection du site publié (via le proxy). Le mot de passe est lu dans l'environnement, jamais affiché."""
import base64, json, os, re, sys, urllib.request, urllib.error
# --local : seulement les vérifications locales (fixtures en dossier temporaire, site/ servi en local, Chrome sans proxy).
# Aucun fichier des bots ni de la sonnette n'est touché ; aucun réseau.
LOCAL = "--local" in sys.argv
if LOCAL: sys.argv.remove("--local")
DASH = "/workspace/dashboard"
ok = True

def lline(label, good, info):
    global ok
    ok &= bool(good)
    print(f"{'OK ' if good else 'KO '} {label:<26} {'(local)':<22} -> {info}")

def _build_module():
    """build.py importé sans rien écrire (pas de .pyc) ; main() n'est pas lancé."""
    sys.dont_write_bytecode = True
    if DASH not in sys.path: sys.path.insert(0, DASH)
    import build as B
    return B

UUID_RX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

def local_rules_no_uuid():
    import json as _j, subprocess
    tr = _j.load(open(DASH + "/site/data/summary.json", encoding="utf-8")).get("team_rules") or {}
    hits = UUID_RX.findall(_j.dumps(tr))
    lline("règles: aucun identifiant", not hits, f"{len(hits)} UUID dans team_rules (build)" + (f" · KO {hits[:2]}" if hits else ""))
    rc = subprocess.run([sys.executable, DASH + "/cloudflare/check_secrets.py", DASH + "/site/data"], capture_output=True, text=True)
    lline("check_secrets site/data", rc.returncode == 0, "rien de sensible" if rc.returncode == 0 else rc.stderr.strip()[:200])

def local_live_orders_fixture():
    """state/live_orders.jsonl : les deux formes écrites par live_place.py (achat + sortie auto), parsées dans un dossier
    temporaire ; revx remplacé par des données de test. Rien n'est lu ni écrit dans les vrais fichiers."""
    import json as _j, tempfile, time as _t
    B = _build_module()
    keep = (B.BOT, B.CACHE, B._revx_cached)
    bad = []
    try:
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(td + "/state")
            now = _t.time(); at = lambda m: _t.strftime("%Y-%m-%dT%H:%M:%S+02:00", _t.localtime(now - m * 60))
            entry = {"ok": True, "armed": "test", "at": at(60), "cmd": ["revx", "order", "place", "BTC-EUR", "buy", "--quote", "20", "--limit", "60000",
                     "--post-only", "--json", "--client-order-id", "c-entry-1"], "stdout": _j.dumps({"data": {"id": "o-entry-1", "client_order_id": "c-entry-1", "status": "new"}}),
                     "stderr": "", "returncode": 0, "order": {"pair": "BTC-EUR", "side": "buy", "price": 60000, "amount_eur": 20, "decision_id": "D-900", "id": "pos-900"}}
            refused = {"ok": False, "at": at(50), "cmd": ["revx", "order", "place", "ETH-EUR", "buy", "--client-order-id", "c-ref"], "stdout": "",
                       "stderr": "RAW-STDERR-TRACE /home/box/.config/revx token=abcdefgh12345678", "returncode": 3,
                       "order": {"pair": "ETH-EUR", "side": "buy", "price": 2000, "amount_eur": 20, "decision_id": "D-901"}}
            dry = {"ok": True, "dry_run": True, "at": at(40), "order": {"pair": "SOL-EUR", "side": "buy", "amount_eur": 20}}
            exit_ = {"ok": True, "kind": "auto_exit", "at": at(10), "order": {"pair": "BTC-EUR", "side": "sell", "amount_eur": 19.9, "qty": 0.0003,
                     "price": 61000, "quote_eur": 18.3, "exit_for": "rx-live-pos-900", "linked_position_id": "rx-live-pos-900", "idea_type": "hausse",
                     "close_reason": "stop_hit", "realized_pnl_eur": -1.62, "realized_pnl_gross_eur": -1.6, "fees_eur": 0.02,
                     "fees_detail": {"total_eur": 0.02}, "entry_price": 66000},
                     "realized_pnl_eur": -1.62, "status": "partial",
                     "attempts": [{"attempt": 1, "order_id": "o-exit-a", "client_order_id": "c-exit-a"}, {"attempt": 2, "order_id": "o-exit-b", "client_order_id": "c-exit-b"}],
                     "note": "sortie auto sur stop"}
            with open(td + "/state/live_orders.jsonl", "w", encoding="utf-8") as f:
                for r in (entry, refused, dry, exit_): f.write(_j.dumps(r) + "\n")
            ms = lambda m: int((now - m * 60) * 1000)
            hist = {"data": [
                {"id": "o-entry-1", "client_order_id": "c-entry-1", "symbol": "BTC/EUR", "side": "buy", "filled_quantity": "0.00033", "filled_amount": "20", "created_date": ms(60), "status": "filled"},
                {"id": "o-exit-a", "client_order_id": "c-exit-a", "symbol": "BTC/EUR", "side": "sell", "filled_quantity": "0.0002", "filled_amount": "12.2", "created_date": ms(10), "status": "filled"},
                {"id": "o-exit-b", "client_order_id": "c-exit-b", "symbol": "BTC/EUR", "side": "sell", "filled_quantity": "0.0001", "filled_amount": "6.1", "created_date": ms(9), "status": "filled"},
                {"id": "o-hand-1", "client_order_id": "c-hand", "symbol": "ETH/EUR", "side": "buy", "filled_quantity": "0.01", "filled_amount": "20", "created_date": ms(5), "status": "filled"}]}
            fake = {"revx_order_history.json": hist, "revx_order_open.json": {"data": []}, "revx_transactions.json": {"data": []}}
            B.BOT, B.CACHE = td, td + "/cache"
            B._revx_cached = lambda name, args, timeout=40: (fake[name], False, None)
            h = B.load_real_history()
            bo = h["bot_orders"]; fills = {f["id"]: f for f in h["fills"]}
            if len(bo) != 3: bad.append(f"{len(bo)} ordres de bot (attendu 3, sans l'essai à blanc)")
            ex = next((o for o in bo if o.get("kind") == "auto_exit"), {})
            for k, want in (("status", "partial"), ("quote_eur", 18.3), ("realized_pnl_eur", -1.62), ("realized_pnl_gross_eur", -1.6), ("fees_eur", 0.02), ("decision_id", "D-900")):
                if ex.get(k) != want: bad.append(f"sortie.{k}={ex.get(k)!r}")
            if not ex.get("status_fr"): bad.append("sortie sans libellé")
            rf = next((o for o in bo if o.get("ok") is False), {})
            if not rf.get("error") or "RAW-STDERR" in _j.dumps(h) or "token=" in _j.dumps(h): bad.append("stderr publié")
            for i in ("o-exit-a", "o-exit-b"):
                f = fills.get(i) or {}
                if f.get("origin") != "bot" or not f.get("bot_exit"): bad.append(f"{i} pas relié à la sortie")
            if (fills.get("o-entry-1") or {}).get("decision_link") != "D-900" or (fills.get("o-entry-1") or {}).get("bot_exit"): bad.append("achat pas relié")
            if (fills.get("o-hand-1") or {}).get("origin") != "manuel": bad.append("ordre à la main mal tagué")
            global FIXTURE_TRADES
            FIXTURE_TRADES = {"trades": [dict(t) for t in h["trades"]], "real": {"bot_orders": bo, "open_orders": []}, "cycles": {"list": []}}
    except Exception as e:
        bad.append(f"{type(e).__name__}: {e}")
    finally:
        B.BOT, B.CACHE, B._revx_cached = keep
    lline("sorties réelles: fixtures", not bad, "2 formes (achat + sortie auto) : chiffres tels quels, essais reliés, pas de stderr" if not bad else ", ".join(bad[:5]))

FIXTURE_TRADES = None

# ---- Règles (references/regles-litterature.md, PM-Orchestrator) : référence calculée ici, indépendamment de build.py
RULES_SRC = "/workspace/predict-market-bot/references/regles-litterature.md"
MOIS_AFF = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
_MOIS_PRE = (("janv", 1), ("fév", 2), ("fev", 2), ("mars", 3), ("avr", 4), ("mai", 5), ("juin", 6), ("juil", 7), ("août", 8), ("aout", 8),
             ("sept", 9), ("oct", 10), ("nov", 11), ("déc", 12), ("dec", 12))
def rules_expected():
    import hashlib
    try:
        raw = open(RULES_SRC, "rb").read(); txt = raw.decode("utf-8")
    except Exception as e:
        return {"error": type(e).__name__}
    lines = txt.splitlines()
    title = next((re.sub(r"^#\s+", "", l) for l in lines if re.match(r"^#\s+", l)), "")
    v = re.search(r"version du\s+(\d{1,2})(?:er)?\s+([a-zéèêûôà]+)\.?\s+(\d{4})(?:\s*(?:,|à|a)?\s*(\d{1,2})\s*[h:]\s*(\d{2}))?", title, re.I)
    mois = next((n for pre, n in _MOIS_PRE if v and v.group(2).lower().startswith(pre)), None) if v else None
    want_date, bits = None, []
    if v and mois:   # mois inconnu → pas de date attendue (repli sur la date du fichier), jamais de plantage
        d = int(v.group(1))
        want_date = f"{v.group(3)}-{mois:02d}-{d:02d}"
        bits = [f"{'1er' if d == 1 else d} {MOIS_AFF[mois - 1]}", v.group(3)] + ([f"{int(v.group(4))}h{v.group(5)}"] if v.group(4) else [])
    hl = [i for i, l in enumerate(lines) if re.match(r"^##+\s+", l)]          # mêmes titres que build.py (## et plus)
    heads = [re.sub(r"\*\*|`", "", re.sub(r"^##+\s+", "", lines[i])).strip() for i in hl]
    body = "\n".join(lines[hl[0]:]) if hl else ""
    tags = {k: len(re.findall(r"\((" + w + r")\)", body)) for k, w in (("sim", "Simulation"), ("reel", "R[ée]el"), ("both", "Les deux"))}
    return {"sha": hashlib.sha256(raw).hexdigest(), "mtime": os.path.getmtime(RULES_SRC), "date": want_date, "bits": bits, "heads": heads, "tags": tags}

def rules_freshness(tr, R):
    """(True, '') si la copie a lu la version actuelle ; (False, note) si le fichier a changé depuis < 10 min ; (None, note) sinon."""
    import time as _t
    if tr.get("source_sha256") == R["sha"]: return True, ""
    age = _t.time() - R["mtime"]
    if age < 600: return False, f"fichier modifié il y a {age / 60:.1f} min, après cette copie (comparaison stricte au prochain build)"
    return None, f"copie plus vieille que le fichier (modifié il y a {age / 60:.0f} min)"

def rules_compare(tr, R):
    if not tr.get("available"): return False, "team_rules absent"
    if UUID_RX.search(json.dumps(tr)): return False, "identifiant (UUID) dans les règles"
    strict, note = rules_freshness(tr, R)
    if strict is False: return True, "toléré : " + note
    if strict is None: return False, note
    gs = tr.get("groups") or []; bad = []
    if [g.get("title") for g in gs] != R["heads"]: bad.append("groupes ≠ titres du fichier")
    mains = [(g.get("title"), g.get("scope")) for g in gs if g.get("main")]
    if [m[1] for m in mains] != ["both", "sim", "reel"] or not mains[0][0].startswith("Règles pour les deux") or mains[1][0] != "Simulation" or not mains[2][0].startswith("Réel"): bad.append(f"3 parties du haut {mains}")
    got = {k: sum((g.get("tags") or {}).get(k, 0) for g in gs) for k in R["tags"]}
    if got != R["tags"]: bad.append(f"étiquettes {got} ≠ fichier {R['tags']}")
    if (R["date"] and tr.get("updated_date") != R["date"]) or not all(x in (tr.get("updated_label") or "") for x in R["bits"]): bad.append(f"date {tr.get('updated_label')}")
    return not bad, (", ".join(bad) if bad else f"{len(gs)} groupes (= fichier) · 3 parties du haut · étiquettes {got} · mises à jour le {tr.get('updated_label')}")

RULES_PAGE_JS = r"""() => { const c = document.getElementById('rulescard'); const sec = document.getElementById('regles');
    const t = {}; [...c.querySelectorAll('.inner .rtag')].forEach(x => t[x.dataset.tag] = (t[x.dataset.tag]||0) + 1);
    return {t, mains: [...c.querySelectorAll('details.rmain')].map(d => [d.dataset.scope, d.open]), head: sec ? sec.textContent.slice(0, 200) : '',
            ov: document.documentElement.scrollWidth - innerWidth, html: c.innerHTML, pipes: /\|\s*-{3,}/.test(c.innerText),
            tables: c.querySelectorAll('table.rtab').length}; }"""

def rules_page_problems(m, R, strict):
    bad = []
    if UUID_RX.search(m["html"]): bad.append("identifiant (UUID) visible dans les règles")
    if m["ov"] > 0: bad.append(f"défilement {m['ov']}px")
    if m["pipes"]: bad.append("tableau affiché en texte brut (|---|)")
    if not strict: return bad
    if {k: m["t"].get(k, 0) for k in R["tags"]} != R["tags"]: bad.append(f"pastilles {m['t']}")
    if [x[0] for x in m["mains"]] != ["both", "sim", "reel"] or not all(x[1] for x in m["mains"]): bad.append(f"groupes principaux {m['mains']}")
    if not all(x in m["head"] for x in R["bits"]): bad.append("sous-titre")
    return bad

def local_rules():
    """Règles dans le build local + page locale (1440/768/375 px) : tableaux en vrais tableaux, rien de coupé."""
    from playwright.sync_api import sync_playwright
    R = rules_expected()
    if R.get("error"):
        lline("règles: fichier", False, R["error"]); return
    tr = json.load(open(DASH + "/site/data/summary.json", encoding="utf-8")).get("team_rules") or {}
    good, info = rules_compare(tr, R); lline("règles: build local", good, info)
    strict, note = rules_freshness(tr, R)
    ntab = sum(1 for g in tr.get("groups") or [] for b in g.get("blocks") or [] if b.get("kind") == "table")
    bad = []
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (1440, 768, 375):
            ctx = _local_ctx(br, w, 800); pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/about.html#regles", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                pg.evaluate("() => document.querySelectorAll('#rulescard details').forEach(d => d.open = true)")
                m = pg.evaluate(RULES_PAGE_JS)
                bad += [f"{w}px {x}" for x in rules_page_problems(m, R, strict is True)]
                if m["tables"] != ntab: bad.append(f"{w}px {m['tables']} tableau(x) ≠ {ntab}")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:80]}")
            finally:
                ctx.close()
        br.close()
    lline("règles: page locale", not bad, ", ".join(bad[:4]) if bad else f"{ntab} tableau(x) en vrai tableau · pas d'identifiant · pas de défilement (1440/768/375 px)" + ("" if strict else " · " + note))

# ---- Rendu local : site/ servi par un petit serveur temporaire (127.0.0.1, port libre), Chrome sans proxy.
# Les données peuvent être remplacées à la volée (route Playwright) : les vrais fichiers ne changent pas.
_SRV = None
def _local_base():
    global _SRV
    if _SRV is None:
        import http.server, threading
        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k): super().__init__(*a, directory=DASH + "/site", **k)
            def log_message(self, *a): pass
        _SRV = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=_SRV.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{_SRV.server_address[1]}"

def _local_ctx(br, w, h, patches=None):
    """Contexte Chrome : /api/live répond « indisponible » (le site lit data/*.json) ; patches = {nom: fonction(dict) -> dict}."""
    import json as _j
    ctx = br.new_context(locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": h}, is_mobile=w < 800, has_touch=w < 800)
    ctx.route("**/api/live*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"available": false}'))
    def make(name, fn):
        def handler(route):
            d = _j.load(open(f"{DASH}/site/data/{name}.json", encoding="utf-8"))
            route.fulfill(status=200, content_type="application/json", body=_j.dumps(fn(d)))
        return handler
    for name, fn in (patches or {}).items():
        ctx.route(f"**/data/{name}.json*", make(name, fn))
    return ctx

def _chrome(p):
    return p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)

def local_render_exits():
    """Page Trades avec les fixtures de sorties : une ligne par sortie (montant reçu, état en clair), pas de doublon."""
    if not FIXTURE_TRADES:
        lline("sorties réelles: page", False, "fixtures absentes"); return
    from playwright.sync_api import sync_playwright
    def patch(d):
        d = dict(d); d["trades"] = list(d.get("trades") or []) + FIXTURE_TRADES["trades"]
        d["real"] = dict(d.get("real") or {}, bot_orders=FIXTURE_TRADES["real"]["bot_orders"]); return d
    want_fills = sum(1 for t in FIXTURE_TRADES["trades"] if t.get("kind") == "fill" and not t.get("bot_exit"))
    bad = []; info = ""
    with sync_playwright() as p:
        br = _chrome(p)
        for w, h in ((1440, 900), (375, 800)):
            ctx = _local_ctx(br, w, h, {"trades": patch})
            pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/trades.html", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(800)
                m = pg.evaluate("""() => { const b = [...document.querySelectorAll('.ttable .badge')];
                    return {exit: b.filter(x => /^Sortie automatique/.test(x.title)).map(x => x.textContent.trim()),
                            fills: [...document.querySelectorAll('.ttable tr.leg')].filter(r => /o-|Rempli/.test(r.innerHTML) && r.querySelector('.badge[title="Rempli (Revolut X)"]')).length,
                            txt: document.getElementById('app').innerText, ov: document.documentElement.scrollWidth - innerWidth}; }""")
                if len(m["exit"]) != 1 or "En partie" not in m["exit"][0]: bad.append(f"{w}px sortie {m['exit']}")
                if "reçus" not in m["txt"] or "net" not in m["txt"]: bad.append(f"{w}px montant reçu / net absent")
                if "Ordre refusé par Revolut X (code 3)" not in m["txt"] or "RAW-STDERR" in m["txt"]: bad.append(f"{w}px refus")
                if m["ov"] > 0: bad.append(f"{w}px défilement {m['ov']}px")
                info = f"sortie « {m['exit'][0] if m['exit'] else '?'} » · montant reçu affiché · refus en clair"
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:80]}")
            finally:
                ctx.close()
        br.close()
    lline("sorties réelles: page", not bad, ", ".join(bad) if bad else info)

def run_local_checks():
    local_rules_no_uuid()
    local_live_orders_fixture()
    for f in LOCAL_EXTRA: f()

def local_render_live_totals():
    """Performance › Argent réel : totaux.live de performance.json (PM-Compound) tels quels ; absent → « pas évalué »."""
    import json as _j
    from playwright.sync_api import sync_playwright
    perf = _j.load(open(DASH + "/site/data/performance.json", encoding="utf-8"))
    L = (((perf.get("team_perf") or {}).get("raw") or {}).get("totaux") or {}).get("live")
    def drop(d):
        d = _j.loads(_j.dumps(d)); ((d.get("team_perf") or {}).get("raw") or {}).get("totaux", {}).pop("live", None); return d
    bad = []
    with sync_playwright() as p:
        br = _chrome(p)
        for tag, patches in (("fichier", None), ("absent", {"performance": drop})):
            ctx = _local_ctx(br, 375, 800, patches); pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/performance.html#reel", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                m = pg.evaluate("() => { const e = document.getElementById('live-totals'); return {t: e ? e.innerText : null, ov: document.documentElement.scrollWidth - innerWidth}; }")
                t = m["t"] or ""
                if tag == "absent" or not L:   # bloc toujours affiché (même place) : chaque chiffre → « pas évalué »
                    vals = pg.evaluate("() => [...document.querySelectorAll('#live-totals .card .mono, #live-totals .stat-v, #live-totals .val')].map(x => x.innerText.trim())")
                    if t.count("pas évalué") < 7: bad.append(f"{tag}: « pas évalué » manquant ({t.count('pas évalué')}/7)")
                else:
                    first = t.split("\n")[1].strip() if "\n" in t else ""
                    if L.get("trades") is not None and first != str(L["trades"]): bad.append(f"trades affiché {first!r} ≠ {L.get('trades')}")
                    if L.get("taux_reussite") is None and "pas évalué" not in t: bad.append("taux absent sans « pas évalué »")
                if m["ov"] > 0: bad.append(f"{tag}: défilement {m['ov']}px")
            except Exception as e:
                bad.append(f"{tag} {type(e).__name__}: {str(e)[:80]}")
            finally:
                ctx.close()
        br.close()
    lline("réel: totaux.live Compound", not bad, ", ".join(bad) if bad else f"trades {(L or {}).get('trades')} · net {(L or {}).get('net_eur')} · taux {(L or {}).get('taux_reussite')} (tels quels) ; absent → « pas évalué »")

def local_render_night():
    """Bandeau « Nuit sans décision » (Accueil) : rendu avec des données injectées (true / null / false), heures = detail.debut/fin."""
    import json as _j
    from playwright.sync_api import sync_playwright
    det = {"nuit": "2026-10-08", "date": "2026-10-08", "fenetre": "22h–09h", "debut": "2026-10-08T23:30:00+02:00", "fin": "2026-10-09T08:15:00+02:00", "decisions": []}
    det_nofen = {k: v for k, v in det.items() if k not in ("fenetre", "date")}
    def mk(v, dd=det):
        def f(d):
            d = _j.loads(_j.dumps(d)); so = d.setdefault("sonnette", {}); so["night_sans_decision"] = v; so["night_sans_decision_detail"] = dd; return d
        return f
    bad = []
    with sync_playwright() as p:
        br = _chrome(p)
        for v in (True, "repli", None, False):
            for w in (1440, 375):
                ctx = _local_ctx(br, w, 800, {"summary": mk(True, det_nofen) if v == "repli" else mk(v)}); pg = ctx.new_page()
                try:
                    pg.goto(_local_base() + "/index.html", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                    m = pg.evaluate("""() => { const r = document.getElementById('nuit-sans-decision'), n = document.getElementById('nuit-pas-evaluee');
                        return {red: r ? r.innerText : null, redCls: r ? r.className : '', note: n ? n.innerText : null, ov: document.documentElement.scrollWidth - innerWidth}; }""")
                    if v is True:
                        if not m["red"] or "err" not in m["redCls"] or "« Nuit sans décision » — la nuit dernière (8 oct.), 22h–09h" not in m["red"] or "23h30" in m["red"]: bad.append(f"vrai {w}px: {m['red']!r}")
                        if m["note"]: bad.append(f"vrai {w}px: note en trop")
                    elif v == "repli":
                        if not m["red"] or "la nuit dernière (8 oct.), 23h30–8h15" not in m["red"]: bad.append(f"repli {w}px: {m['red']!r}")
                    elif v is None:
                        if m["red"] or not m["note"] or "pas évaluée" not in m["note"].lower(): bad.append(f"null {w}px: {m}")
                    else:
                        if m["red"] or m["note"]: bad.append(f"faux {w}px: bandeau affiché")
                    if m["ov"] > 0: bad.append(f"{v} {w}px défilement {m['ov']}px")
                except Exception as e:
                    bad.append(f"{v} {w}px {type(e).__name__}: {str(e)[:80]}")
                finally:
                    ctx.close()
        br.close()
    lline("bandeau nuit: rendu", not bad, ", ".join(bad[:4]) if bad else "vrai → « Nuit sans décision » — la nuit dernière (8 oct.), 22h–09h (date + fenêtre écrites) · sans fenêtre → debut/fin 23h30–8h15 · null → note neutre · faux → rien (1440 et 375 px)")

def local_no_hscroll():
    """Aucun défilement horizontal (ni page, ni bloc intérieur) à 375 / 768 / 1000 / 1440 px ; rien ne dépasse de l'écran.
    (body n'a plus overflow-x:hidden : un dépassement se voit donc vraiment ici.)"""
    from playwright.sync_api import sync_playwright
    pages = ["/index.html#apercu", "/index.html#sonnette", "/trades.html", "/performance.html#reel", "/performance.html#tests", "/research.html#decisions", "/research.html#journaux", "/about.html#regles"]
    JS = """() => { const vw = document.documentElement.clientWidth;
      const out = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.right > vw + 1; }).length;
      const inner = [...document.querySelectorAll('body *')].filter(e => /auto|scroll/.test(getComputedStyle(e).overflowX) && e.scrollWidth > e.clientWidth + 1).length;
      const css = getComputedStyle(document.body).overflowX;
      return {doc: document.documentElement.scrollWidth - vw, out, inner, css}; }"""
    bad = []
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (375, 768, 1000, 1440):
            ctx = _local_ctx(br, w, 900)
            for u in pages:
                pg = ctx.new_page()
                try:
                    pg.goto(_local_base() + u, wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
                    m = pg.evaluate(JS)
                    if m["css"] == "hidden": bad.append(f"{w}px body overflow-x:hidden")
                    if m["doc"] > 0 or m["out"] or m["inner"]: bad.append(f"{w}px {u} {m}")
                except Exception as e:
                    bad.append(f"{w}px {u} {type(e).__name__}")
                finally:
                    pg.close()
            ctx.close()
        br.close()
    lline("pas de défilement horizontal", not bad, ", ".join(bad[:3]) if bad else f"{len(pages)} pages × 375/768/1000/1440 px : rien ne dépasse")

# ---- Lot 2 : chiffres écrits par PM-Risk / la sonnette, affichés tels quels (aucun calcul du site)
GUARD = "/workspace/predict-market-bot/guardian/state.json"
def _rappro_page(patch):
    """Texte des 3 valeurs du contrôle Revolut X sur l'Accueil (375 px), avec summary.json modifié par patch."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = _chrome(p); ctx = _local_ctx(br, 375, 800, {"summary": patch} if patch else None); pg = ctx.new_page()
        try:
            pg.goto(_local_base() + "/index.html#apercu", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
            return pg.evaluate("""() => { const r = document.getElementById('rappro'); if (!r) return null;
                const v = {}; r.querySelectorAll('[data-k]').forEach(x => v[x.dataset.k] = x.innerText.trim());
                return {present: r.dataset.present, v, txt: r.innerText, ov: document.documentElement.scrollWidth - innerWidth}; }""")
        finally:
            ctx.close(); br.close()

def local_rappro():
    """Contrôle avec Revolut X = guardian/state.json → rapprochement_revolut (PM-Risk), tel quel ; absent → « pas évalué »."""
    import json as _j
    bj = _j.load(open(DASH + "/site/data/summary.json", encoding="utf-8"))
    R = (bj.get("paper") or {}).get("rapprochement") or {}
    try: G = _j.load(open(GUARD, encoding="utf-8")).get("rapprochement_revolut")
    except Exception: G = None
    bad = []
    if "reconciliation" in (bj.get("paper") or {}): bad.append("ancienne somme du site encore là")
    src = open(DASH + "/build.py", encoding="utf-8").read() + open(DASH + "/src/app.js", encoding="utf-8").read()
    if any(x in src for x in ("def _sum(rows", "sum_eur", "gap_eur")): bad.append("code de somme encore présent")
    if R.get("raw") != G:
        same_t = isinstance(G, dict) and isinstance(R.get("raw"), dict) and str(G.get("controle_at")) > str(R["raw"].get("controle_at"))
        if not same_t: bad.append(f"build {R.get('raw')} ≠ fichier {G}")
    def fx(rr):
        def f(d):
            d = _j.loads(_j.dumps(d)); pp = d.setdefault("paper", {})
            pp["rapprochement"] = {"present": rr is not None, "raw": rr, "source": "fixture"}; return d
        return f
    cases = [("fichier", None, None), ("absent", fx(None), None),
             ("simulation", fx({"gain_equipe_eur": 0, "gain_revolut_eur": "sans objet", "ecart_eur": "sans objet", "controle_at": "2026-10-09T15:48:29+02:00", "mode": "simulation"}), None),
             ("réel", fx({"gain_equipe_eur": 1.23, "gain_revolut_eur": 1.2, "ecart_eur": 0.03, "controle_at": "2026-10-09T15:48:29+02:00", "mode": "live"}), None)]
    for tag, patch, _ in cases:
        try: m = _rappro_page(patch)
        except Exception as e: bad.append(f"{tag} {type(e).__name__}"); continue
        if not m: bad.append(f"{tag}: bloc absent"); continue
        if m["ov"] > 0: bad.append(f"{tag}: défilement")
        v = m["v"]
        if tag == "absent":
            if m["present"] != "false" or "pas évalué" not in m["txt"]: bad.append("absent: « pas évalué » manquant")
        elif tag == "simulation":
            if v.get("gain_revolut_eur") != "sans objet (simulation)" or v.get("ecart_eur") != "sans objet (simulation)" or v.get("gain_equipe_eur") not in ("0,00 €", "+0,00 €", "+ 0,00 €"): bad.append(f"simulation: {v}")
        elif tag == "réel":
            if "1,23" not in v.get("gain_equipe_eur", "") or "1,20" not in v.get("gain_revolut_eur", "") or "0,03" not in v.get("ecart_eur", ""): bad.append(f"réel: {v}")
        elif isinstance(G, dict):
            for k in ("gain_equipe_eur", "gain_revolut_eur", "ecart_eur"):
                g = (R.get("raw") or {}).get(k)
                if isinstance(g, str) and not v.get(k, "").startswith(g): bad.append(f"fichier {k} {v.get(k)!r} ≠ {g!r}")
                if g is None and v.get(k) != "pas évalué": bad.append(f"fichier {k} manquant sans « pas évalué »")
    lline("contrôle Revolut = Risk", not bad, ", ".join(bad[:4]) if bad else
          f"tel quel : {(R.get('raw') or {}).get('gain_equipe_eur')} / {(R.get('raw') or {}).get('gain_revolut_eur')} / {(R.get('raw') or {}).get('ecart_eur')} · absent → « pas évalué » · « sans objet (simulation) » · réel chiffré (fixtures)")

CYCLE_FIX_ROWS = [
    {"id": "S1", "ts": "2026-10-01T10:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "sell", "idea_type": "baisse", "decision_id": "D-801", "price": 2000.0, "amount_eur": 10.0, "qty": 0.005, "target_price": 1980.0, "safety_price": 2020.0, "cycle_id": "S1"},
    {"id": "B1", "ts": "2026-10-01T11:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "buy", "idea_type": "baisse", "decision_id": "D-801", "price": 1980.0, "amount_eur": 9.9, "qty": 0.005, "cycle_id": "S1", "rebuy_reason": "target", "realized_pnl_eur": 0.0987, "realized_pnl_pct": 0.99, "coins_gained": 0.0},
    {"id": "X1", "ts": "2026-10-02T10:00:00Z", "mode": "paper", "pair": "SOL-EUR", "side": "sell", "idea_type": "baisse", "decision_id": "D-802", "price": 100.0, "amount_eur": 10.0, "qty": 0.1},
    {"id": "X2", "ts": "2026-10-02T11:00:00Z", "mode": "paper", "pair": "SOL-EUR", "side": "buy", "idea_type": "baisse", "kind": "rebuy", "price": 99.0, "amount_eur": 9.9, "qty": 0.1, "rebuy_reason": "target", "realized_pnl_eur": 0.0991, "linked_position_id": "X1"},
    {"id": "H1", "ts": "2026-10-03T10:00:00Z", "mode": "paper", "pair": "SOL-EUR", "side": "buy", "idea_type": "hausse", "decision_id": "D-803", "price": 98.0, "amount_eur": 15.0, "qty": 0.153, "stop_price": 97.0, "cycle_id": "H1"},
    {"id": "H2", "ts": "2026-10-03T11:00:00Z", "mode": "paper", "pair": "SOL-EUR", "side": "sell", "idea_type": "hausse", "decision_id": "D-803", "price": 97.5, "amount_eur": 14.8, "qty": 0.151, "close_reason": "idee_morte", "realized_pnl_eur": -0.195003, "realized_pnl_pct": -1.316, "fees_eur": 0.0147, "cycle_id": "H1"},
    {"id": "H3", "ts": "2026-10-03T11:03:00Z", "mode": "paper", "pair": "SOL-EUR", "side": "sell", "idea_type": "hausse", "decision_id": "D-803", "price": 97.7, "amount_eur": 0.18, "qty": 0.002, "close_reason": "idee_morte_reste", "realized_pnl_eur": -0.00192, "cycle_id": "H1"},
    {"id": "O1", "ts": "2026-10-04T10:00:00Z", "mode": "paper", "pair": "BTC-EUR", "side": "sell", "idea_type": "baisse", "decision_id": "D-804", "price": 74000.0, "amount_eur": 10.0, "qty": 0.000135, "target_price": 73000.0, "safety_price": 74500.0, "cycle_id": "O1"},
    {"id": "R1", "ts": "2026-10-05T10:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "sell", "idea_type": "baisse", "decision_id": "D-805", "price": 2100.0, "amount_eur": 10.0, "qty": 0.0047, "cycle_id": "R1"},
    {"id": "Q1", "ts": "2026-10-06T10:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "sell", "idea_type": "baisse", "decision_id": "D-806", "price": 2050.0, "amount_eur": 10.0, "qty": 0.0049},
    {"id": "Q2", "ts": "2026-10-06T12:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "buy", "idea_type": "baisse", "decision_id": "D-806", "price": 2040.0, "amount_eur": 9.99, "qty": 0.0049, "cycle_id": "Q1", "rebuy_reason": "target", "realized_pnl_eur": 0.049},
    {"id": "R2", "ts": "2026-10-05T12:00:00Z", "mode": "paper", "pair": "ETH-EUR", "side": "buy", "idea_type": "baisse", "decision_id": "D-805", "price": 2110.0, "amount_eur": 9.9, "qty": 0.0047, "cycle_id": "R1", "rebuy_reason": "safety", "realized_pnl_eur": -0.047}]
CYCLE_FIX_G = {"positions": [{"id": "O1", "status": "open", "unrealized_pnl_eur": 0.0413, "unrealized_pnl_pct": 0.41}, {"id": "H1", "status": "closed"}]}
FIXTURE_CYCLES = None

def local_cycles_fixture():
    """Cycles = cycle_id seulement (fixtures) : lignes sans cycle_id jamais regroupées, chiffres tels qu'écrits."""
    global FIXTURE_CYCLES
    B = _build_module(); bad = []
    try:
        C = B.load_cycles([dict(r) for r in CYCLE_FIX_ROWS], CYCLE_FIX_G)
        by = {c["id"]: c for c in C["list"] if not c["single"]}
        legs = sorted((c["cycle_id"] or "-", tuple(g["id"] for g in c["legs"])) for c in C["list"])
        # règle stricte : Q1 (sans cycle_id) reste seule même si Q2 la désigne par cycle_id=Q1
        want = sorted([("S1", ("S1", "B1")), ("-", ("X1",)), ("-", ("X2",)), ("H1", ("H1", "H2", "H3")), ("O1", ("O1",)), ("R1", ("R1", "R2")), ("-", ("Q1",)), ("Q1", ("Q2",))])
        if legs != want: bad.append(f"groupes {legs}")
        if any(len(c["legs"]) != 1 for c in C["list"] if c["single"]): bad.append("ligne sans cycle_id regroupée")
        rows = {r["id"]: r for r in CYCLE_FIX_ROWS}
        for c in C["list"]:
            for g in c["legs"]:
                r = rows[g["id"]]
                for k in ("price", "amount_eur", "qty", "realized_pnl_eur", "realized_pnl_pct", "fees_eur", "coins_gained"):
                    if g.get(k) != r.get(k): bad.append(f"{g['id']}.{k} {g.get(k)} ≠ {r.get(k)}")
        o = by.get("O1") or {}
        if not o.get("open") or o.get("target_price") != 73000.0 or o.get("safety_price") != 74500.0 or o.get("latent_pnl_eur") != 0.0413: bad.append(f"O1 ouvert {o.get('open')} {o.get('target_price')} {o.get('latent_pnl_eur')}")
        if (by.get("H1") or {}).get("open") or (by.get("S1") or {}).get("open"): bad.append("cycle fermé vu ouvert")
        if set(C["used_ids"]) != set(rows): bad.append("lignes oubliées")
        FIXTURE_CYCLES = C
    except Exception as e:
        bad.append(f"{type(e).__name__}: {e}")
    src = open(DASH + "/build.py", encoding="utf-8").read()
    if any(x in src for x in ("open_buys", "def load_sell_first", "SF_REBUY")): bad.append("ancien regroupement deviné encore dans build.py")
    lline("cycles: cycle_id seul", not bad, ", ".join(bad[:4]) if bad else "8 groupes attendus : lignes sans cycle_id seules (même désignées par un autre cycle_id), 3 lignes D-803 ensemble, chiffres tels quels")

def local_render_cycles():
    """Page Trades avec les cycles de test : même numéro pour un cycle, lignes sans cycle_id seules, rachat prévu si ouvert."""
    if not FIXTURE_CYCLES:
        lline("cycles: page", False, "fixtures absentes"); return
    import json as _j
    from playwright.sync_api import sync_playwright
    def patch(d):
        d = dict(d); d["cycles"] = FIXTURE_CYCLES; d["trades"] = [t for t in d.get("trades") or [] if t.get("mode") != "sim"]; return d
    bad = []
    with sync_playwright() as p:
        br = _chrome(p)
        for w, h in ((1440, 900), (375, 800)):
            ctx = _local_ctx(br, w, h, {"trades": patch}); pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/trades.html", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(700)
                m = pg.evaluate("""() => [...document.querySelectorAll('.ttable tr.leg')].map(r => ({id: r.dataset.id || null, cy: r.dataset.cycle || null, num: r.dataset.num,
                    pend: !!r.dataset.pending, step: (r.querySelector('td[data-label="Trade"]')||{}).innerText || '', res: (r.querySelector('td[data-label="Résultat"]')||{}).innerText || ''}))""")
                num = {}
                for r in m:
                    if r["id"]: num[r["id"]] = r["num"]
                if len({num.get(i) for i in ("S1", "B1")}) != 1 or len({num.get(i) for i in ("H1", "H2", "H3")}) != 1 or len({num.get(i) for i in ("R1", "R2")}) != 1: bad.append(f"{w}px cycle coupé")
                if num.get("X1") == num.get("X2") or num.get("Q1") == num.get("Q2") or any("/" in r["step"] for r in m if r["id"] in ("X1", "X2", "Q1")): bad.append(f"{w}px lignes sans cycle_id regroupées")
                if not any(r["pend"] and r["cy"] == "O1" for r in m): bad.append(f"{w}px rachat prévu absent")
                h2 = next((r["res"] for r in m if r["id"] == "H2"), "")
                if "0,20" not in h2 and "0,195" not in h2: bad.append(f"{w}px H2 résultat {h2!r}")
                if pg.evaluate("document.documentElement.scrollWidth - innerWidth") > 0: bad.append(f"{w}px défilement")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:80]}")
            finally:
                ctx.close()
        br.close()
    lline("cycles: page", not bad, ", ".join(bad[:4]) if bad else "un numéro par cycle_id · lignes sans cycle_id seules · rachat prévu affiché (1440 et 375 px)")

SONN = "/workspace/tools/sonnette/state/status.json"
def _zones_pages(patch, snap):
    """(snap = summary.json lu une seule fois : la boucle de build peut le réécrire entre deux pages.) Écarts affichés : Accueil › Sonnette ([data-gap=id]) et Analyses › Prévisions (tr[data-zone=id] [data-gap]) + état."""
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (1440, 375):
            ctx = _local_ctx(br, w, 900, {"summary": lambda d, f=patch: (f or (lambda x: x))(json.loads(json.dumps(snap)))}); pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/index.html#sonnette", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                home = pg.evaluate("() => { const o = {}, e = {}; document.querySelectorAll('#zones-distance [data-gap]').forEach(x => o[x.dataset.gap] = x.innerText.trim()); document.querySelectorAll('#zones-distance [data-etat]').forEach(x => e[x.dataset.etat] = x.innerText.trim()); return {gaps: o, etats: e, txt: (document.getElementById('zones-distance')||{}).innerText || ''}; }")
                pg.goto(_local_base() + "/research.html#predict", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                res = pg.evaluate("""() => { const o = {}; document.querySelectorAll('#zonesbox tr[data-zone]').forEach(r => o[r.dataset.zone] = {gap: r.querySelector('[data-gap]').innerText.trim(), etat: r.querySelector('[data-etat]').innerText.trim()});
                    return {rows: o, ov: document.documentElement.scrollWidth - innerWidth}; }""")
                out[w] = (home, res)
            finally:
                ctx.close()
        br.close()
    return out

def local_zones():
    """Écart des zones = ecart_pct de la sonnette, même valeur sur Accueil et Analyses ; état seulement s'il est écrit."""
    import json as _j
    bj = _j.load(open(DASH + "/site/data/summary.json", encoding="utf-8"))
    zb = ((bj.get("sonnette") or {}).get("zones_distance") or {}).get("paires") or {}
    try: so = _j.load(open(SONN, encoding="utf-8"))
    except Exception: so = {}
    bad, note = [], ""
    # même lecture que build.py (load_sonnette), comparée au fichier lu au même instant (réessai si la sonnette réécrit entre-temps)
    B = _build_module()
    for _ in range(5):
        so = _j.load(open(SONN, encoding="utf-8")); got = B.load_sonnette(); so2 = _j.load(open(SONN, encoding="utf-8"))
        if so.get("heartbeat") == so2.get("heartbeat"): break
    gp = (got.get("zones_distance") or {}).get("paires") or {}
    for k, v in ((so.get("zones_distance") or {}).get("paires") or {}).items():
        for side in ("dessous", "dessus"):
            if ((gp.get(k) or {}).get(side) or {}).get("ecart_pct") != (v.get(side) or {}).get("ecart_pct"): bad.append(f"{k}.{side} ≠ status.json")
            if ((gp.get(k) or {}).get(side) or {}).get("etat") != (v.get(side) or {}).get("etat"): bad.append(f"{k}.{side}.etat ≠ status.json")
        if v.get("etat") is not None and (gp.get(k) or {}).get("etat") != v.get("etat"): bad.append(f"{k}.etat ≠ status.json")
    js = open(DASH + "/src/app.js", encoding="utf-8").read()
    if "(z.price - px)" in js or "px >= z.price" in js: bad.append("écart encore calculé dans le navigateur")
    want = {side["id"]: side["ecart_pct"] for v in zb.values() for side in (v.get("dessous"), v.get("dessus")) if side and side.get("id")}
    fmt = lambda x: "pas évalué" if x is None else ((str(int(x)) if float(x).is_integer() else repr(x)).replace(".", ",") + " %")   # tel qu'écrit, sans arrondi
    def with_etat(d):
        d = _j.loads(_j.dumps(d)); P = ((d.get("sonnette") or {}).get("zones_distance") or {}).get("paires") or {}
        for v in P.values():
            if v.get("dessous"): v["dessous"]["etat"] = "dedans"
            if v.get("dessus"): v["dessus"].pop("etat", None)
        return d
    try:
        for tag, patch in (("fichier", None), ("état écrit", with_etat)):
            for w, (home, res) in _zones_pages(patch, bj).items():
                if res["ov"] > 0: bad.append(f"{tag} {w}px défilement")
                for zid, gap in want.items():
                    if home["gaps"].get(zid) != fmt(gap): bad.append(f"{w}px accueil {zid} {home['gaps'].get(zid)!r} ≠ {fmt(gap)!r}")
                    if zid in res["rows"] and res["rows"][zid]["gap"] != home["gaps"].get(zid): bad.append(f"{w}px {zid} pas le même écart sur les 2 pages")
                P = ((patch or (lambda x: x))(_j.loads(_j.dumps(bj))).get("sonnette") or {}).get("zones_distance") or {}
                wet = {sd["id"]: sd.get("etat") for v in (P.get("paires") or {}).values() for sd in (v.get("dessous"), v.get("dessus")) if sd and sd.get("id")}
                for zid, et in wet.items():
                    exp = "pas évalué" if et in (None, "") else et   # tel qu'écrit
                    if home["etats"].get(zid) != exp: bad.append(f"{tag} {w}px accueil {zid} état {home['etats'].get(zid)!r} ≠ {exp!r}")
                    if zid in res["rows"] and res["rows"][zid]["etat"] != exp: bad.append(f"{tag} {w}px analyses {zid} état {res['rows'][zid]['etat']!r} ≠ {exp!r}")
                for zid, r in res["rows"].items():
                    if zid not in want and r["gap"] != "pas évalué": bad.append(f"{w}px {zid} écart inventé {r['gap']!r}")
                    if zid not in wet and r["etat"] != "pas évalué": bad.append(f"{w}px {zid} état inventé {r['etat']!r}")
    except Exception as e:
        bad.append(f"{type(e).__name__}: {str(e)[:100]}")
    lline("zones: écart = sonnette", not bad, ", ".join(bad[:4]) if bad else f"{len(want)} écart(s) + état (dedans / au-dessus / en dessous) de status.json, tels quels et identiques Accueil / Analyses ; côté sans état et autres zones → « pas évalué » ; état injecté affiché tel quel" + note)

def local_no_defaults():
    """Plus de valeurs inventées : objectifs go/no-go, seuil / intervalle du réveil mouvement, multiple d'espérance.
    Champ absent → « pas évalué » (ou —) à l'écran ; présent → valeur du fichier."""
    import json as _j
    from playwright.sync_api import sync_playwright
    js = open(DASH + "/src/app.js", encoding="utf-8").read(); bsrc = open(DASH + "/build.py", encoding="utf-8").read()
    bad = [x for x in ("|| 0.08", "(g.min_win_rate || 0)", "seuil_pct || 0.5", "intervalle_min_min || 30", '"0.5"', "aujourd_hui || 0") if x in js]
    if 'expectancy_min_multiple_of_cost", 3)' in bsrc: bad.append("build.py défaut 3")
    if (_j.load(open(DASH + "/site/data/summary.json", encoding="utf-8")).get("rules") or {}).get("expectancy_multiple") != \
       ((_j.load(open("/workspace/predict-market-bot/config.json", encoding="utf-8")).get("official_rules") or {}).get("expectancy_min_multiple_of_cost")): bad.append("multiple d'espérance ≠ config")
    G = _j.load(open("/workspace/predict-market-bot/config.json", encoding="utf-8")).get("go_nogo") or {}
    def no_goals(d): d = _j.loads(_j.dumps(d)); d["go_nogo"] = {}; return d
    def no_mv(d):
        d = _j.loads(_j.dumps(d)); mv = (d.get("sonnette") or {}).get("mouvement")
        if isinstance(mv, dict):
            for k in ("seuil_pct", "intervalle_min_min", "aujourd_hui"): mv[k] = None
            mv["actif"] = True
        return d
    goal_txt = lambda pg: pg.evaluate("() => [...document.querySelectorAll('[data-goal]')].map(x => x.innerText)")
    with sync_playwright() as p:
        br = _chrome(p)
        try:
            for tag, patches in (("fichier", None), ("absent", {"performance": no_goals})):
                ctx = _local_ctx(br, 375, 800, patches); pg = ctx.new_page()
                pg.goto(_local_base() + "/performance.html#simulation", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
                t = goal_txt(pg); ctx.close()
                if len(t) != 3: bad.append(f"{tag}: {len(t)} objectif(s)"); continue
                if tag == "absent":
                    if not all("pas évalué" in x for x in t) or any("8 %" in x for x in t): bad.append(f"absent: {t}")
                else:
                    if G.get("min_trades") is not None and f"/ {G['min_trades']}" not in t[0]: bad.append(f"min_trades {t[0]!r}")
                    if G.get("min_win_rate") is not None and f"{round(G['min_win_rate'] * 100)} %" not in t[1].replace("\u202f", " ").replace("\xa0", " "): bad.append(f"min_win_rate {t[1]!r}")
                    if G.get("max_drawdown_pct") is not None and f"{round(G['max_drawdown_pct'] * 100)} %" not in t[2].replace("\u202f", " ").replace("\xa0", " "): bad.append(f"max_drawdown {t[2]!r}")
            ctx = _local_ctx(br, 375, 800, {"summary": no_mv}); pg = ctx.new_page()
            pg.goto(_local_base() + "/index.html#apercu", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
            mt = pg.evaluate("() => (document.getElementById('cycle-mouvement') || {}).innerText || ''"); ctx.close()
            if not mt: bad.append("carte réveil mouvement absente")
            elif ("seuil pas évalué" not in mt or "délai pas évalué" not in mt or "aujourd’hui : pas évalué" not in mt or "30 min" in mt or "0,5 %" in mt): bad.append(f"réveil mouvement sans champs : {mt[:160]!r}")
        except Exception as e:
            bad.append(f"{type(e).__name__}: {str(e)[:100]}")
        finally:
            br.close()
    lline("pas de valeur inventée", not bad, ", ".join(bad[:4]) if bad else "objectifs = config.json (absents → « pas évalué ») · seuil / intervalle du réveil = sonnette (absents → « pas évalué ») · multiple d'espérance tel quel")

# ---- Carte « Réveil mouvement » : UNE seule sur le site (Accueil › Cycles automatiques), composant commun des cycles (cycleCard)
MV_PAGES = ["/index.html#apercu", "/index.html#reel", "/index.html#journal", "/index.html#sonnette", "/trades.html", "/performance.html#simulation",
            "/performance.html#reel", "/research.html#predict", "/research.html#decisions", "/about.html#regles"]
MV_JS = r"""() => { const cards = [...document.querySelectorAll('#cycle-mouvement, .mvblock')].concat([...document.querySelectorAll('.cy-name')].filter(x => /mouvement/i.test(x.textContent)).map(x => x.closest('.cy')).filter(c => c && c.id !== 'cycle-mouvement'));
  const c = document.getElementById('cycle-mouvement'); if (!c) return {n: cards.length};
  const lb = c.querySelector('.ledbox'), r = c.getBoundingClientRect(), vw = document.documentElement.clientWidth;
  const lit = lb ? lb.querySelectorAll('.s.on').length + (lb.querySelector('.lw') ? 1 : 0) : 0;
  const col = getComputedStyle(c).getPropertyValue('--c').trim();
  const sib = [...document.querySelectorAll('#cycles .cy')].map(x => Math.round(x.getBoundingClientRect().width));
  return {n: cards.length, shared: c.classList.contains('cy') && !!c.querySelector('[data-led="mouvement"]') && !!c.querySelector('.cy-bar') && !!c.querySelector('.foot'),
    lit, col, word: (lb && lb.querySelector('.lw') || {}).textContent || '', w: Math.round(r.width), vw, cap: (c.querySelector('.cy-next')||{}).textContent || '',
    pairs: [...c.querySelectorAll('[data-mvpair]')].map(x => [x.dataset.mvpair, x.querySelector('b').textContent.trim()]),
    day: (c.querySelector('[data-mvday]')||{}).textContent || '', badge: (c.querySelector('[data-cb="mouvement"]')||{}).textContent || '', txt: c.innerText,
    sib, inGrid: !!c.closest('#cycles'), ov: document.documentElement.scrollWidth - vw}; }"""

def mv_fmt(v):
    if v is None: return "—"
    a = abs(v); t = (str(int(a)) if float(a).is_integer() else repr(a)).replace(".", ",") + " %"
    return ("+" if v > 0 else "−" if v < 0 else "") + t

def mv_card_problems(m, mv, w, page):
    """Problèmes de la carte mouvement mesurée dans Cycles automatiques (m = MV_JS)."""
    bad = []
    if not m.get("shared"): bad.append(f"{w}px pas le composant commun des cycles")
    if not m.get("lit"): bad.append(f"{w}px afficheur vide")
    if not m.get("col"): bad.append(f"{w}px couleur de l'afficheur absente (chiffres invisibles)")
    if w >= 1000 and m.get("w", 0) > 0.5 * m.get("vw", 1): bad.append(f"{w}px carte pleine largeur ({m.get('w')}px)")
    if m.get("sib") and abs(m.get("w", 0) - max(m["sib"])) > 2: bad.append(f"{w}px largeur {m.get('w')} ≠ cartes voisines {sorted(set(m['sib']))}")
    if not m.get("inGrid"): bad.append(f"{w}px pas dans la grille Cycles automatiques")
    if m.get("ov", 0) > 0: bad.append(f"{w}px défilement {m['ov']}px")
    if not re.search(r"prochain réveil possible \(à \d{1,2}h\d{2}\)|prêt : sonne dès|pas encore de décision|désactivé", m.get("cap", "")): bad.append(f"{w}px légende {m.get('cap')!r}")
    if mv:
        want = [[k, mv_fmt((mv.get("mouvement_pct") or {}).get(k))] for k in sorted(((mv.get("reference") or {}).get("prix") or {}))]
        if m.get("pairs") != want: bad.append(f"{w}px mouvements {m.get('pairs')} ≠ sonnette {want}")
        if mv.get("aujourd_hui") is not None and not m.get("day", "").startswith(f"{mv['aujourd_hui']} réveil"): bad.append(f"{w}px compteur du jour {m.get('day')!r}")
    if "Dernier passage".upper() not in m.get("txt", "").upper(): bad.append(f"{w}px pied « Dernier passage » absent")
    if re.search(r"navigateur|≈", m.get("txt", "")): bad.append(f"{w}px jargon dans la carte")
    return bad

def local_mv_card():
    """Carte mouvement : exactement une sur tout le site (Accueil › Cycles automatiques, même taille que ses voisines),
    composant commun, pas de case vide ; « prêt » dans l'afficheur quand le délai est passé (données injectées) ;
    onglet Sonnette = un lien d'une ligne, sans chiffre."""
    import json as _j
    from playwright.sync_api import sync_playwright
    snap = _j.load(open(DASH + "/site/data/summary.json", encoding="utf-8"))
    mv = (snap.get("sonnette") or {}).get("mouvement")
    def ready(d):
        d = _j.loads(_j.dumps(d)); m = (d.get("sonnette") or {}).get("mouvement")
        if m: m["prochain_reveil_possible"] = "2020-01-01T00:00:00+01:00"; m["actif"] = True; m["attente_decision"] = False
        return d
    bad, total = [], {}
    with sync_playwright() as p:
        br = _chrome(p)
        try:
            for w in (375, 768, 1000, 1440):
                ctx = _local_ctx(br, w, 900, {"summary": lambda d: _j.loads(_j.dumps(snap))}); pg = ctx.new_page(); n = 0
                for u in MV_PAGES:
                    pg.goto(_local_base() + u, wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
                    m = pg.evaluate(MV_JS); n += m["n"]
                    if u.endswith("#apercu") and mv: bad += mv_card_problems(m, mv, w, u)
                    if u.endswith("#sonnette"):
                        lk = pg.evaluate("(document.getElementById('mv-link')||{}).innerText || ''")
                        if mv and (not lk or "%" in lk or re.search(r"\d", lk)): bad.append(f"{w}px lien Sonnette {lk!r}")
                total[w] = n
                ctx.close()
            ctx = _local_ctx(br, 1440, 900, {"summary": ready}); pg = ctx.new_page()
            pg.goto(_local_base() + "/index.html#apercu", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(1300)
            m = pg.evaluate(MV_JS); ctx.close()
            if mv and (m.get("word", "").lower() != "prêt" or "Prêt" not in m.get("badge", "") or "prêt : sonne dès" not in m.get("cap", "")): bad.append(f"délai passé : {m.get('word')!r} / {m.get('badge')!r} / {m.get('cap')!r}")
        except Exception as e:
            bad.append(f"{type(e).__name__}: {str(e)[:100]}")
        finally:
            br.close()
    want_n = 1 if mv else 0
    if any(v != want_n for v in total.values()): bad.append(f"cartes sur le site {total} (attendu {want_n})")
    lline("carte mouvement: une seule", not bad, ", ".join(bad[:4]) if bad else
          f"1 carte (Cycles automatiques, taille des voisines) sur {len(MV_PAGES)} pages × 375/768/1000/1440 px · composant commun · afficheur allumé · mouvements = sonnette · « prêt » si délai passé")

PATH_RX = re.compile(r"(?<![\w@])[\w./-]*\w\.(?:jsonl?|md|py)\b|/workspace/")
def local_plain_notes():
    """Notes de source en français simple (chemins de fichiers seulement en info-bulle) ; ordres manuels = « Achat manuel
    (app Revolut, hors bots) » sans ❔, prix seulement s'il est écrit par Revolut X (fixtures)."""
    import json as _j, tempfile
    from playwright.sync_api import sync_playwright
    bad = []
    # 1) build : transaction de l'app Revolut sans prix → None ; avec prix écrit → ce prix, tel quel
    B = _build_module(); keep = (B.BOT, B.CACHE, B._revx_cached)
    try:
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(td + "/state")
            tx = {"data": [{"id": "tx-noprice", "status": "completed", "type": "buy", "source": {"amount": "0.50", "currency": "EUR", "account": {"type": "revolut"}},
                            "destination": {"amount": "0.00000679", "currency": "BTC", "account": {"type": "revolut_x"}}, "created_date": 1791508631285},
                           {"id": "tx-price", "status": "completed", "type": "buy", "price": "73600.5", "source": {"amount": "1.00", "currency": "EUR", "account": {"type": "revolut"}},
                            "destination": {"amount": "0.0000135", "currency": "BTC", "account": {"type": "revolut_x"}}, "created_date": 1791508631999},
                           {"id": "tx-sell-eth", "status": "completed", "type": "sell", "source": {"amount": "0.001", "currency": "ETH", "account": {"type": "revolut_x"}},
                            "destination": {"amount": "2.20", "currency": "EUR", "account": {"type": "revolut"}}, "created_date": 1791508632999}]}
            fake = {"revx_order_history.json": {"data": []}, "revx_order_open.json": {"data": []}, "revx_transactions.json": tx}
            B.BOT, B.CACHE = td, td + "/cache"
            B._revx_cached = lambda name, args, timeout=40: (fake[name], False, None)
            fl = {t["id"]: t for t in B.load_real_history()["trades"]}
            if (fl.get("tx-noprice") or {}).get("price") is not None: bad.append("prix inventé (montant ÷ quantité ?)")
            if (fl.get("tx-price") or {}).get("price") != 73600.5: bad.append(f"prix écrit pas repris : {(fl.get('tx-price') or {}).get('price')}")
            if any((fl.get(i) or {}).get("origin") != "app Revolut" for i in ("tx-noprice", "tx-price")): bad.append("origine")
            FX = [dict(fl["tx-noprice"]), dict(fl["tx-price"]), dict(fl["tx-sell-eth"])]
    except Exception as e:
        bad.append(f"build {type(e).__name__}: {e}"); FX = []
    finally:
        B.BOT, B.CACHE, B._revx_cached = keep
    def patch(d):
        d = dict(d); d["trades"] = list(d.get("trades") or []) + FX; return d
    pages = ["/index.html#apercu", "/index.html#reel", "/index.html#sonnette", "/trades.html", "/performance.html#simulation", "/performance.html#reel",
             "/performance.html#monnaies", "/performance.html#tests", "/research.html#predict", "/research.html#decisions", "/about.html#regles"]
    with sync_playwright() as p:
        br = _chrome(p)
        try:
            for w in (1440, 375):
                ctx = _local_ctx(br, w, 900, {"trades": patch}); pg = ctx.new_page()
                for u in pages:
                    pg.goto(_local_base() + u, wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
                    hits = sorted(set(PATH_RX.findall(pg.evaluate("document.getElementById('app').innerText"))))
                    if hits: bad.append(f"{w}px {u} chemin visible {hits[:3]}")
                    if u == "/trades.html":
                        m = pg.evaluate("""() => ({src: (document.getElementById('trades-sources')||{}).innerText || '',
                            man: [...document.querySelectorAll('.ttable tr.leg')].filter(r => r.querySelector('[data-manual]')).map(r => ({id: r.dataset.id || '',
                              type: r.querySelector('td[data-label="Type"]').innerText, kind: r.querySelector('[data-manual]').dataset.manual,
                              pair: r.querySelector('td[data-label="Paire"]').innerText.trim(), sens: r.querySelector('td[data-label="Sens"]').innerText.trim().toLowerCase(), px: r.querySelector('td[data-label="Prix · heure"]').innerText.split(String.fromCharCode(10))[0].trim()}))})""")
                        if m["src"].strip() != "Simulation : chiffres de PM-Risk · Réel : historique Revolut X.": bad.append(f"{w}px note des sources {m['src']!r}")
                        if not m["man"]: bad.append(f"{w}px aucune ligne « manuel »")
                        for r in m["man"]:
                            want = "🪙 Arrondi Revolut (petite monnaie, hors bots)" if r["kind"] == "arrondi" else "Hors bots (app Revolut)"
                            if "❔" in r["type"] or want not in r["type"] or "Achat manuel" in r["type"]: bad.append(f"{w}px type {r['type']!r}")
                            if r["kind"] == "arrondi" and not (r["pair"] == "BTC-EUR" and r["sens"] == "achat"): bad.append(f"{w}px arrondi sur {r['pair']} {r['sens']}")
                            if r["kind"] != "arrondi" and r["pair"] == "BTC-EUR" and r["sens"] == "achat": bad.append(f"{w}px achat BTC hors bots pas « arrondi »")
                        if FX and not any(r["kind"] == "hors-bots" for r in m["man"]): bad.append(f"{w}px cas « hors bots » (vente ETH) absent")
                        pxs = sorted(r["px"] for r in m["man"])
                        if FX and not any(x.startswith("73") and "600" in x for x in pxs): bad.append(f"{w}px prix écrit absent {pxs}")
                        if FX and "—" not in pxs: bad.append(f"{w}px prix non écrit ≠ « — » {pxs}")
                ctx.close()
        except Exception as e:
            bad.append(f"{type(e).__name__}: {str(e)[:100]}")
        finally:
            br.close()
    lline("notes simples + manuels", not bad, ", ".join(bad[:4]) if bad else
          f"aucun chemin de fichier visible ({len(pages)} pages × 1440/375 px) · « Simulation : chiffres de PM-Risk · Réel : historique Revolut X. » · achat BTC hors bots = « 🪙 Arrondi Revolut », autre = « Hors bots (app Revolut) », sans ❔, prix seulement s'il est écrit")

WALLET_RX = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")
def local_no_wallet():
    """Aucune adresse de portefeuille (0x…) dans les fichiers construits (site/ entier = ce qui part en ligne et dans D1)."""
    hits = []
    for dp, _, fn in os.walk(DASH + "/site"):
        for f in fn:
            try: t = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            except OSError: continue
            if WALLET_RX.search(t): hits.append(os.path.relpath(os.path.join(dp, f), DASH))
    le = (json.load(open(DASH + "/site/data/summary.json", encoding="utf-8")).get("live_equity") or {}).get("metamask") or {}
    lline("pas d'adresse 0x (build)", not hits and "adresse" not in le, "aucune adresse de portefeuille publiée" if not hits else f"KO {hits}")

def local_decision_dups():
    """Numéros D-xxx en double dans le carnet de Predict : KO tant qu'il y en a (pour qu'on le voie), sans bloquer la
    publication (deploy.sh / check_secrets ne lisent pas ce contrôle : l'avertissement orange sur le site est voulu).
    + rendu : deux cartes au même numéro montrées toutes les deux (clés différentes), avertissement sur chaque carte,
    en haut de Décisions écrites et petite note sur Accueil ; sans doublon → aucun avertissement."""
    import json as _j, re as _re
    from playwright.sync_api import sync_playwright
    B = _build_module(); decs = B.parse_decision_log()
    ids = [str(d.get("id") or "").strip() for d in decs if _re.match(r"^D-\d+$", str(d.get("id") or "").strip())]
    dups = sorted({i for i in ids if ids.count(i) > 1}, key=lambda x: int(x[2:]))
    bj = _j.load(open(DASH + "/site/data/summary.json", encoding="utf-8"))
    built = [d["id"] for d in (bj.get("decision_duplicates") or [])]
    lline("décisions: numéros uniques", not dups and built == dups,
          ("en double dans le carnet : " + ", ".join(dups) + " → avertissement orange affiché, Predict doit renuméroter" if dups else "") +
          ("" if built == dups else f" · summary.json dit {built}") if (dups or built != dups) else f"{len(ids)} numéros D-xxx, aucun en double")
    bad = []
    def res_dup(d):
        d = _j.loads(_j.dumps(d)); L = [x for x in d.get("decisions") or [] if _re.match(r"^D-\d+$", str(x.get("id") or ""))]
        if not L: return d
        a = _j.loads(_j.dumps(L[0])); b = _j.loads(_j.dumps(L[0]))
        a.update(id="D-925", key="D-925#1", dup=True, title="Carte A doublon", summary="Carte A doublon", time_text="2026-10-09 15:39")
        b.update(id="D-925", key="D-925#2", dup=True, title="Carte B doublon", summary="Carte B doublon", time_text="2026-10-09 15:40")
        d["decisions"] = [b, a] + [dict(x, dup=False) for x in d["decisions"]]
        d["decision_duplicates"] = [{"id": "D-925", "count": 2, "times": ["2026-10-09 15:39", "2026-10-09 15:40"]}]
        return d
    def sum_dup(d):
        d = _j.loads(_j.dumps(d)); d["decision_duplicates"] = [{"id": "D-925", "count": 2, "times": []}]; return d
    def res_clean(d):
        d = _j.loads(_j.dumps(d)); d["decision_duplicates"] = []; d["decisions"] = [dict(x, dup=False) for x in d.get("decisions") or []]; return d
    def sum_clean(d):
        d = _j.loads(_j.dumps(d)); d["decision_duplicates"] = []; return d
    W = "⚠️ Numéro en double (D-925) : Predict doit le corriger"
    with sync_playwright() as p:
        br = _chrome(p)
        for case, pt in (("doublon", {"research": res_dup, "summary": sum_dup}), ("propre", {"research": res_clean, "summary": sum_clean})):
            for w in (1440, 375):
                ctx = _local_ctx(br, w, 900, pt); pg = ctx.new_page()
                try:
                    pg.goto(_local_base() + "/research.html#decisions", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                    m = pg.evaluate("""() => { const c = [...document.querySelectorAll('#decisions .card.dec')];
                        return {keys: c.map(x => x.dataset.key), d925: c.filter(x => x.dataset.did === 'D-925').map(x => ({t: x.innerText, w: !!x.querySelector('[data-dupwarn]')})),
                                warned: c.filter(x => x.querySelector('[data-dupwarn]')).length, top: (document.getElementById('dec-dup') || {}).innerText || null,
                                ov: document.documentElement.scrollWidth - innerWidth}; }""")
                    pg.goto(_local_base() + "/index.html#apercu", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(500)
                    note = pg.evaluate("() => (document.getElementById('dec-dup-note') || {}).innerText || null")
                    if len(set(m["keys"])) != len(m["keys"]): bad.append(f"{case} {w}px clés en double {m['keys'][:4]}")
                    if case == "doublon":
                        if len(m["d925"]) != 2 or not any("Carte A" in x["t"] for x in m["d925"]) or not any("Carte B" in x["t"] for x in m["d925"]): bad.append(f"{w}px les 2 cartes D-925 pas montrées")
                        if not all(x["w"] and W in x["t"] for x in m["d925"]) or m["warned"] != 2: bad.append(f"{w}px avertissement carte")
                        if not m["top"] or W not in m["top"]: bad.append(f"{w}px avertissement onglet {m['top']!r}")
                        if not note or "D-925" not in note: bad.append(f"{w}px note Accueil {note!r}")
                    else:
                        if m["warned"] or m["top"] or note: bad.append(f"{w}px avertissement sans doublon")
                    if m["ov"] > 0: bad.append(f"{case} {w}px défilement")
                except Exception as e:
                    bad.append(f"{case} {w}px {type(e).__name__}: {str(e)[:80]}")
                finally:
                    ctx.close()
        br.close()
    lline("décisions: rendu doublons", not bad, ", ".join(bad[:4]) if bad else "2 cartes D-925 montrées (clés différentes), « " + W + " » sur chaque carte + en haut de l'onglet + note Accueil ; sans doublon → rien (1440 et 375 px)")

def local_predict_occupe():
    """« Predict occupé » (status.json → predict_occupe) : build = fichier tel quel ; carte Sonnette : phrase seulement si actif === true."""
    import json as _j
    from playwright.sync_api import sync_playwright
    B = _build_module(); bad = []
    for _ in range(5):
        so = _j.load(open(SONN, encoding="utf-8")); got = B.load_sonnette(); so2 = _j.load(open(SONN, encoding="utf-8"))
        if so.get("heartbeat") == so2.get("heartbeat"): break
    po, gp = so.get("predict_occupe"), got.get("predict_occupe")
    if isinstance(po, dict):
        if not gp or gp["actif"] != (po.get("actif") is True) or gp["minutes"] != po.get("minutes") or gp["jusqua_fr"] != po.get("jusqua_fr"): bad.append(f"build ≠ status.json {gp}")
    elif gp is not None: bad.append("build invente predict_occupe")
    def mk(v):
        def f(d):
            d = _j.loads(_j.dumps(d)); sn = d.setdefault("sonnette", {})
            if v is None: sn.pop("predict_occupe", None)
            else: sn["predict_occupe"] = v
            return d
        return f
    cases = (("vrai", {"actif": True, "minutes": 5.0, "jusqua_fr": "17h55", "file": 2}), ("faux", {"actif": False, "minutes": 5.0, "file": 0}), ("absent", None))
    with sync_playwright() as p:
        br = _chrome(p)
        for tag, v in cases:
            for w in (1440, 375):
                ctx = _local_ctx(br, w, 900, {"summary": mk(v)}); pg = ctx.new_page()
                try:
                    pg.goto(_local_base() + "/index.html#sonnette", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                    t = pg.evaluate("() => { const e = document.getElementById('predict-occupe'); return e ? e.innerText : null; }")
                    txt = pg.evaluate("() => document.getElementById('app').innerText")
                    if tag == "vrai":
                        if not t or "⏳ Predict réfléchit : les autres alertes attendent sa décision (5 min max)" not in t or "17h55" not in t or "2 alertes en attente" not in t: bad.append(f"vrai {w}px {t!r}")
                    elif t or "Predict réfléchit" in txt: bad.append(f"{tag} {w}px phrase affichée")
                    if pg.evaluate("document.documentElement.scrollWidth - innerWidth") > 0: bad.append(f"{tag} {w}px défilement")
                except Exception as e:
                    bad.append(f"{tag} {w}px {type(e).__name__}: {str(e)[:80]}")
                finally:
                    ctx.close()
        br.close()
    lline("sonnette: Predict occupé", not bad, ", ".join(bad[:4]) if bad else f"build = status.json ({'actif' if (po or {}).get('actif') else 'inactif'}) · vrai → « ⏳ Predict réfléchit : les autres alertes attendent sa décision (5 min max) » · faux / absent → rien (1440 et 375 px)")

DEC_LINES = ["declencheur", "resume", "prix", "place", "reel", "avis", "pourquoi", "revus", "propositions", "valable", "suivi"]
PROP_LINES = ["niveau", "idee", "plan", "prevision", "confiance", "rappel", "decision", "statut"]
DEC_JS = """() => [...document.querySelectorAll('#decisions .card.dec')].map(c => ({did: c.dataset.did, fmt: c.dataset.format, time: c.dataset.time,
    lines: [...c.querySelectorAll(':scope > .dl')].map(x => x.dataset.line).filter(x => x !== 'numero'),
    cancel: !!c.querySelector('[data-cancel]'), old: !!c.querySelector('[data-oldfmt]'),
    resume: ((c.querySelector('.dl[data-line=resume] .dv') || {}).innerText || '').trim(),
    props: [...c.querySelectorAll('.dprop')].map(p => ({id: p.dataset.prop, lines: [...p.querySelectorAll('.dl')].map(x => x.dataset.line),
        dec: ((p.querySelector('.dl[data-line=decision] .dv') || {}).innerText || '').trim(), statut: ((p.querySelector('.dl[data-line=statut] .dv') || {}).innerText || '').trim(),
        conf: ((p.querySelector('.dl[data-line=confiance] .dv') || {}).innerText || '').trim(), plan: ((p.querySelector('.dl[data-line=plan] .dv') || {}).innerText || '').trim()})),
    suivi: ((c.querySelector('.dl[data-line=suivi] .dv') || {}).innerText || '').trim()})).concat([{ov: document.documentElement.scrollWidth - innerWidth}])"""

def _file_props(txt):
    """Lecture indépendante du carnet : sous-titre **D-xxxa — …** → sa propre ligne « - Décision : » (jusqu'à la ligne vide)."""
    out, cur = {}, None
    for ln in txt.splitlines():
        s = ln.strip()
        m = _re_mod.match(r"^\*\*(D-\d+[a-z])\s*[—–-]", s)
        if m: cur = m.group(1); out[cur] = None; continue
        if cur and not s: cur = None; continue
        if cur and out[cur] is None:
            mm = _re_mod.match(r"^-\s*Décision\s*:\s*(.+)$", s)
            if mm: out[cur] = mm.group(1).replace("**", "").strip()
    return out

import re as _re_mod

def _all_decisions_page(pg):
    pg.goto(_local_base() + "/research.html?d=D-002#decisions", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(700)
    return pg.evaluate(DEC_JS)

def local_decisions_real():
    """Décisions écrites (carnet réel de PM-Predict) : cas qui étaient faux en ligne, + même gabarit sur toutes les cartes, plus récente d'abord."""
    import json as _j
    from playwright.sync_api import sync_playwright
    B = _build_module(); ds = {d["id"]: d for d in B.parse_decision_log()}
    txt = open("/workspace/predict-market-bot/knowledge/decision_log.md", encoding="utf-8").read()
    FP = _file_props(txt); bad = []
    d35 = ds.get("D-035")
    if not d35 or not d35.get("time") or len(d35.get("proposals") or []) != 3: bad.append("D-035 absente ou incomplète (titre « 21h39 », sans paire)")
    for did in ("D-024", "D-026", "D-031"):
        pr = (ds.get(did) or {}).get("proposals") or []
        if [x["id"] for x in pr] != [did + l for l in "abc"]: bad.append(f"{did} propositions {[x['id'] for x in pr]}")
    for pid, dec in FP.items():   # chaque proposition garde SA décision (telle qu'écrite)
        got = next((x.get("decision") for d in ds.values() for x in d.get("proposals") or [] if x.get("id") == pid), "∅")
        if dec is not None and got != dec: bad.append(f"{pid} décision {str(got)[:30]!r} ≠ carnet {dec[:30]!r}")
    for did, old in (("D-027", "D-026"), ("D-032", "D-025")):
        d = ds.get(did) or {}
        if d.get("status") != "annulée" or not d.get("title") or d.get("ancien_numero") != old: bad.append(f"{did} annulation/titre/ancien numéro : {d.get('status')}, {d.get('title')!r}, {d.get('ancien_numero')}")
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (1440, 375):
            ctx = _local_ctx(br, w, 900); pg = ctx.new_page()
            try:
                cards = _all_decisions_page(pg); ov = cards.pop()["ov"]
                by = {c["did"]: c for c in cards}
                if "D-035" not in by: bad.append(f"{w}px D-035 pas affichée")
                for c in cards:
                    if c["lines"] != DEC_LINES: bad.append(f"{w}px {c['did']} lignes {c['lines']}"); break
                    if any(pp["lines"] != PROP_LINES for pp in c["props"]): bad.append(f"{w}px {c['did']} lignes de proposition"); break
                for did in ("D-024", "D-026", "D-031"):
                    for pp in (by.get(did) or {}).get("props") or []:
                        want = FP.get(pp["id"])
                        if want and pp["dec"] != want: bad.append(f"{w}px {pp['id']} affiche {pp['dec'][:30]!r}")
                for did in ("D-027", "D-032"):
                    c = by.get(did) or {}
                    if not c.get("cancel") or not c.get("resume") or c.get("resume") == "pas évalué": bad.append(f"{w}px {did} annulée/titre")
                if not all(c["old"] for c in cards if c["fmt"] == "ancien"): bad.append(f"{w}px étiquette « ancien format » manquante")
                ts = [c["time"] for c in cards if c["time"]]
                if ts != sorted(ts, reverse=True): bad.append(f"{w}px pas « plus récente d'abord »")
                if ov > 0: bad.append(f"{w}px défilement {ov}px")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:90]}")
            finally:
                ctx.close()
        br.close()
    lline("décisions: cas réels", not bad, ", ".join(bad[:4]) if bad else f"D-035 affichée · D-024/D-026/D-031 : chaque proposition avec SA décision (= carnet, {sum(1 for v in FP.values() if v)} propositions) · D-027/D-032 annulées avec titre · {len(ds)} cartes, même ordre de lignes, plus récente d'abord (1440 et 375 px)")

TPL_LOG = '''# Carnet
## Entrées

### 2026-10-10 09:15 | BTC-EUR + SOL-EUR | D-901 — Essai du modèle
```json
{"id": "D-901", "heure": "2026-10-10T09:15:00+02:00", "paires": ["BTC-EUR", "SOL-EUR"],
 "declencheur": {"type": "sonnette_zone", "detail": "Z-BTC-75000"}, "resume": "Essai du modèle", "type": "propositions",
 "prix_releves": {"heure": "09:14", "BTC-EUR": 75000, "SOL-EUR": 99.5}, "place_libre_eur": 25, "reel_permis": false, "reel_raison": "hors créneau",
 "avis_research": "pas demandé", "pourquoi": "test",
 "propositions": [
  {"lettre": "a", "niveau": "prudente", "paire": "BTC-EUR", "idee": "à la hausse", "sens": "achat", "montant_eur": 15, "quantite": 0.0002,
   "prix_entree": 75000, "prix_vise": 76000, "prix_arret": 74000, "heure_limite": "2026-10-10T17:00:00+02:00",
   "prevision": "BTC touche 76 000 € avant 74 000 €", "confiance": {"mot": "faible", "pct": 55}, "decision": "simuler", "statut": "proposée"},
  {"lettre": "c", "niveau": "risquée", "paire": "SOL-EUR", "idee": "à la baisse", "sens": "vente", "montant_eur": 10,
   "prix_entree": 99.5, "prix_vise": 97.5, "prix_arret": 100.5, "heure_limite": "2026-10-10T17:00:00+02:00",
   "prevision": "SOL touche 97,5 € avant 100,5 €", "confiance": null, "decision": "simuler_si_place", "statut": "proposée"}],
 "valable_jusqua": "09:45", "statut": "active"}
```

```json
{"suivi": "D-901", "proposition": "a", "heure": "2026-10-10T09:16:00+02:00", "par": "PM-Risk", "statut": "simulée", "texte": "arrêt resserré à 74 100"}
{"suivi": "D-901", "proposition": "c", "heure": "2026-10-10T09:16:00+02:00", "par": "PM-Risk", "statut": "pas_simulée", "texte": "plus de place"}
```

### 2026-10-10 09:30 | BTC-EUR | D-902 — Annulée par suivi
```json
{"id": "D-902", "heure": "2026-10-10T09:30:00+02:00", "paires": ["BTC-EUR"], "declencheur": {"type": "demande_quentin"}, "resume": "Annulée par suivi",
 "type": "pas_de_trade", "pourquoi": "rien", "statut": "active", "ancien_numero": "D-899"}
```
```json
{"suivi": "D-902", "heure": "2026-10-10T09:31:00+02:00", "par": "PM-Predict", "statut": "annulée", "texte": "doublon"}
```
'''

def local_decision_template():
    """Modèle commun (docs/modele-decision.md) : bloc json + blocs de suivi → carte au même gabarit, valeurs telles qu'écrites."""
    import json as _j, tempfile, os as _os
    from playwright.sync_api import sync_playwright
    B = _build_module(); tmp = tempfile.mkdtemp(); _os.makedirs(tmp + "/knowledge")
    open(tmp + "/knowledge/decision_log.md", "w", encoding="utf-8").write(TPL_LOG)
    orig = B.p; B.p = lambda *a: _os.path.join(tmp, *a)
    try: ds = B.parse_decision_log()
    finally: B.p = orig
    bad = []; d1 = next((d for d in ds if d["id"] == "D-901"), None); d2 = next((d for d in ds if d["id"] == "D-902"), None)
    if not d1 or d1["format"] != "modele": bad.append("D-901 pas lu comme modèle")
    else:
        st = {x["lettre"]: x["statut"] for x in d1["proposals"]}
        if st != {"a": "simulée", "c": "pas_simulée"}: bad.append(f"statuts {st}")
        if len(d1["suivi"]) != 2: bad.append(f"suivi {len(d1['suivi'])}")
    if not d2 or d2["status"] != "annulée" or d2.get("ancien_numero") != "D-899": bad.append(f"D-902 {d2 and d2['status']}")
    def inj(d):
        d = _j.loads(_j.dumps(d)); d["decisions"] = sorted(ds, key=lambda x: (x.get("time") or "", x.get("order", 0)), reverse=True) + list(d.get("decisions") or []); return d
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (1440, 375):
            ctx = _local_ctx(br, w, 900, {"research": inj}); pg = ctx.new_page()
            try:
                cards = _all_decisions_page(pg); ov = cards.pop()["ov"]; by = {c["did"]: c for c in cards}
                c1, c2 = by.get("D-901"), by.get("D-902")
                if not c1 or c1["old"] or c1["fmt"] != "modele": bad.append(f"{w}px D-901 format"); continue
                if c1["lines"] != DEC_LINES or any(pp["lines"] != PROP_LINES for pp in c1["props"]): bad.append(f"{w}px D-901 gabarit")
                pa = next((x for x in c1["props"] if x["id"] == "D-901a"), {}); pc = next((x for x in c1["props"] if x["id"] == "D-901c"), {})
                n = lambda t: t.replace("\u202f", " ").replace("\xa0", " ")
                if "simulée" != pa.get("statut", "").lower() or "pas simulée" != pc.get("statut", "").lower(): bad.append(f"{w}px statuts {pa.get('statut')!r}/{pc.get('statut')!r}")
                if pc.get("conf") != "pas évalué" or "faible" not in pa.get("conf", "") or "55" not in pa.get("conf", ""): bad.append(f"{w}px confiance {pa.get('conf')!r}/{pc.get('conf')!r}")
                if "75 000,00 €" not in n(pa.get("plan", "")) or "76 000,00 €" not in n(pa.get("plan", "")) or "74 000,00 €" not in n(pa.get("plan", "")): bad.append(f"{w}px plan {pa.get('plan')!r}")
                if "arrêt resserré à 74 100" not in c1["suivi"]: bad.append(f"{w}px suivi")
                if not c2 or not c2["cancel"]: bad.append(f"{w}px D-902 pas annulée")
                if [c["did"] for c in cards][:2] != ["D-902", "D-901"]: bad.append(f"{w}px ordre {[c['did'] for c in cards][:3]}")
                if ov > 0: bad.append(f"{w}px défilement")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:90]}")
            finally:
                ctx.close()
        br.close()
    lline("décisions: modèle + suivi", not bad, ", ".join(bad[:4]) if bad else "bloc json lu tel quel · suivi PM-Risk → statuts « Simulée » / « Pas simulée » · confiance absente → « pas évalué » · annulation par suivi · même gabarit que les anciennes (1440 et 375 px)")

def _fp(x):   # même arrondi que l'écran (décimal écrit, moitié vers le haut)
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    s = f"{q:,.2f}".replace(",", " ").replace(".", ",") + " €"
    return s

def local_trades_more():
    """Trades simulés : lignes en plus (Départ, Montant, Arrêt · objectif, Fermeture, Décision) = ce que les bots ont écrit ; format du tableau inchangé."""
    import json as _j
    from playwright.sync_api import sync_playwright
    T = _j.load(open(DASH + "/site/data/trades.json", encoding="utf-8"))
    cyc = (T.get("cycles") or {}).get("list") or []
    bad, n_checked = [], 0
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (1440, 375):
            ctx = _local_ctx(br, w, 900); pg = ctx.new_page()
            try:
                pg.goto(_local_base() + "/trades.html", wait_until="networkidle", timeout=30000); pg.wait_for_timeout(700)
                M = pg.evaluate("""() => { const o = {}; document.querySelectorAll('tr.leg-more').forEach(r => { const d = {};
                    r.querySelectorAll('.tm').forEach(t => d[t.dataset.more] = {txt: t.querySelector('.tmv').innerText.replace(/[\\u202f\\xa0]/g, ' '), href: (t.querySelector('a[data-declink]') || {}).href || null});
                    o[r.dataset.moreFor] = d; }); return {more: o, heads: [...document.querySelectorAll('table.ttable thead th')].map(x => x.innerText.trim()),
                    ov: document.documentElement.scrollWidth - innerWidth, unpaired: [...document.querySelectorAll('tr.leg-more')].filter(r => !(r.previousElementSibling && r.previousElementSibling.classList.contains('has-more'))).length}; }""")
                want_heads = ["Trade", "Sens", "Type", "Paire", "Prix · heure", "Montant", "Résultat", "Statut", "Raison · leçon"]
                if w == 1440 and [h.lower() for h in M["heads"]] != [h.lower() for h in want_heads]: bad.append(f"colonnes changées {M['heads']}")
                if M["unpaired"]: bad.append(f"{w}px {M['unpaired']} ligne(s) en plus détachée(s)")
                for c in cyc:
                    legs, P, D = c["legs"], c.get("plan") or {}, c.get("decision")
                    for i, g in enumerate(legs):
                        m = M["more"].get(g["id"]) or {}
                        isc = bool(g.get("close_reason") or g.get("rebuy_reason"))
                        if (i == 0 or isc) and "plan" in m:
                            t = m["plan"]["txt"]; n_checked += 1
                            for lab, val in (("arrêt", P.get("stop")), ("objectif", P.get("target"))):
                                exp = _fp(val) if val is not None else "pas évalué"
                                if f"{lab} {exp}" not in t: bad.append(f"{w}px {g['id'][-8:]} {lab} {t[:60]!r} ≠ {exp}")
                        elif i == 0 or isc: bad.append(f"{w}px {g['id'][-8:]} pas de ligne « Arrêt · objectif »")
                        if i > 0:
                            dep = (m.get("depart") or {}).get("txt", "")
                            if _fp(legs[0]["price"]) not in dep: bad.append(f"{w}px {g['id'][-8:]} départ {dep[:50]!r}")
                            if legs[0].get("amount_eur") is not None and (legs[0]["amount_eur"] is not None) and "montant écrit" not in dep: bad.append(f"{w}px {g['id'][-8:]} montant de départ non étiqueté")
                        if isc:
                            f = (m.get("fermeture") or {}).get("txt", "")
                            if (g.get("reason_fr") or "") not in f or _fp(g["price"]) not in f: bad.append(f"{w}px {g['id'][-8:]} fermeture {f[:60]!r}")
                            cl = c.get("close") or {}
                            if cl.get("leg_id") == g["id"] and cl.get("trigger_price") is not None and "déclenché à " + _fp(cl["trigger_price"]) not in f: bad.append(f"{w}px {g['id'][-8:]} déclenchement")
                        if i == 0 and D:
                            dd = m.get("decision") or {}
                            if not dd.get("txt", "").startswith(D["ref"]) or (D.get("found") and "?d=" + D["id"] not in (dd.get("href") or "")): bad.append(f"{w}px {g['id'][-8:]} lien décision {dd}")
                            for r in D.get("risk") or []:
                                if (r.get("texte") or "")[:40].replace("\u202f", " ") not in dd.get("txt", "") and "fichier" not in dd.get("txt", ""): bad.append(f"{w}px {D['ref']} texte Risk absent"); break
                            if D.get("niveau") and D["niveau"] not in dd.get("txt", ""): bad.append(f"{w}px {D['ref']} niveau")
                c31 = next((c for c in cyc if (c.get("decision") or {}).get("ref") == "D-031a"), None)
                if c31:
                    t = ((M["more"].get(c31["legs"][0]["id"]) or {}).get("decision") or {}).get("txt", "")
                    if "arrêt resserré à 73 120" not in t or "prudente" not in t: bad.append(f"{w}px D-031a validation Risk {t[:80]!r}")
                if M["ov"] > 0: bad.append(f"{w}px défilement {M['ov']}px")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:90]}")
            finally:
                ctx.close()
        br.close()
    lline("trades: infos en plus", not bad, ", ".join(bad[:4]) if bad else f"{len(cyc)} trades simulés : départ, montant étiqueté, arrêt/objectif, fermeture (+ déclenchement écrit), décision cliquable + prévision + Risk = fichiers ({n_checked} lignes contrôlées) · colonnes inchangées (1440 et 375 px)")

def local_perf_parity():
    """Performance : onglets Simulation et Argent réel = mêmes blocs, même ordre, mêmes cases ; chiffres de chaque mode tels qu'écrits."""
    import json as _j
    from playwright.sync_api import sync_playwright
    perf = _j.load(open(DASH + "/site/data/performance.json", encoding="utf-8"))
    TT = (((perf.get("team_perf") or {}).get("raw") or {}).get("totaux") or {})
    js = open(DASH + "/src/app.js", encoding="utf-8").read(); bad = []
    if "function perfSim" in js or "function perfReal" in js: bad.append("ancien code en double (perfSim / perfReal)")
    if js.count('perfMode(P, "sim")') != 1 or js.count('perfMode(P, "reel")') != 1: bad.append("les 2 onglets n'utilisent pas la même fonction")
    J = """() => [...document.querySelectorAll('[data-block]')].map(b => ({k: b.dataset.block, labels: [...b.querySelectorAll('.card .label, th')].map(x => x.innerText.trim()),
        first: ((b.querySelector('.card .mid') || {}).innerText || '').trim(), txt: b.innerText})).concat([{ov: document.documentElement.scrollWidth - innerWidth}])"""
    with sync_playwright() as p:
        br = _chrome(p)
        for w in (375, 1440):
            ctx = _local_ctx(br, w, 900); pg = ctx.new_page(); R = {}
            try:
                for t in ("simulation", "reel"):
                    pg.goto(_local_base() + "/performance.html#" + t, wait_until="networkidle", timeout=30000); pg.wait_for_timeout(600)
                    R[t] = pg.evaluate(J); ov = R[t].pop()["ov"]
                    if ov > 0: bad.append(f"{w}px {t} défilement")
                ks = [[b["k"] for b in R[t]] for t in R]
                if ks[0] != ks[1] or ks[0] != ["resultats", "sens", "portefeuille", "objectifs", "lignes"]: bad.append(f"{w}px blocs {ks}")
                for a, b in zip(R["simulation"], R["reel"]):
                    la = [x for x in a["labels"]]; lb = [x for x in b["labels"]]
                    la = ["Valeur du portefeuille" if x.lower() == "valeur du portefeuille" else x for x in la]
                    lb = ["Valeur du portefeuille" if x.lower() == "capital du bot" else x for x in lb]
                    if [x.lower() for x in la] != [x.lower() for x in lb]: bad.append(f"{w}px bloc {a['k']} cases différentes")
                for t, key in (("simulation", "simulation"), ("reel", "live")):
                    T = TT.get(key); res = R[t][0]
                    exp = str(T["trades"]) if T and T.get("trades") is not None else "pas évalué"
                    if res["first"] != exp: bad.append(f"{w}px {t} trades {res['first']!r} ≠ {exp!r}")
                    if T and T.get("taux_reussite") is None and "pas évalué" not in res["txt"]: bad.append(f"{w}px {t} taux absent sans « pas évalué »")
            except Exception as e:
                bad.append(f"{w}px {type(e).__name__}: {str(e)[:90]}")
            finally:
                ctx.close()
        br.close()
    lline("performance: 2 onglets pareils", not bad, ", ".join(bad[:4]) if bad else "Simulation et Argent réel : 5 blocs dans le même ordre (résultats, par sens, portefeuille, objectifs, lignes), mêmes cases, une seule fonction ; chiffres de PM-Compound par mode, absents → « pas évalué » (375 et 1440 px)")


LOCAL_EXTRA = [local_no_wallet, local_rappro, local_cycles_fixture, local_render_cycles, local_zones, local_no_defaults, local_mv_card, local_plain_notes, local_decision_dups, local_decisions_real, local_decision_template, local_trades_more, local_perf_parity, local_predict_occupe, local_render_exits, local_render_live_totals, local_render_night, local_rules, local_no_hscroll]
base = (sys.argv[1] if len(sys.argv) > 1 else "https://pm-pipeline-tableau.pages.dev").rstrip("/")
proxy = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")
op = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
def get(path, auth=None):
    h = {"User-Agent": "pm-verify/1"}
    if auth: h["Authorization"] = "Basic " + base64.b64encode(auth.encode()).decode()
    for attempt in range(3):   # le proxy hoquette parfois (délai TLS) : 2 nouveaux essais sur erreur réseau seulement
        try:
            r = op.open(urllib.request.Request(base + path, headers=h), timeout=30); b = r.read()
            return r.status, dict(r.headers), len(b), b
        except urllib.error.HTTPError as e:
            b = e.read(); return e.code, dict(e.headers), len(b), b
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 2: raise
            __import__("time").sleep(3)
run_local_checks()
if LOCAL:
    sys.exit(0 if ok else 1)
pw = os.environ["DASHBOARD_PASSWORD"]
def check(label, path, auth, want):
    global ok
    st, hd, n, _ = get(path, auth)
    good = st == want
    ok &= good
    extra = ""
    if st == 401: extra = " WWW-Authenticate=" + ("oui" if hd.get("WWW-Authenticate") or hd.get("www-authenticate") else "NON")
    xr = hd.get("X-Robots-Tag") or hd.get("x-robots-tag")
    print(f"{'OK ' if good else 'KO '} {label:<26} {path:<22} -> {st} ({n} o){extra} X-Robots-Tag={xr}")
for p in ["/", "/data/summary.json", "/data/prices.json"]:
    check("sans identifiants", p, None, 401)
for p in ["/", "/data/prices.json"]:
    check("mauvais mot de passe", p, "quentin:mauvais-" + "x" * 8, 401)
check("mauvais utilisateur", "/", "admin:" + pw, 401)
for p in ["/", "/trades.html", "/performance.html", "/news.html", "/research.html", "/about.html", "/data/prices.json", "/data/summary.json", "/app.js"]:
    check("bon mot de passe", p, "quentin:" + pw, 200)
check("robots.txt (public)", "/robots.txt", None, 200)
check("sans identifiants", "/api/live?f=summary", None, 401)
# Passages des routines (Accueil > Journal des cycles) : présents dans le site, le build ET le paquet direct
import json
def check_runs(label, path, test):
    global ok
    st, _, _, b = get(path, "quentin:" + pw)
    try: good, info = test(st, b)
    except Exception as e: good, info = False, type(e).__name__
    ok &= good
    print(f"{'OK ' if good else 'KO '} {label:<26} {path:<22} -> {st} {info}")
def runs_of(d): r = d["routine_runs"]; assert isinstance(r.get("events"), list); return r
check_runs("passages: code page", "/app.js", lambda st, b: (st == 200 and b"Passages des routines" in b and "Aucun passage enregistré".encode() in b, "section présente"))
check_runs("passages: build", "/data/summary.json", lambda st, b: (st == 200, f"{len(runs_of(json.loads(b))['events'])} ligne(s)"))
def live_test(st, b):
    j = json.loads(b)
    if not j.get("available"): return False, "envoi direct indisponible"
    return True, f"{len(runs_of(j['files']['summary'])['events'])} ligne(s), envoyé {j.get('pushed_at')}"
check_runs("passages: envoi direct", "/api/live?f=summary", live_test)
# Zones de prix de PM-Predict (Analyses > Prévisions) : même paquet que le reste (summary.sonnette.zones)
def zones_of(d): z = d["sonnette"]["zones"]; assert isinstance(z, list); return z
check_runs("zones: code page", "/app.js", lambda st, b: (st == 200 and "Zones de prix du jour".encode() in b, "section présente"))
check_runs("zones: build", "/data/summary.json", lambda st, b: (st == 200, f"{len(zones_of(json.loads(b)))} zone(s)"))
def zones_live(st, b):
    j = json.loads(b)
    if not j.get("available"): return False, "envoi direct indisponible"
    return True, f"{len(zones_of(j['files']['summary']))} zone(s), envoyé {j.get('pushed_at')}"
check_runs("zones: envoi direct", "/api/live?f=summary", zones_live)

# Aucun « [object Object] » : prix / objets mal affichés (ex. dernier point PM-Research.prix) — fonction plus bas
# Règles communes : source unique references/regles-litterature.md (mtime = date affichée)
def check_team_rules():
    """Règles : structure et étiquettes = celles du fichier (PM-Orchestrator). Date affichée = « version du … » du titre.
    Chaque copie (build, envoi direct, page) est comparée strictement si elle a lu la version actuelle du fichier
    (source_sha256 notée par build.py) ; si le fichier a changé depuis moins de 10 min, l'écart est toléré (build toutes les 5 min)."""
    global ok
    R = rules_expected()
    if R.get("error"):
        print(f"KO  règles: fichier                -> {R['error']}"); ok = False; return
    def test(st, b, live=False):
        if st != 200: return False, f"HTTP {st}"
        j = json.loads(b)
        if live:
            if not j.get("available"): return False, "envoi direct indisponible"
            j = (j.get("files") or {}).get("summary") or {}
        return rules_compare(j.get("team_rules") or {}, R)
    srcb = open("/workspace/dashboard/build.py", encoding="utf-8").read()
    check_runs("règles: code", "/app.js", lambda st, b: (st == 200 and b"function rulesHtml" in b and b"rules-top" not in b and "_rule_group_of_section" not in srcb and "RULE_GROUPS" not in srcb, "rangement du site retiré"))
    check_runs("règles: build", "/data/summary.json", lambda st, b: test(st, b))
    check_runs("règles: envoi direct", "/api/live?f=summary", lambda st, b: test(st, b, live=True))
    # page : même référence que la copie qu'elle affiche (envoi direct si disponible, sinon fichiers publiés)
    st_l, _, _, b_l = get("/api/live?f=summary", "quentin:" + pw)
    jl = json.loads(b_l) if st_l == 200 else {}
    src_tr = ((jl.get("files") or {}).get("summary") or {}).get("team_rules") if jl.get("available") else None
    if src_tr is None:
        st_b, _, _, b_b = get("/data/summary.json", "quentin:" + pw)
        src_tr = (json.loads(b_b) if st_b == 200 else {}).get("team_rules") or {}
    strict, note = rules_freshness(src_tr, R)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
            for w, h in ((1440, 900), (375, 800)):
                ctx = br.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": h})
                pg = ctx.new_page(); bad = []
                try:
                    pg.goto(base + "/about.html#regles", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                    m = pg.evaluate(RULES_PAGE_JS)
                    bad = rules_page_problems(m, R, strict is True)
                    if strict is None: bad.append(note)
                except Exception as e:
                    bad.append(type(e).__name__)
                finally:
                    ctx.close()
                good = not bad; ok &= good
                print(f"{'OK ' if good else 'KO '} {'règles: page ' + str(w) + 'px':<26} {'/about.html#regles':<22} -> {', '.join(bad) if bad else ('pastilles = étiquettes du fichier, 3 parties ouvertes' if strict else 'toléré : ' + note)}")
            br.close()
    except Exception as e:
        ok = False; print(f"KO  règles: page                   -> {type(e).__name__}")

check_team_rules()

def check_no_object_object():
    global ok
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"KO  object Object: playwright   -> import échoué ({type(e).__name__})"); ok = False; return
    cred = {"username": "quentin", "password": pw}
    pages = ["/", "/research.html", "/research.html#decisions", "/trades.html", "/performance.html", "/performance.html#tests", "/news.html", "/about.html", "/index.html#apercu", "/research.html#archives", "/research.html#predict"]
    bad = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                              proxy={"server": proxy})
        ctx = b.new_context(http_credentials=cred, locale="fr-BE", timezone_id="Europe/Brussels",
                            viewport={"width": 1280, "height": 900})
        for path in pages:
            pg = ctx.new_page()
            try:
                r = pg.goto(base + path, wait_until="networkidle", timeout=60000)
                pg.wait_for_timeout(1800)
                # Forcer le rendu des onglets concernés si ancre
                txt = pg.evaluate("() => (document.body && document.body.innerText) || ''")
                html = pg.evaluate("() => (document.getElementById('app') && document.getElementById('app').innerHTML) || ''")
                if "[object Object]" in txt or "[object Object]" in html:
                    bad.append(path)
                # Carte Research : le bloc Prix ne doit pas être littéral [object Object]
                if "research" in path and "Prix :" in txt and "[object Object]" in txt:
                    bad.append(path + "(prix)")
            except Exception as e:
                bad.append(f"{path}:{type(e).__name__}")
            finally:
                pg.close()
        ctx.close(); b.close()
    # Paquet live : si last_research.prix est un objet, app.js doit avoir prixHtml (pas esc(lr.prix))
    st, _, _, bjs = get("/app.js", "quentin:" + pw)
    js_ok = st == 200 and b"function prixHtml" in bjs and b"esc(lr.prix)" not in bjs
    st2, _, _, br = get("/data/research.json", "quentin:" + pw)
    live_st, _, _, bl = get("/api/live?f=research", "quentin:" + pw)
    blob_ok = True
    try:
        import json as _j
        for label, stX, body in (("build", st2, br), ("live", live_st, bl)):
            if stX != 200:
                continue
            j = _j.loads(body)
            if label == "live":
                if not j.get("available"):
                    continue
                j = (j.get("files") or {}).get("research") or {}
            prix = (j.get("last_research") or {}).get("prix")
            if isinstance(prix, dict) and not js_ok:
                blob_ok = False
                bad.append(f"{label}:prix objet sans prixHtml")
            # Décisions : aucun bilan « Test du passé » sans id D-xxx
            for d in j.get("decisions") or []:
                did = str(d.get("id") or "")
                blob = " ".join([did, str(d.get("title") or ""), str(d.get("time_text") or "")])
                if ("Test du passé" in blob or "Test du passe" in blob) and not __import__("re").match(r"^D-\d+$", did):
                    bad.append(f"{label}:decision junk {did or d.get('time_text')}")
                    blob_ok = False
    except Exception as e:
        bad.append("parse:" + type(e).__name__); blob_ok = False
    good = not bad and js_ok and blob_ok
    ok &= good
    print(f"{'OK ' if good else 'KO '} {'object Object / junk':<26} {'pages+live':<22} -> {'clean' if good else ', '.join(bad[:6])}; prixHtml={'oui' if js_ok else 'NON'}")


# En-tête : titre « Équipe trading » + fraîcheur (#fresh, « ● à jour il y a 30 s », 1 ligne, sans cadre, détail en infobulle),
# bande de prix BTC/ETH/SOL complète,
# aucun défilement horizontal à 1440 et 375 px, ancienne fraîcheur retirée de la bande de prix.
def check_header():
    global ok
    st, _, _, bh = get("/", "quentin:" + pw)
    t_ok = st == 200 and "<title>Accueil — Équipe trading".encode() in bh and b"PM Pipeline" not in bh
    st2, _, _, bjs = get("/app.js", "quentin:" + pw)
    js_ok = st2 == 200 and 'id="fresh"'.encode() in bjs and b"setInterval(renderFresh" in bjs and b"PM Pipeline" not in bjs
    ok &= t_ok and js_ok
    print(f"{'OK ' if t_ok else 'KO '} {'en-tête: <title>':<26} {'/':<22} -> {'Équipe trading' if t_ok else 'titre incorrect'}")
    print(f"{'OK ' if js_ok else 'KO '} {'en-tête: code page':<26} {'/app.js':<22} -> {'#fresh + relecture' if js_ok else 'manquant'}")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"KO  en-tête: playwright        -> import échoué ({type(e).__name__})"); ok = False; return
    JS = """() => {
      const vw = window.innerWidth, f = document.getElementById('fresh'), pb = document.getElementById('pricebar');
      const fr = f ? f.getBoundingClientRect() : null, st = f ? getComputedStyle(f) : null;
      const pps = pb ? [...pb.querySelectorAll('.pp')].map(e => { const r = e.getBoundingClientRect(); return {t: e.textContent, in: r.left >= 0 && r.right <= vw + 0.5 && r.width > 0}; }) : [];
      const lh = f ? parseFloat(st.lineHeight) || parseFloat(st.fontSize) * 1.3 : 0;
      return {title: document.title, freshTip: f ? (f.title || '') : '', freshOneLine: !!(f && fr.height <= lh * 1.6 + 2),
        freshBorder: f ? parseFloat(st.borderTopWidth) + parseFloat(st.borderLeftWidth) : 0, freshDot: f ? ((f.querySelector('.dot') || {}).className || '') : '', brand: (document.querySelector('.brand b') || {}).textContent || '',
        fresh: f ? f.textContent : null, freshVisible: !!(f && fr.width > 0 && fr.height > 0 && st.display !== 'none' && st.visibility !== 'hidden'),
        freshInHeader: !!(f && f.closest('.site-header')), freshClipped: f ? (f.scrollWidth > f.clientWidth + 1 || fr.right > vw + 0.5 || fr.left < 0) : true,
        pbText: pb ? pb.textContent : '', pps, overflow: document.documentElement.scrollWidth - vw,
        footer: (document.getElementById('ftr') || {}).textContent || ''};
    }"""
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
        for tag, vp, mob in (("1440", {"width": 1440, "height": 900}, False), ("375", {"width": 375, "height": 812}, True)):
            ctx = b.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels",
                                viewport=vp, is_mobile=mob, has_touch=mob)
            for path in ("/", "/trades.html"):
                pg = ctx.new_page(); bad = []
                try:
                    for attempt in (1, 2):   # 1 nouvel essai si le proxy hoquette
                        try: pg.goto(base + path, wait_until="networkidle", timeout=60000); break
                        except Exception:
                            if attempt == 2: raise
                    pg.wait_for_timeout(2000)
                    m = pg.evaluate(JS)
                    pg.wait_for_timeout(6000)
                    later = pg.evaluate("(document.getElementById('fresh') || {}).textContent || ''")
                    if "Équipe trading" not in m["title"]: bad.append("titre")
                    if m["brand"].strip() != "Équipe trading": bad.append("nom en-tête")
                    if "Équipe trading" not in m["footer"]: bad.append("pied de page")
                    if not (m["fresh"] and m["freshVisible"] and m["freshInHeader"]): bad.append("fraîcheur absente")
                    elif m["freshClipped"]: bad.append("fraîcheur coupée")
                    elif not m["fresh"].startswith("à jour"): bad.append("fraîcheur: texte inattendu")
                    elif not m["freshOneLine"]: bad.append("fraîcheur sur plusieurs lignes")
                    elif m["freshBorder"] > 0: bad.append("fraîcheur encadrée")
                    elif not all(k in m["freshTip"] for k in ("Prix", "Page", "30 s")): bad.append("infobulle incomplète")
                    elif not any(c in m["freshDot"].split() for c in ("ok", "mid", "bad")): bad.append("point sans couleur")
                    if later == m["fresh"] and m["fresh"].endswith(" s"): bad.append("fraîcheur figée")
                    coins = [c for c in ("BTC", "ETH", "SOL") if any(x["t"].startswith(c) and x["in"] for x in m["pps"])]
                    if len(coins) != 3: bad.append("prix coupés (" + ",".join(coins) + ")")
                    if "Mis à jour" in m["pbText"] or "il y a" in m["pbText"]: bad.append("fraîcheur encore dans la bande")
                    if m["overflow"] > 0: bad.append(f"défilement horizontal {m['overflow']}px")
                    info = f"{m['fresh']} [{next((c for c in m['freshDot'].split() if c in ('ok', 'mid', 'bad')), '?')}] · infobulle: {m['freshTip']}"
                except Exception as e:
                    bad.append(type(e).__name__ + ": " + str(e).splitlines()[0][:90]); info = ""
                finally:
                    pg.close()
                good = not bad
                ok &= good
                print(f"{'OK ' if good else 'KO '} {'en-tête ' + tag + ' px':<26} {path:<22} -> {', '.join(bad) if bad else info}")
            ctx.close()
        b.close()

check_header()

# Envoi direct : /api/live servi par Cloudflare D1 (seule source), paquet poussé il y a moins de 90 s
def check_d1_live():
    global ok
    from datetime import datetime, timezone
    def test(st, b):
        if st != 200: return False, f"HTTP {st}"
        j = json.loads(b)
        if not j.get("available"): return False, f"indisponible ({j.get('reason')})"
        if j.get("store") != "d1": return False, f"source={j.get('store')} (attendu d1)"
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(j["pushed_at"])).total_seconds()
        good = age < 90 and all(n in (j.get("files") or {}) for n in ("prices", "summary"))
        return good, f"source=d1 · poussé il y a {round(age)} s (max 90 s)"
    check_runs("envoi direct: D1 < 90 s", "/api/live?f=prices,summary", test)

check_d1_live()

def check_no_wallet():
    for path in ("/data/summary.json", "/data/performance.json", "/data/trades.json", "/api/live?f=summary,performance,trades", "/app.js"):
        check_runs("pas d'adresse 0x", path, lambda st, b: (st == 200 and not WALLET_RX.search(b.decode("utf-8", "ignore")), "aucune adresse de portefeuille" if st == 200 else f"HTTP {st}"))
check_no_wallet()

# Journal des cycles : lignes des journaux des bots (format commun, section « 4. Journal » seulement), Grok Bot compris, pas archives/
def check_journal_lines():
    kinds = {"fait", "décision", "alerte", "problème", "leçon", "règle reçue"}
    def test(st, b, live=False):
        if st != 200: return False, f"HTTP {st}"
        j = json.loads(b)
        if live:
            if not j.get("available"): return False, "envoi direct indisponible"
            j = (j.get("files") or {}).get("summary") or {}
        jl = [e for e in j.get("log") or [] if e.get("status") == "JOURNAL"]
        bots = sorted({e.get("script") for e in jl})
        bad_kind = [e for e in jl if e.get("kind") not in kinds]
        arch = [e for e in jl if "archives/" in (e.get("source") or "")]
        from datetime import datetime, timezone, timedelta
        lg = j.get("log") or []
        lim = datetime.now(timezone.utc) - timedelta(days=7, hours=1)   # fenêtre 7 jours (+1 h : build toutes les 5 min)
        old = [e for e in lg if datetime.fromisoformat(e["started"].replace("Z", "+00:00")) < lim]
        good = len(jl) >= 30 and "Grok Bot" in bots and not bad_kind and not arch and not old and len(lg) <= 1000
        return good, f"{len(lg)} ligne(s) sur 7 j (max 1000, >7 j={len(old)}) dont {len(jl)} de journal · {len(bots)} bots · sans type={len(bad_kind)} · archives={len(arch)}"
    check_runs("journaux: code page", "/app.js", lambda st, b: (st == 200 and b"e.time_label" in b and b"e.kind" in b and b'id="more"' in b, "type + heure approx. + Voir plus"))
    check_runs("journaux: build", "/data/summary.json", lambda st, b: test(st, b))
    check_runs("journaux: envoi direct", "/api/live?f=summary", lambda st, b: test(st, b, live=True))

check_journal_lines()

# Journaux des bots : légende des emojis visible au-dessus des onglets (1440 et 375 px, pas de défilement horizontal)
def check_legend():
    global ok
    from playwright.sync_api import sync_playwright
    want = ["✅ fait", "📌 décision", "🔔 alerte", "⚠️ problème", "💡 leçon", "📜 règle reçue"]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
        for tag, vp, mob in (("1440", {"width": 1440, "height": 900}, False), ("375", {"width": 375, "height": 812}, True)):
            ctx = b.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels", viewport=vp, is_mobile=mob, has_touch=mob)
            pg = ctx.new_page(); bad = []; txt = ""
            try:
                for attempt in (1, 2):
                    try: pg.goto(base + "/research.html#journaux", wait_until="networkidle", timeout=60000); break
                    except Exception:
                        if attempt == 2: raise
                pg.wait_for_timeout(1500)
                m = pg.evaluate("""() => { const e = document.getElementById('jlegend'), t = document.querySelector('[data-j]'), vw = innerWidth;
                  if (!e) return null; const r = e.getBoundingClientRect(), st = getComputedStyle(e);
                  return {txt: e.textContent, vis: r.width > 0 && r.height > 0 && st.display !== 'none' && st.visibility !== 'hidden',
                          inside: r.left >= 0 && r.right <= vw + 0.5, above: !!(t && r.bottom <= t.getBoundingClientRect().top + 1),
                          overflow: document.documentElement.scrollWidth - vw}; }""")
                if not m: bad.append("légende absente")
                else:
                    txt = m["txt"]
                    if not m["vis"]: bad.append("invisible")
                    if not m["inside"]: bad.append("coupée")
                    if not m["above"]: bad.append("pas au-dessus des onglets")
                    if m["overflow"] > 0: bad.append(f"défilement horizontal {m['overflow']}px")
                    miss = [w for w in want if w not in txt]
                    if miss: bad.append("manque " + ", ".join(miss))
            except Exception as e:
                bad.append(type(e).__name__)
            finally:
                ctx.close()
            good = not bad; ok &= good
            print(f"{'OK ' if good else 'KO '} {'légende journaux ' + tag:<26} {'/research.html#journaux':<22} -> {', '.join(bad) if bad else txt}")
        b.close()

check_legend()

# ---- Règle « site = affichage seulement » (9 oct.) : chaque chiffre métier du site = le fichier de son propriétaire, exactement.
BOTD = "/workspace/predict-market-bot"
def _summary_pair():
    """(build, live) summary.json ; live = None si l'envoi direct est indisponible."""
    st, _, _, b = get("/data/summary.json", "quentin:" + pw)
    bj = json.loads(b) if st == 200 else {}
    st2, _, _, b2 = get("/api/live?f=summary", "quentin:" + pw)
    lj = None
    if st2 == 200:
        j = json.loads(b2)
        if j.get("available"): lj = (j.get("files") or {}).get("summary")
    return bj, lj

def _jl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                try: out.append(json.loads(ln))
                except ValueError: pass
    return out

def _read_guardian():
    """Même règle que le site : pas de lecture pendant que PM-Risk tient guardian/state.json.lock (verrou partagé, ~3 s)."""
    import fcntl, time as _t
    fh = open(BOTD + "/guardian/state.json.lock", "r")
    try:
        for _ in range(30):
            try:
                fcntl.flock(fh, fcntl.LOCK_SH | fcntl.LOCK_NB); break
            except OSError:
                _t.sleep(0.1)
        else:
            raise RuntimeError("guardian/state.json.lock tenu > 3 s")
        return json.load(open(BOTD + "/guardian/state.json", encoding="utf-8"))
    finally:
        try: fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError: pass
        fh.close()

def _want_verdict(v):
    """Verdict attendu tel qu'écrit : forme (a) chaîne "oui"/"non", forme (b) {ok, valeur, …}."""
    if isinstance(v, dict):
        v = v.get("ok") if isinstance(v.get("ok"), bool) else v.get("valeur")
    if isinstance(v, bool): return v
    if isinstance(v, str) and v.strip().lower() in ("oui", "non", "yes", "no", "true", "false"): return v.strip().lower() in ("oui", "yes", "true")
    return None

def check_audit():
    global ok
    def line(label, good, info):
        global ok
        ok &= bool(good)
        print(f"{'OK ' if good else 'KO '} {label:<26} {'':<22} -> {info}")
    bj, lj = _summary_pair()
    st, _, _, bp = get("/data/performance.json", "quentin:" + pw); P = json.loads(bp) if st == 200 else {}
    st, _, _, bt = get("/data/trades.json", "quentin:" + pw); T = json.loads(bt) if st == 200 else {}
    st, _, _, js = get("/app.js", "quentin:" + pw)
    G = _read_guardian()
    gpos = G.get("positions") or []
    gopen = [x for x in gpos if x.get("status") != "closed"]; gclosed = [x for x in gpos if x.get("status") == "closed"]
    # 1. Portefeuille simulé = guardian/state.json (PM-Risk), égalité exacte (build, envoi direct, page performance.json)
    pairs = {"balance_eur": "equity_eur", "cash_eur": "cash_eur", "peak_equity_eur": "peak_equity_eur", "invested_eur": "bankroll_eur",
             "drawdown_pct": "drawdown_pct", "daily_pnl_eur": "daily_pnl_eur", "daily_pnl_date": "daily_pnl_date",
             "total_pnl_eur": "total_pnl_eur", "unrealized_pnl_eur": "unrealized_pnl_eur", "exposure_eur": "exposure_eur", "exposure_pct": "exposure_pct"}
    posmap = {"id": "id", "pair": "pair", "side_raw": "side", "qty": "qty", "entry_price": "avg_price", "cost_eur": "cost_eur", "mark_eur": "mark_eur",
              "unrealized_eur": "unrealized_pnl_eur", "target_price": "target_price", "stop_price": "stop_price_eur", "fee_eur": "fee_eur", "decision_id": "decision_id",
              "last_mid_eur": "last_mid_eur", "unrealized_pct": "unrealized_pnl_pct"}
    from datetime import datetime as _dt
    def _same(a, b):
        try: return _dt.fromisoformat(str(a).replace("Z", "+00:00")) == _dt.fromisoformat(str(b).replace("Z", "+00:00"))
        except ValueError: return False
    # PM-Risk réécrit le fichier toutes les ~30 s : chaque copie du site est comparée EXACTEMENT à la version du gardien
    # qu'elle porte (summary_updated_at) : le fichier lui-même si c'est encore la même version, sinon la copie brute
    # de cette version gardée par build.py (cache/guardian_snapshots, octets lus sous verrou).
    SNAP = "/workspace/dashboard/cache/guardian_snapshots/"
    import re as _re2
    def ref_for(pp):
        ts = pp.get("summary_updated_at") or pp.get("updated_at")
        if _same(ts, G.get("summary_updated_at") or G.get("updated_at")): return G, "fichier"
        for f in sorted(os.listdir(SNAP)) if os.path.isdir(SNAP) else []:
            try: d = json.load(open(SNAP + f, encoding="utf-8"))
            except Exception: continue
            if _same(d.get("summary_updated_at") or d.get("updated_at"), ts): return d, "version " + str(ts)
        return None, None
    refs = {}
    for tag, S in (("build", bj), ("direct", lj), ("performance.json", P)):
        if S is None: line("portefeuille " + tag, True, "envoi direct indisponible (pas vérifié)"); continue
        pp = S.get("paper") or {}
        R, how = ref_for(pp)
        if R is None:
            line("portefeuille = gardien " + tag[:6], False, f"version {pp.get('summary_updated_at')} introuvable (ni fichier ni copie)"); continue
        refs[tag] = R
        Ropen = [x for x in R.get("positions") or [] if x.get("status") != "closed"]
        diff = [k for k, g in pairs.items() if pp.get(k) != R.get(g)]
        ol = pp.get("open_list") or []
        if len(ol) != len(Ropen): diff.append(f"{len(ol)} positions ≠ {len(Ropen)}")
        for o, g in zip(ol, Ropen):
            diff += [f"{o.get('id')}.{k}" for k, gk in posmap.items() if o.get(k) != g.get(gk)]
            if g.get("mark_ts") and not _same(o.get("mark_ts"), g.get("mark_ts")): diff.append(f"{o.get('id')}.mark_ts")
        line("portefeuille = gardien " + tag[:6], not diff, f"valeur {pp.get('balance_eur')} · liquidités {pp.get('cash_eur')} · sommet {pp.get('peak_equity_eur')} · {len(ol)} position(s) · comparé au {how}" + (f" · KO {diff[:4]}" if diff else " (égalité exacte)"))
    # 2. Contrôle avec Revolut X : guardian/state.json → rapprochement_revolut (PM-Risk), tel quel ; le site n'additionne rien
    R = refs.get("build") or G
    r = (bj.get("paper") or {}).get("rapprochement") or {}
    good = r.get("raw") == R.get("rapprochement_revolut") and "reconciliation" not in (bj.get("paper") or {})
    line("contrôle Revolut = Risk", good, f"{r.get('raw')} (version {R.get('summary_updated_at')})")
    # 3. Trades : gain/perte = realized_pnl_eur / unrealized_pnl_eur écrits (trades_log.jsonl ou gardien), aucun calculé
    logged = {x.get("realized_pnl_eur") for x in _jl(BOTD + "/state/trades_log.jsonl")} | {x.get("realized_pnl_eur") for x in gpos} | {x.get("unrealized_pnl_eur") for x in gpos} | {x.get(k) for R_ in refs.values() for x in R_.get("positions") or [] for k in ("realized_pnl_eur", "unrealized_pnl_eur")}
    tr = T.get("trades") or []
    bad = [t.get("id") for t in tr if t.get("pnl_eur") is not None and t.get("kind") != "fill" and t["pnl_eur"] not in logged]
    bad += [t.get("id") for t in tr if t.get("kind") == "fill" and t.get("pnl_eur") is not None]
    line("trades = journal", not bad, f"{sum(1 for t in tr if t.get('pnl_eur') is not None)} résultat(s), tous lus tels quels" + (f" · KO {bad[:3]}" if bad else ""))
    # 4. Cycles : lignes de trades_log.jsonl regroupées par cycle_id seulement ; chiffres et objectifs tels qu'écrits
    rows = {x.get("id"): x for x in _jl(BOTD + "/state/trades_log.jsonl")}
    cyc = (T.get("cycles") or {}).get("list") or []
    bad = []
    for c in cyc:
        k = c.get("cycle_id")
        for g in c.get("legs") or []:
            src = rows.get(g.get("id"))
            if src is None: continue   # ligne réécrite depuis la copie
            if k is not None and src.get("cycle_id") != k: bad.append(f"{g.get('id')} dans {k} sans cycle_id")   # règle stricte
            for f in ("price", "amount_eur", "qty", "realized_pnl_eur", "realized_pnl_pct", "coins_gained"):
                if g.get(f) != src.get(f): bad.append(f"{g.get('id')}.{f}")
        if k is None and len(c.get("legs") or []) != 1: bad.append(f"{c.get('id')} groupé sans cycle_id")
        op = rows.get(k) if k else None
        if op and c.get("target_price") != op.get("target_price"): bad.append(f"{k}.objectif")
    if "sell_first" in T: bad.append("ancien regroupement publié")
    line("cycles = cycle_id", cyc and not bad, f"{sum(1 for c in cyc if c.get('cycle_id'))} cycle(s) + {sum(1 for c in cyc if not c.get('cycle_id'))} ligne(s) seule(s)" + (f" · KO {bad[:3]}" if bad else " : regroupés par cycle_id seulement, chiffres tels quels"))
    # 5. Chiffres globaux = state/performance.json (PM-Compound) tel quel
    try: perf = json.load(open(BOTD + "/state/performance.json", encoding="utf-8"))
    except Exception: perf = None
    tp = P.get("team_perf") or {}
    line("chiffres globaux = Compound", (tp.get("raw") == perf) if perf is not None else not tp.get("present"),
         f"n_closed {(perf or {}).get('n_closed')} · écrit {tp.get('updated_at')}")
    # 5b. guardian/config.json (PM-Risk) : plafonds et nombre de trades réels par jour, tels quels
    GC = json.load(open(BOTD + "/guardian/config.json", encoding="utf-8"))
    ru = bj.get("rules") or {}; pp0 = bj.get("paper") or {}
    badc = []
    if pp0.get("cap_pct") != GC.get("paper_max_exposure_pct"): badc.append("plafond simulation")
    if ru.get("max_live_per_day") != GC.get("max_live_per_day"): badc.append("max_live_per_day")
    if GC.get("max_exposure_pct") is not None and ru.get("max_exposure_pct") != round(GC["max_exposure_pct"] * 100, 1): badc.append("plafond réel")
    line("config = guardian/config", not badc, f"simulation {GC.get('paper_max_exposure_pct')} · réel {GC.get('max_exposure_pct')} · réels/jour {GC.get('max_live_per_day')}" + (f" · KO {badc}" if badc else ""))
    # 5c. Sorties réelles : realized_pnl_eur (net) / _gross_eur / fees_eur de live_orders.jsonl, tels quels
    lo_rows = [r for r in _jl(BOTD + "/state/live_orders.jsonl") if not r.get("dry_run")] if os.path.exists(BOTD + "/state/live_orders.jsonl") else []
    bo = (T.get("real") or {}).get("bot_orders") or []
    bado = [i for i, (o, r) in enumerate(zip(bo, lo_rows)) for k in ("realized_pnl_eur", "realized_pnl_gross_eur", "fees_eur")
            if o.get(k) != r.get(k, (r.get("order") or {}).get(k))]
    line("sorties réelles = Risk", len(bo) == len(lo_rows) and not bado, f"{len(lo_rows)} ligne(s) dans live_orders.jsonl" + (" (fichier absent)" if not lo_rows else "") + (f" · KO {bado[:3]}" if bado else ""))
    # 6. Tests du passé : verdict seulement si un bot l'a écrit (verdict_equipe.*), sinon None → gris « non évalué »
    cards = (P.get("sellrebuy_tests") or []) + (P.get("backtests") or []) + (P.get("checks") or [])
    bad = [t.get("name") or t.get("id") for t in cards for k in ("past", "live")
           if ((t.get("gates") or {}).get(k) or {}).get("ok") is not None and not ((t.get("gates") or {}).get(k) or {}).get("by")]
    nv = sum(1 for t in cards for k in ("past", "live") if ((t.get("gates") or {}).get(k) or {}).get("ok") is None)
    # verdicts des runs = run_card.json / config.json du run, deux formes (a) chaîne et (b) objet
    import glob as _g
    RUNS = "/workspace/tools/vibe-trading/home/runs"
    for t in P.get("backtests") or []:
        docs = [json.load(open(f, encoding="utf-8")) for f in (f"{RUNS}/{t['id']}/config.json", f"{RUNS}/{t['id']}/run_card.json") if os.path.exists(f)]
        for k, key in (("past", "test_du_passe_reussi"), ("live", "autorise_en_reel")):
            want = None
            for d in docs:
                for src in ((d.get("verdict_equipe") or {}) if isinstance(d.get("verdict_equipe"), dict) else {}, d):
                    if want is None: want = _want_verdict(src.get(key))
            if t["gates"][k]["ok"] != want: bad.append(f"{t['id'][-30:]}.{k}")
            if t["id"].endswith("_grid") and t["gates"][k]["ok"] is not None: bad.append(f"{t['id'][-30:]} grille avec verdict")
    nred = sum(1 for t in cards for k in ("past", "live") if t["gates"][k]["ok"] is False)
    nwhy = sum(1 for t in cards for k in ("past", "live") if t["gates"][k]["ok"] is False and t["gates"][k].get("why"))
    line("tests: verdict équipe", cards and not bad and "non évalué par l’équipe".encode() in js,
         f"{len(cards)} carte(s) · {nv} critère(s) non évalué(s) · {nred} « non » dont {nwhy} avec raison" + (f" · KO {bad[:3]}" if bad else ""))
    # 7. Sonnette : compteurs du jour = status.json tels quels ; vrais/essais seulement si la sonnette les écrit
    so_f = json.load(open("/workspace/tools/sonnette/state/status.json", encoding="utf-8"))
    td = so_f.get("today") or {}
    bells = {b.get("key"): b for b in (bj.get("sonnette") or {}).get("bells") or []}
    bad = []
    for k in ("predict", "risk", "compound"):
        b = bells.get(k) or {}; dv = td.get(k + "_delivered") or {}
        if b.get("today_date") == td.get("date") and (b.get("today_real_mode"), b.get("today_dry")) != (dv.get("real"), dv.get("dry")): bad.append(k)
        tot = ((so_f.get("totals") or {}).get(k)) or {}
        if b.get("real_events") != tot.get("vrais") or b.get("tests") != tot.get("essais"): bad.append(k + " vrais/essais")
    # 7b. Les totaux écrits par la sonnette correspondent à son propre journal rings.jsonl (vérification indépendante)
    def _is_test(r):
        pl = r.get("payload") if isinstance(r.get("payload"), dict) else {}
        return bool(pl.get("test") or pl.get("mode") == "test" or str(pl.get("zone_id") or "").upper() == "TEST" or str(pl.get("decision_id") or "").upper().startswith("D-ESSAI"))
    rings = _jl("/workspace/tools/sonnette/state/rings.jsonl")
    tots = so_f.get("totals") or {}
    bad7 = []
    for k in ("predict", "risk", "compound"):
        mine = [r for r in rings if (r.get("bot") or (r.get("payload") or {}).get("bot")) == k]
        v, e = sum(1 for r in mine if not _is_test(r)), sum(1 for r in mine if _is_test(r))
        if (tots.get(k) or {}).get("vrais") != v or (tots.get(k) or {}).get("essais") != e: bad7.append(f"{k} {v}/{e}")
    line("sonnette totaux = rings", tots and not bad7 and "Vrais réveils : ".encode() in js,
         " · ".join(f"{k} vrais {(tots.get(k) or {}).get('vrais')} / essais {(tots.get(k) or {}).get('essais')}" for k in ("predict", "risk", "compound")) + (f" · KO {bad7}" if bad7 else ""))
    line("sonnette = status.json", len(bells) == 3 and not bad, " · ".join(f"{k} {bells[k].get('today_real_mode')}/{bells[k].get('today_dry')}" for k in bells) + (f" · KO {bad}" if bad else ""))
    # 7c. Nuit sans décision + distance des zones : repris de status.json (le bandeau ne lit que ce drapeau)
    bso = bj.get("sonnette") or {}
    zd_b, zd_f = bso.get("zones_distance") or {}, so_f.get("zones_distance") or {}
    bad7c = []
    if bso.get("night_sans_decision") != so_f.get("night_sans_decision"): bad7c.append("nuit")
    if sorted((zd_b.get("paires") or {})) != sorted((zd_f.get("paires") or {})): bad7c.append("paires")
    if not all(x.encode() in js for x in ("nuit-sans-decision", "night_sans_decision === true", "zones-distance")): bad7c.append("code page")
    line("sonnette nuit + distance zones", not bad7c,
         f"nuit sans décision={bso.get('night_sans_decision')} · " + " · ".join(f"{k} {'OK' if v.get('ok') else 'trop loin'}" for k, v in sorted((zd_b.get('paires') or {}).items()))
         + (f" · KO {bad7c}" if bad7c else ""))
    # 7d. Réveil mouvement : prochain réveil possible + références = status.json (même tour) ; le site ne recalcule rien
    mv_b, mv_f = (bj.get("sonnette") or {}).get("mouvement") or {}, so_f.get("predict_mouvement") or {}
    bad7d = []
    if _same(mv_b.get("ecrit_a"), so_f.get("heartbeat")):
        if mv_b.get("prochain_reveil_possible") != mv_f.get("prochain_reveil_possible"): bad7d.append("prochain réveil")
        if (mv_b.get("reference") or {}).get("prix") != ((mv_f.get("reference") or {}).get("prix")): bad7d.append("références")
        cmp_txt = "même tour"
    else:
        if (mv_b.get("reference") or {}).get("decision_id") != (mv_f.get("reference") or {}).get("decision_id"): bad7d.append("décision de référence")
        cmp_txt = "status.json réécrit depuis la copie : décision comparée"
    if not all(x.encode() in js for x in ("cycle-mouvement", "function mvCycle", "allCycles(s).map(cycleCard)", "prochain réveil possible (à ")): bad7d.append("code page")
    if "max_par_jour" in mv_b: bad7d.append("plafond encore affiché")
    if b"function mvBlock" in js: bad7d.append("ancienne carte encore dans le code")
    line("sonnette mouvement = status.json", mv_b and not bad7d,
         f"réf. {(mv_b.get('reference') or {}).get('decision_id')} · prochain réveil {mv_b.get('prochain_reveil_possible_fr')} · "
         + " · ".join(f"{k.split('-')[0]} {v:+.2f} %" for k, v in sorted((mv_b.get('mouvement_pct') or {}).items()) if v is not None)
         + f" · {cmp_txt}" + (f" · KO {bad7d}" if bad7d else ""))
    # 8. Argent réel : live_equity.json tel quel ; aucun total / valeur € calculé par le site
    le_f = json.load(open(BOTD + "/state/live_equity.json", encoding="utf-8"))
    cands = [S.get("live_equity") or {} for S in (bj, lj) if S]
    le = next((c for c in cands if _same(c.get("ts"), le_f.get("ts"))), None)
    if le is None:   # live_equity.json est réécrit toutes les quelques minutes : comparer la copie au même instant seulement
        line("réel = live_equity.json", True, f"fichier réécrit après les copies ({le_f.get('ts')}) : pas comparable maintenant"); le = {}
    bad = [k for k in ("capital_reel", "eur_available", "perte_jour_pct", "baisse_depuis_plus_haut_pct") if le.get(k) != le_f.get(k)]
    bad += [f"hors_bot.{c}" for c, v in (le.get("hors_bot") or {}).items() if v.get("eur") != (le_f.get("hors_bot") or {}).get(c, {}).get("eur")]
    rl = bj.get("real") or {}
    if "total_eur" in rl or "hors_bot_eur" in le: bad.append("total calculé")
    if any("value_eur" in a or "price_eur" in a for a in rl.get("assets") or [] if isinstance(a, dict)): bad.append("valeur d’actif calculée")
    if le:
        for k in ("total_reel_eur", "total_revolut_x_eur", "total_reel_complet", "soldes_revolut_x"):
            if le.get(k) != le_f.get(k): bad.append(k)
        mm_f = {k: v for k, v in (le_f.get("metamask") or {}).items() if k not in ("adresse", "address", "wallet", "wallet_address")}
        if (le.get("metamask") or {}) != mm_f: bad.append("metamask")   # tel quel, sauf l'adresse (jamais publiée)
        sl = next((S.get("sellable") or {} for S in (bj, lj) if S and _same((S.get("live_equity") or {}).get("ts"), le_f.get("ts"))), {})
        sx = le_f.get("soldes_revolut_x") or {}
        for row in sl.get("rows") or []:
            src = (le_f.get("metamask") or {}) if row.get("where", "").startswith("MetaMask") else sx.get(row.get("currency")) or {}
            pairs_ = (("total", "eth"), ("eur", "eur")) if row.get("where", "").startswith("MetaMask") else (("total", "total"), ("available", "disponible"), ("blocked_staking", "stake"), ("reserved_orders", "reserve"), ("eur", "eur"))
            bad += [f"{row.get('where')} {row.get('currency')}.{a}" for a, b_ in pairs_ if row.get(a) != src.get(b_)]
        if len(sl.get("rows") or []) != len([c for c in sx if c != "EUR"]) + (1 if (le_f.get("metamask") or {}).get("eth") is not None else 0): bad.append("lignes pièces")
    if le: line("réel = live_equity.json", not bad, f"capital {le.get('capital_reel')} · {len(le.get('hors_bot') or {})} pièce(s) hors bot" + (f" · KO {bad}" if bad else ""))
    # 9. Plus de calcul métier dans le code du site
    src = open("/workspace/dashboard/build.py", encoding="utf-8").read()
    gone = [f for f in ("def equity_series", "def overview_stats", "def test_gates", "def _halves_from", "def trade_stats", "def _check_gates") if f in src]
    gone += [f for f in ("coin_gain_if_now", "drawEquity", "total_return_pct\" in p") if f.encode() in js]
    gone += [f for f in ("def _sum(rows", "open_buys", "def load_sell_first", 'expectancy_min_multiple_of_cost", 3)') if f in src]   # lot 2
    gone += [f for f in ("(z.price - px)", "|| 0.08", "seuil_pct || 0.5", "intervalle_min_min || 30", "gap_eur") if f.encode() in js]
    gone += [f for f in ('    ("account", "balances"),', '"eth_getBalance", "params"', 'revx_read(["account", "balances"') if f in src]   # soldes : sonnette seulement
    line("aucun recalcul (code)", not gone, "build.py et app.js" + (f" · KO {gone}" if gone else " : fonctions de calcul retirées"))
    # Pages (1440 et 375 px) : valeurs affichées = gardien, critères gris, pas de défilement horizontal
    def num(t):
        import re as _re
        t = t.replace("\u202f", "").replace("\xa0", "").replace(" ", "")
        m = _re.search(r"-?[\d.]+(,\d+)?", t.replace("−", "-"))
        return float(m.group(0).replace(".", "").replace(",", ".")) if m else None
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        line("pages", False, f"playwright ({type(e).__name__})"); return
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
        for w, h in ((1440, 900), (375, 800)):
            ctx = br.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": h})
            pg = ctx.new_page(); bad = []; infos = []
            try:
                pg.goto(base + "/index.html#apercu", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
                m = pg.evaluate("""() => ({eq: (document.getElementById('paper-equity')||{}).textContent, cash: (document.getElementById('paper-cash')||{}).textContent,
                    peak: (document.getElementById('paper-peak')||{}).textContent, recon: (document.getElementById('rappro')||{}).textContent || '',
                    sides: [...document.querySelectorAll('.openpos')].map(o => o.dataset.side), ov: document.documentElement.scrollWidth - innerWidth})""")
                # la page affiche UNE version du gardien (data-ts = summary_updated_at) : comparée à cette version exacte
                upd = pg.evaluate("(document.getElementById('paper-updated')||{dataset:{}}).dataset.ts || ''")
                PR, phow = ref_for({"summary_updated_at": upd})
                if PR is None: bad.append(f"version affichée {upd} introuvable")
                else:
                    for k, gk in (("eq", "equity_eur"), ("cash", "cash_eur"), ("peak", "peak_equity_eur")):
                        if num(m[k] or "") != round(PR[gk], 2): bad.append(f"{k} affiché {m[k]} ≠ gardien {PR[gk]} ({phow})")
                rw = r.get("raw") or {}
                for k in ("gain_revolut_eur", "ecart_eur"):
                    if isinstance(rw.get(k), str) and rw[k] not in m["recon"]: bad.append(f"contrôle Revolut {k} pas tel quel")
                if not rw and "pas évalué" not in m["recon"]: bad.append("contrôle Revolut absent sans « pas évalué »")
                if PR is not None and len(m["sides"]) != len([x for x in (PR.get("positions") or []) if x.get("status") != "closed"]): bad.append("positions")

                if m["ov"] > 0: bad.append(f"défilement accueil {m['ov']}px")
                infos.append(f"affiché {m['eq']} / {m['cash']} / {m['peak']}")
                tr_txt = pg.evaluate("(document.getElementById('real-total')||{}).textContent || ''")
                ok_vals = {round(x, 2) for x in ((bj.get("live_equity") or {}).get("total_reel_eur"), ((lj or {}).get("live_equity") or {}).get("total_reel_eur"), le_f.get("total_reel_eur")) if x is not None}
                if ok_vals and num(tr_txt) not in ok_vals: bad.append(f"total réel affiché {tr_txt} ∉ {sorted(ok_vals)}")
                infos.append(f"total réel {tr_txt}")
                mm = pg.evaluate(MV_JS)
                pg.goto(base + "/index.html#sonnette", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
                nso = pg.evaluate(MV_JS)["n"]
                mvl = (bj.get("sonnette") or {}).get("mouvement")
                if mm["n"] != (1 if mvl else 0) or nso != 0: bad.append(f"carte mouvement : {mm['n']} dans Cycles automatiques, {nso} dans Sonnette")
                if mvl: bad += mv_card_problems(mm, None, w, "apercu")
                infos.append("carte mouvement 1× (Cycles automatiques)")
                pg.goto(base + "/performance.html#tests", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                if pg.locator("#tmore").count(): pg.click("#tmore"); pg.wait_for_timeout(800)
                m = pg.evaluate("""() => { const b = [...document.querySelectorAll('.gate')];
                    const red = b.filter(x => x.dataset.ok === 'false');
                    return {n: b.length, na: b.filter(x => x.dataset.ok === 'na' && /non évalué par l’équipe|pas de verdict/.test(x.textContent) && x.classList.contains('b-mute')).length,
                            redwhy: red.filter(x => (x.title || '').split(String.fromCharCode(10)).length > 1 && (x.title || '').split(String.fromCharCode(10))[1].trim().length > 0).length, red: red.length,
                            nul: /\\bnull\\b|undefined|NaN/.test(document.getElementById('app').innerText), ov: document.documentElement.scrollWidth - innerWidth}; }""")
                if m["nul"]: bad.append("« null » visible")
                if m["n"] != 2 * len(cards) or m["na"] != nv: bad.append(f"critères {m['na']} gris / {m['n']} (attendu {nv})")
                if m["ov"] > 0: bad.append(f"défilement tests {m['ov']}px")
                if m["red"] != nred or m["redwhy"] != nwhy: bad.append(f"raisons au survol {m['redwhy']}/{m['red']} (attendu {nwhy}/{nred})")
                infos.append(f"{m['na']} critère(s) gris · {m['redwhy']} raison(s) au survol")
                pg.goto(base + "/index.html#sonnette", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                m = pg.evaluate("""() => ({n: [...document.querySelectorAll('.bell')].filter(b => /Aujourd’hui : /.test(b.textContent)).length, ov: document.documentElement.scrollWidth - innerWidth})""")
                if m["n"] < 3: bad.append(f"sonnettes {m['n']}/3")
                if m["ov"] > 0: bad.append(f"défilement sonnette {m['ov']}px")
                # Réveil mouvement : compte à rebours vivant dans la carte unique (Cycles automatiques)
                pg.goto(base + "/index.html#apercu", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                mvj = """() => { const c = document.getElementById('cycle-mouvement'), l = c && c.querySelector('.led');
                    const w = l && l.querySelector('.lw');
                    return {ok: !!c, word: w ? w.textContent.trim() : null, lg: l ? l.querySelectorAll('.lg').length : 0, lit: l ? l.querySelectorAll('.s.on').length : 0,
                            html: l ? l.innerHTML : null, pairs: c ? c.querySelectorAll('[data-mvpair]').length : 0}; }"""
                a1 = pg.evaluate(mvj); pg.wait_for_timeout(2100); a2 = pg.evaluate(mvj)
                if not a1["ok"] or not (a1["word"] == "prêt" or (a1["lg"] >= 4 and a1["lit"] > 0)): bad.append(f"mouvement carte: afficheur {a1['word']!r} {a1['lg']} chiffres")
                elif a1["word"] is None and a1["html"] == a2["html"] and a1["lit"] != 4 * 6: bad.append("mouvement carte: le compte à rebours ne bouge pas")
                if a1["pairs"] != 3: bad.append(f"mouvement carte: {a1['pairs']} paire(s)")
                infos.append("mouvement « " + (a1["word"] or f"{a1['lg']} chiffres") + " »")
                for u in ("/performance.html#simulation", "/performance.html#reel", "/performance.html#monnaies", "/index.html#reel", "/trades.html"):
                    pg.goto(base + u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1000)
                    m = pg.evaluate("() => ({ov: document.documentElement.scrollWidth - innerWidth, bad: /undefined|NaN/.test(document.getElementById('app').innerText)})")
                    if m["ov"] > 0 or m["bad"]: bad.append(u + " " + str(m))
            except Exception as e:
                bad.append(type(e).__name__ + ": " + str(e).splitlines()[0][:160])
            finally:
                ctx.close()
            line(f"pages {w}px", not bad, ", ".join(bad) if bad else " · ".join(infos))
        br.close()

check_audit()

check_no_object_object()
sys.exit(0 if ok else 1)
