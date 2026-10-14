#!/usr/bin/env python3
"""Captures de chaque page ET de chaque onglet (desktop 1366 + mobile 375), contrôle débordement + erreurs JS.
Usage : shots_all.py local|hosted [préfixe]. Hébergé : Basic Auth avec DASHBOARD_PASSWORD (env, jamais affiché)."""
import json, os, sys
from playwright.sync_api import sync_playwright
MODE = sys.argv[1] if len(sys.argv) > 1 else "local"
PFX = sys.argv[2] if len(sys.argv) > 2 else MODE
BASE = "http://127.0.0.1:8080/" if MODE == "local" else "https://pm-pipeline-tableau.pages.dev/"
OUT = "/workspace/dashboard/screenshots/v3/"; os.makedirs(OUT, exist_ok=True)
TARGETS = [("index", t) for t in ("apercu", "reel", "cycles", "sonnette")] + [("trades", "")] + \
          [("performance", t) for t in ("simulation", "reel", "monnaies", "tests")] + \
          [("research", t) for t in ("marche", "predict", "decisions", "score", "archives", "journaux")] + [("news", ""), ("about", "")]
rep = {}
with sync_playwright() as p:
    kw = {"args": ["--no-proxy-server"]} if MODE == "local" else {"proxy": {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")}}
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, **kw)
    for label, vp, mob in (("desktop", {"width": 1366, "height": 900}, False), ("mobile", {"width": 375, "height": 812}, True)):
        ckw = {"http_credentials": {"username": "quentin", "password": os.environ["DASHBOARD_PASSWORD"]}} if MODE != "local" else {}
        ctx = b.new_context(viewport=vp, device_scale_factor=2 if mob else 1, is_mobile=mob, has_touch=mob, locale="fr-BE", timezone_id="Europe/Brussels", **ckw)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        for page, tab in TARGETS:
            pg.goto(BASE + page + ".html" + ("#" + tab if tab else ""), wait_until="networkidle"); pg.wait_for_timeout(1500)
            info = pg.evaluate("""() => { const vw = document.documentElement.clientWidth, sw = document.documentElement.scrollWidth;
              const off = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width>0 && r.right > vw + 1 && !e.closest('.table-wrap,.pricebar,.tabs'); }).slice(0,5).map(e => e.tagName + '.' + e.className);
              const on = document.querySelector('.tabs .tab.on'); const upd = document.getElementById('upd');
              return {overflow: sw > vw, off, tab: on ? on.textContent : null, upd: upd ? upd.textContent : null}; }""")
            name = f"{PFX}_{page}{'_' + tab if tab else ''}_{label}"
            pg.screenshot(path=OUT + name + ".png", full_page=True)
            rep[name] = info
        rep[f"{label}/js_errors"] = errs[:10]
        ctx.close()
    b.close()
bad = {k: v for k, v in rep.items() if isinstance(v, dict) and (v["overflow"] or v["off"])}
print(json.dumps({"n": len(rep), "overflow": bad, "js_errors": {k: v for k, v in rep.items() if k.endswith("js_errors")},
                  "sample_upd": rep.get(f"{PFX}_index_apercu_desktop", {}).get("upd"), "tabs": {k: v.get("tab") for k, v in rep.items() if isinstance(v, dict)}}, indent=1, ensure_ascii=False))
