#!/usr/bin/env python3
"""Vérifie la protection du site publié (via le proxy). Le mot de passe est lu dans l'environnement, jamais affiché."""
import base64, os, sys, urllib.request, urllib.error
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
pw = os.environ["DASHBOARD_PASSWORD"]
ok = True
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
    global ok
    import os as _os
    src = "/workspace/predict-market-bot/references/regles-litterature.md"
    want = None
    try:
        from datetime import datetime, timezone
        from zoneinfo import ZoneInfo
        mt = datetime.fromtimestamp(_os.path.getmtime(src), timezone.utc).astimezone(ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d")
        want = mt
    except Exception as e:
        print(f"KO  règles: mtime fichier        -> {type(e).__name__}"); ok = False; return
    def test(st, b, live=False):
        if st != 200: return False, f"HTTP {st}"
        j = json.loads(b)
        if live:
            if not j.get("available"): return False, "envoi direct indisponible"
            j = (j.get("files") or {}).get("summary") or {}
        tr = j.get("team_rules") or {}
        if not tr.get("available"): return False, "team_rules absent"
        got = tr.get("updated_date")
        good = got == want
        return good, f"date={got} (fichier {want}) · {tr.get('updated_label')} · {sum(g.get('count') or 0 for g in tr.get('groups') or [])} règles"
    check_runs("règles: code page", "/app.js", lambda st, b: (st == 200 and b"function rulesHtml" in b and "verrouillées le 7 octobre".encode() not in b, "rulesHtml, plus de date en dur"))
    check_runs("règles: build", "/data/summary.json", lambda st, b: test(st, b))
    check_runs("règles: envoi direct", "/api/live?f=summary", lambda st, b: test(st, b, live=True))

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

# ---- Audit du 9 oct. (5 points) : chaque correction a sa vérification pour ne pas revenir.
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

def check_audit():
    global ok
    def line(label, good, info):
        global ok
        ok &= bool(good)
        print(f"{'OK ' if good else 'KO '} {label:<26} {'':<22} -> {info}")
    bj, lj = _summary_pair()
    st, _, _, bp = get("/data/performance.json", "quentin:" + pw)
    P = json.loads(bp) if st == 200 else {}
    st, _, _, js = get("/app.js", "quentin:" + pw)
    # 1. Comptabilité : solde = liquidités + achats − ventes à racheter ; départ + fermés + ouverts − frais = solde (écart ≤ 0,01 €)
    for tag, S in (("build", bj), ("direct", lj)):
        if S is None: line("1 compta " + tag, True, "envoi direct indisponible (pas vérifié)"); continue
        pp = S.get("paper") or {}; r = pp.get("reconciliation") or {}
        try:
            bal = pp["balance_eur"]; calc = pp["cash_eur"] + pp["long_value_eur"] - pp["short_to_rebuy_eur"]
            expl = r["start_eur"] + r["realized_eur"] + r["unrealized_eur"] - r["open_fees_eur"]
            ge = r.get("guardian_equity_eur")
            tol = 0.05 * (pp.get("in_positions_eur") or 0) + 0.05     # gardien valorisé à son dernier prix, site au prix du moment
            good = abs(bal - calc) <= 0.01 and abs(bal - expl) <= 0.01 and abs(r.get("gap_eur", 9)) <= 0.01 and (ge is None or abs(bal - ge) <= tol)
            info = f"solde {bal:.2f} € = {r['start_eur']:.0f} {r['realized_eur']:+.2f} {r['unrealized_eur']:+.2f} −{r['open_fees_eur']:.2f} · gardien {ge} · écart {r.get('gap_eur')}"
        except Exception as e:
            good, info = False, f"champ manquant ({type(e).__name__})"
        line("1 compta " + tag, good, info)
    # 2. Sens des positions : champ side (achat/vente) sur chaque position ouverte, plus de « acheté » codé en dur
    ol = (bj.get("paper") or {}).get("open_list") or []
    bad = [o.get("pair") for o in ol if o.get("side") not in ("achat", "vente") or (o.get("side") == "vente" and o.get("buy_price") is not None)]
    line("2 sens positions", not bad and b'" \xc2\xb7 achet\xc3\xa9 "' not in js and b"function openPosHtml" in js,
         f"{len(ol)} position(s) : " + (", ".join(f"{o.get('pair')} {o.get('side')}" for o in ol) or "aucune") + (f" · KO {bad}" if bad else ""))
    # 3. Tests du passé : 2 critères sur chaque carte, 0 frais seulement dit, « Autorisé en réel » seulement avec frais réels + 3×
    cards = (P.get("sellrebuy_tests") or []) + (P.get("backtests") or []) + (P.get("checks") or [])
    bad = []
    for t in cards:
        G = t.get("gates") or {}
        pa, li = G.get("past") or {}, G.get("live") or {}
        if not pa.get("label", "").startswith("Test du passé réussi") or li.get("label") != "Autorisé en réel": bad.append("libellé"); continue
        if pa.get("ok") and "0 frais sur tous" in (pa.get("fees") or "") and "avec 0 frais seulement" not in pa["label"]: bad.append("0 frais non dit")
        if li.get("ok") and (not pa.get("ok") or "frais réels sur chaque ordre" not in (pa.get("fees") or "") or not all(c.get("ok") is True for c in li.get("checks") or [])): bad.append("réel trop permissif")
    line("3 tests: données", cards and not bad, f"{len(cards)} carte(s), {sum(1 for t in cards if t['gates']['past']['ok'])} test(s) réussi(s), {sum(1 for t in cards if t['gates']['live']['ok'])} autorisé(s) en réel" + (f" · KO {bad[:3]}" if bad else ""))
    # 4. Règles : groupes « Simulation » / « Réel » explicites, aucune règle « Live… » hors Réel ni « Simulation… » hors Simulation
    import re as _re
    tr = bj.get("team_rules") or {}
    titles = [g.get("title") for g in tr.get("groups") or []]
    mixed = []
    for g in tr.get("groups") or []:
        for sc in g.get("sections") or []:
            for it in sc.get("items") or []:
                t0 = _re.sub(r"^<strong>", "", it).lower()
                if g.get("key") != "live" and _re.match(r"^(live\b|en live\b|pas de live\b|ticket mini live\b)", t0): mixed.append("live→" + g.get("title"))
                if g.get("key") != "simulation" and t0.startswith("simulation"): mixed.append("simu→" + g.get("title"))
    line("4 règles groupes", "Simulation" in titles and "Réel" in titles and not mixed and b'data-scope=' in js, " · ".join(titles) + (f" · KO {mixed[:3]}" if mixed else ""))
    # 5. Sonnette : vrais réveils et essais séparés par sonnette, comptés sur rings.jsonl
    so = bj.get("sonnette") or {}
    bells = {b.get("key"): b for b in so.get("bells") or []}
    good5, info5 = all(k in bells for k in ("predict", "risk", "compound")), ""
    try:
        cnt = {}
        with open("/workspace/tools/sonnette/state/rings.jsonl", encoding="utf-8") as f:
            for ln in f:
                if not ln.strip(): continue
                r = json.loads(ln); plx = r.get("payload") or {}
                k = r.get("bot") or plx.get("bot"); cnt[k] = cnt.get(k, 0) + 1
        for k in ("predict", "risk", "compound"):
            b = bells.get(k) or {}
            if (b.get("real") or 0) + (b.get("tests") or 0) != cnt.get(k, 0): good5 = False
        info5 = " · ".join(f"{bells[k]['bot']} vrais {bells[k]['real']} / essais {bells[k]['tests']}" for k in ("predict", "risk", "compound") if k in bells)
    except Exception as e:
        good5, info5 = False, type(e).__name__
    line("5 sonnette réveils", good5 and "Vrais réveils : ".encode() in js and "pas encore de résultat lié".encode() in js, info5)
    # Rendu réel des pages (1440 et 375 px) : position, rapprochement, cartes de tests (toutes), règles, sonnette
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        line("audit: pages", False, f"playwright ({type(e).__name__})"); return
    with sync_playwright() as p:
        br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
        for w, h in ((1440, 900), (375, 800)):
            ctx = br.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": h})
            pg = ctx.new_page(); bad = []; infos = []
            try:
                pg.goto(base + "/index.html#apercu", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1500)
                m = pg.evaluate("""() => { const c = [...document.querySelectorAll('.card')].find(x => /Argent fictif/.test(x.innerText)) || {innerText:''};
                    return {t: c.innerText, sides: [...document.querySelectorAll('.openpos')].map(o => [o.dataset.side, o.textContent]),
                            recon: (document.querySelector('.recon')||{}).innerText || '', ov: document.documentElement.scrollWidth - innerWidth}; }""")
                if not m["recon"]: bad.append("rapprochement absent")
                elif "écart" in m["recon"]: infos.append("écart affiché")
                for sd, tx in m["sides"]:
                    if sd == "vente" and ("acheté" in tx or "Vente" not in tx or "rachat prévu" not in tx): bad.append("vente mal libellée")
                    if sd == "achat" and "Achat" not in tx: bad.append("achat mal libellé")
                if m["ov"] > 0: bad.append(f"défilement accueil {m['ov']}px")
                pg.goto(base + "/performance.html#tests", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                if pg.locator("#tmore").count(): pg.click("#tmore"); pg.wait_for_timeout(800)
                m = pg.evaluate("""() => { const cs = [...document.querySelectorAll('.gates')].map(g => g.textContent);
                    return {n: cs.length, both: cs.filter(t => /Test du passé réussi/.test(t) && /Autorisé en réel/.test(t)).length,
                            nul: /\\bnull\\b|undefined|NaN/.test(document.getElementById('app').innerText), ov: document.documentElement.scrollWidth - innerWidth}; }""")
                if m["nul"]: bad.append("« null » visible")
                if not m["n"] or m["both"] != m["n"]: bad.append(f"critères {m['both']}/{m['n']}")
                if m["ov"] > 0: bad.append(f"défilement tests {m['ov']}px")
                infos.append(f"{m['n']} cartes à 2 critères")
                pg.goto(base + "/about.html#regles", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1000)
                sc = pg.evaluate("() => [...document.querySelectorAll('details.rgroup')].map(d => d.dataset.scope)")
                if "sim" not in sc or "reel" not in sc: bad.append("groupes Simulation/Réel absents")
                pg.goto(base + "/index.html#sonnette", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                m = pg.evaluate("""() => ({n: [...document.querySelectorAll('.bell')].filter(b => /Vrais réveils : \\d+ · Essais : \\d+/.test(b.innerText)).length,
                                         ov: document.documentElement.scrollWidth - innerWidth})""")
                if m["n"] < 3: bad.append(f"sonnettes {m['n']}/3")
                if m["ov"] > 0: bad.append(f"défilement sonnette {m['ov']}px")
            except Exception as e:
                bad.append(type(e).__name__)
            finally:
                ctx.close()
            line(f"audit: pages {w}px", not bad, ", ".join(bad) if bad else " · ".join(infos))
        br.close()

check_audit()

check_no_object_object()
sys.exit(0 if ok else 1)
