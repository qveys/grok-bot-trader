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
    """Règles : structure et étiquettes = celles du fichier (PM-Orchestrator). Date affichée = « version du … » du titre."""
    global ok
    import re as _re
    src = "/workspace/predict-market-bot/references/regles-litterature.md"
    try:
        txt = open(src, encoding="utf-8").read()
    except Exception as e:
        print(f"KO  règles: fichier                -> {type(e).__name__}"); ok = False; return
    MOIS = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"]
    title = next((l[2:] for l in txt.splitlines() if l.startswith("# ")), "")
    v = _re.search(r"version du\s+(\d{1,2})\s+([a-zéû]+)\.?\s+(\d{4})(?:,\s*(\d{1,2})h(\d{2}))?", title)
    want_date = f"{v.group(3)}-{MOIS.index(v.group(2)) + 1:02d}-{int(v.group(1)):02d}" if v else None
    want_label_bits = [f"{int(v.group(1))} {v.group(2)}", v.group(3)] + ([f"{int(v.group(4))}h{v.group(5)}"] if v and v.group(4) else []) if v else []
    heads = [_re.sub(r"\*\*|`", "", l[3:]).strip() for l in txt.splitlines() if l.startswith("## ")]
    body = txt.split("\n## ", 1)[1] if "\n## " in txt else ""
    want_tags = {k: len(_re.findall(r"\((" + w + r")\)", body)) for k, w in (("sim", "Simulation"), ("reel", "Réel"), ("both", "Les deux"))}
    def test(st, b, live=False):
        if st != 200: return False, f"HTTP {st}"
        j = json.loads(b)
        if live:
            if not j.get("available"): return False, "envoi direct indisponible"
            j = (j.get("files") or {}).get("summary") or {}
        tr = j.get("team_rules") or {}
        if not tr.get("available"): return False, "team_rules absent"
        gs = tr.get("groups") or []
        bad = []
        if [g.get("title") for g in gs] != heads: bad.append("groupes ≠ titres du fichier")
        mains = [(g.get("title"), g.get("scope")) for g in gs if g.get("main")]
        if [m[1] for m in mains] != ["both", "sim", "reel"] or not mains[0][0].startswith("Règles pour les deux") or mains[1][0] != "Simulation" or not mains[2][0].startswith("Réel"): bad.append(f"3 parties du haut {mains}")
        got_tags = {k: sum((g.get("tags") or {}).get(k, 0) for g in gs) for k in want_tags}
        if got_tags != want_tags: bad.append(f"étiquettes {got_tags} ≠ fichier {want_tags}")
        if tr.get("updated_date") != want_date or not all(x in (tr.get("updated_label") or "") for x in want_label_bits): bad.append(f"date {tr.get('updated_label')}")
        return not bad, (", ".join(bad) if bad else f"{len(gs)} groupes (= fichier) · 3 parties du haut · étiquettes {got_tags} · mises à jour le {tr.get('updated_label')}")
    srcb = open("/workspace/dashboard/build.py", encoding="utf-8").read()
    check_runs("règles: code", "/app.js", lambda st, b: (st == 200 and b"function rulesHtml" in b and b"rules-top" not in b and "_rule_group_of_section" not in srcb and "RULE_GROUPS" not in srcb, "rangement du site retiré"))
    check_runs("règles: build", "/data/summary.json", lambda st, b: test(st, b))
    check_runs("règles: envoi direct", "/api/live?f=summary", lambda st, b: test(st, b, live=True))
    # page : une pastille par étiquette du fichier, 3 groupes principaux ouverts, sous-titre = version du fichier
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, proxy={"server": proxy})
            for w, h in ((1440, 900), (375, 800)):
                ctx = br.new_context(http_credentials={"username": "quentin", "password": pw}, locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": h})
                pg = ctx.new_page(); bad = []
                try:
                    pg.goto(base + "/about.html#regles", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                    m = pg.evaluate("""() => { const c = document.getElementById('rulescard'); const sec = document.getElementById('regles');
                        const t = {}; [...c.querySelectorAll('.inner .rtag')].forEach(x => t[x.dataset.tag] = (t[x.dataset.tag]||0) + 1);
                        return {t, mains: [...c.querySelectorAll('details.rmain')].map(d => [d.dataset.scope, d.open]), head: sec ? sec.textContent.slice(0, 200) : '',
                                ov: document.documentElement.scrollWidth - innerWidth}; }""")
                    if {k: m["t"].get(k, 0) for k in want_tags} != want_tags: bad.append(f"pastilles {m['t']}")
                    if [x[0] for x in m["mains"]] != ["both", "sim", "reel"] or not all(x[1] for x in m["mains"]): bad.append(f"groupes principaux {m['mains']}")
                    if not all(x in m["head"] for x in want_label_bits): bad.append("sous-titre")
                    if m["ov"] > 0: bad.append(f"défilement {m['ov']}px")
                except Exception as e:
                    bad.append(type(e).__name__)
                finally:
                    ctx.close()
                good = not bad; ok &= good
                print(f"{'OK ' if good else 'KO '} {'règles: page ' + str(w) + 'px':<26} {'/about.html#regles':<22} -> {', '.join(bad) if bad else 'pastilles = étiquettes du fichier, 3 parties ouvertes'}")
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
    G = json.load(open(BOTD + "/guardian/state.json", encoding="utf-8"))
    gpos = G.get("positions") or []
    gopen = [x for x in gpos if x.get("status") != "closed"]; gclosed = [x for x in gpos if x.get("status") == "closed"]
    # 1. Portefeuille simulé = guardian/state.json (PM-Risk), égalité exacte (build, envoi direct, page performance.json)
    pairs = {"balance_eur": "equity_eur", "cash_eur": "cash_eur", "peak_equity_eur": "peak_equity_eur", "invested_eur": "bankroll_eur",
             "drawdown_pct": "drawdown_pct", "daily_pnl_eur": "daily_pnl_eur", "daily_pnl_date": "daily_pnl_date",
             "total_pnl_eur": "total_pnl_eur", "unrealized_pnl_eur": "unrealized_pnl_eur", "exposure_eur": "exposure_eur", "exposure_pct": "exposure_pct"}
    posmap = {"id": "id", "pair": "pair", "side_raw": "side", "qty": "qty", "entry_price": "avg_price", "cost_eur": "cost_eur", "mark_eur": "mark_eur",
              "unrealized_eur": "unrealized_pnl_eur", "target_price": "target_price", "stop_price": "stop_price_eur", "fee_eur": "fee_eur", "decision_id": "decision_id"}
    from datetime import datetime as _dt
    def _same(a, b):
        try: return _dt.fromisoformat(str(a).replace("Z", "+00:00")) == _dt.fromisoformat(str(b).replace("Z", "+00:00"))
        except ValueError: return False
    matched = []
    for tag, S in (("build", bj), ("direct", lj), ("performance.json", P)):
        if S is None: line("portefeuille " + tag, True, "envoi direct indisponible (pas vérifié)"); continue
        pp = S.get("paper") or {}
        if not _same(pp.get("updated_at"), G.get("summary_updated_at") or G.get("updated_at")):   # gardien réécrit après ce build : pas comparable, mais pas plus vieux de 15 min
            print(f"--  {'portefeuille = gardien ' + tag[:6]:<26} {'':<22} -> copie du gardien {pp.get('updated_at')}, fichier réécrit depuis ({G.get('updated_at')}) : pas comparable"); continue
        matched.append(tag)
        diff = [k for k, g in pairs.items() if pp.get(k) != G.get(g)]
        ol = pp.get("open_list") or []
        if len(ol) != len(gopen): diff.append(f"{len(ol)} positions ≠ {len(gopen)}")
        for o, g in zip(ol, gopen):
            diff += [f"{o.get('id')}.{k}" for k, gk in posmap.items() if o.get(k) != g.get(gk)]
        line("portefeuille = gardien " + tag[:6], not diff, f"valeur {pp.get('balance_eur')} · liquidités {pp.get('cash_eur')} · sommet {pp.get('peak_equity_eur')} · {len(ol)} position(s)" + (f" · KO {diff[:4]}" if diff else " (égalité exacte)"))
    if not matched: line("portefeuille = gardien", False, "aucune copie au même instant que guardian/state.json")
    # 2. Rapprochement : uniquement des sommes de champs du gardien ; écart = equity − somme (jamais une valeur de remplacement)
    r = (bj.get("paper") or {}).get("reconciliation") or {}
    # départ + Σ realized_pnl_eur (fermées) + Σ unrealized_pnl_eur de Risk (ouvertes, frais déjà inclus par le gardien)
    want = [G.get("bankroll_eur"), round(sum(x.get("realized_pnl_eur") or 0 for x in gclosed), 6),
            round(sum(x.get("unrealized_pnl_eur") or 0 for x in gopen), 6)]
    got = [c.get("value") for c in r.get("components") or []]
    miss_u = sum(1 for x in gopen if not isinstance(x.get("unrealized_pnl_eur"), (int, float)))
    good = got == want and r.get("equity_eur") == G.get("equity_eur") and r.get("gap_eur") == round(G.get("equity_eur") - sum(want), 6) \
        and (r.get("components") or [{}])[-1].get("missing") == miss_u
    line("rapprochement", good, f"{got} = {r.get('sum_eur')} · gardien {r.get('equity_eur')} · écart {r.get('gap_eur')}")
    # 3. Trades : gain/perte = realized_pnl_eur / unrealized_pnl_eur écrits (trades_log.jsonl ou gardien), aucun calculé
    logged = {x.get("realized_pnl_eur") for x in _jl(BOTD + "/state/trades_log.jsonl")} | {x.get("realized_pnl_eur") for x in gpos} | {x.get("unrealized_pnl_eur") for x in gpos}
    tr = T.get("trades") or []
    bad = [t.get("id") for t in tr if t.get("pnl_eur") is not None and t.get("kind") != "fill" and t["pnl_eur"] not in logged]
    bad += [t.get("id") for t in tr if t.get("kind") == "fill" and t.get("pnl_eur") is not None]
    line("trades = journal", not bad, f"{sum(1 for t in tr if t.get('pnl_eur') is not None)} résultat(s), tous lus tels quels" + (f" · KO {bad[:3]}" if bad else ""))
    # 4. Cycles « vendre d'abord » : gains / objectifs = champs écrits, aucun « si maintenant »
    rows = {x.get("id"): x for x in _jl(BOTD + "/state/trades_log.jsonl")}
    cyc = (T.get("sell_first") or {}).get("cycles") or []
    bad = []
    for c in cyc:
        if any(k.endswith("_if_now") or k.endswith("_if_now_pct") for k in c): bad.append(c["id"] + " si-maintenant")
        src = rows.get(c["id"]) or {}
        for k, fk in (("target_price", ("target_price", "rebuy_target_price", "rebuy_price_target", "prix_rachat")), ("safety_price", ("safety_price", "rebuy_stop_price", "stop_price_eur", "prix_rachat_force"))):
            if c.get(k) is not None and c[k] not in [src.get(f) for f in fk]: bad.append(f"{c['id']}.{k}")
        vals = {v for x in rows.values() for v in (x.get("realized_pnl_eur"), x.get("eur_gain"), x.get("coins_gained"), x.get("coin_gain"))}
        for k in ("eur_gain", "coin_gain"):
            if c.get(k) is not None and c[k] not in vals: bad.append(f"{c['id']}.{k}")
    line("cycles = journal", cyc and not bad, f"{len(cyc)} cycle(s)" + (f" · KO {bad[:3]}" if bad else " : objectifs et gains lus tels quels"))
    # 5. Chiffres globaux = state/performance.json (PM-Compound) tel quel
    try: perf = json.load(open(BOTD + "/state/performance.json", encoding="utf-8"))
    except Exception: perf = None
    tp = P.get("team_perf") or {}
    line("chiffres globaux = Compound", (tp.get("raw") == perf) if perf is not None else not tp.get("present"),
         f"n_closed {(perf or {}).get('n_closed')} · écrit {tp.get('updated_at')}")
    # 6. Tests du passé : verdict seulement si un bot l'a écrit (verdict_equipe.*), sinon None → gris « non évalué »
    cards = (P.get("sellrebuy_tests") or []) + (P.get("backtests") or []) + (P.get("checks") or [])
    bad = [t.get("name") or t.get("id") for t in cards for k in ("past", "live")
           if ((t.get("gates") or {}).get(k) or {}).get("ok") is not None and not ((t.get("gates") or {}).get(k) or {}).get("by")]
    nv = sum(1 for t in cards for k in ("past", "live") if ((t.get("gates") or {}).get(k) or {}).get("ok") is None)
    line("tests: verdict équipe", cards and not bad and "non évalué par l’équipe".encode() in js,
         f"{len(cards)} carte(s) · {nv} critère(s) non évalué(s) par l’équipe" + (f" · KO {bad[:3]}" if bad else ""))
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
        for k in ("total_reel_eur", "total_revolut_x_eur", "total_reel_complet", "soldes_revolut_x", "metamask"):
            if le.get(k) != le_f.get(k): bad.append(k)
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
                    peak: (document.getElementById('paper-peak')||{}).textContent, recon: (document.querySelector('.recon')||{}).textContent || '',
                    sides: [...document.querySelectorAll('.openpos')].map(o => o.dataset.side), ov: document.documentElement.scrollWidth - innerWidth})""")
                for k, gk in (("eq", "equity_eur"), ("cash", "cash_eur"), ("peak", "peak_equity_eur")):
                    if num(m[k] or "") != round(G[gk], 2): bad.append(f"{k} affiché {m[k]} ≠ gardien {G[gk]}")
                gap = r.get("gap_eur")
                if (gap is not None and abs(gap) >= 0.005) != ("écart" in m["recon"]): bad.append("écart mal affiché")
                if len(m["sides"]) != len(gopen): bad.append("positions")
                if ("*" in m["recon"]) != bool(miss_u): bad.append("étoile du rapprochement")
                if m["ov"] > 0: bad.append(f"défilement accueil {m['ov']}px")
                infos.append(f"affiché {m['eq']} / {m['cash']} / {m['peak']}")
                tr_txt = pg.evaluate("(document.getElementById('real-total')||{}).textContent || ''")
                ok_vals = {round(x, 2) for x in ((bj.get("live_equity") or {}).get("total_reel_eur"), ((lj or {}).get("live_equity") or {}).get("total_reel_eur"), le_f.get("total_reel_eur")) if x is not None}
                if ok_vals and num(tr_txt) not in ok_vals: bad.append(f"total réel affiché {tr_txt} ∉ {sorted(ok_vals)}")
                infos.append(f"total réel {tr_txt}")
                pg.goto(base + "/performance.html#tests", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                if pg.locator("#tmore").count(): pg.click("#tmore"); pg.wait_for_timeout(800)
                m = pg.evaluate("""() => { const b = [...document.querySelectorAll('.gate')];
                    return {n: b.length, na: b.filter(x => x.dataset.ok === 'na' && /non évalué par l’équipe/.test(x.textContent) && x.classList.contains('b-mute')).length,
                            nul: /\\bnull\\b|undefined|NaN/.test(document.getElementById('app').innerText), ov: document.documentElement.scrollWidth - innerWidth}; }""")
                if m["nul"]: bad.append("« null » visible")
                if m["n"] != 2 * len(cards) or m["na"] != nv: bad.append(f"critères {m['na']} gris / {m['n']} (attendu {nv})")
                if m["ov"] > 0: bad.append(f"défilement tests {m['ov']}px")
                infos.append(f"{m['na']} critère(s) gris")
                pg.goto(base + "/index.html#sonnette", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1200)
                m = pg.evaluate("""() => ({n: [...document.querySelectorAll('.bell')].filter(b => /Aujourd’hui : /.test(b.textContent)).length, ov: document.documentElement.scrollWidth - innerWidth})""")
                if m["n"] < 3: bad.append(f"sonnettes {m['n']}/3")
                if m["ov"] > 0: bad.append(f"défilement sonnette {m['ov']}px")
                for u in ("/performance.html#simulation", "/performance.html#reel", "/performance.html#monnaies", "/index.html#reel", "/trades.html"):
                    pg.goto(base + u, wait_until="networkidle", timeout=60000); pg.wait_for_timeout(1000)
                    m = pg.evaluate("() => ({ov: document.documentElement.scrollWidth - innerWidth, bad: /undefined|NaN/.test(document.getElementById('app').innerText)})")
                    if m["ov"] > 0 or m["bad"]: bad.append(u + " " + str(m))
            except Exception as e:
                bad.append(type(e).__name__)
            finally:
                ctx.close()
            line(f"pages {w}px", not bad, ", ".join(bad) if bad else " · ".join(infos))
        br.close()

check_audit()

check_no_object_object()
sys.exit(0 if ok else 1)
