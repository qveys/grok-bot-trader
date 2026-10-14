#!/usr/bin/env python3
"""Captures du site publié (Basic Auth, mot de passe lu dans l'env, jamais affiché) : bureau 1440 + mobile 375."""
import os, sys
from playwright.sync_api import sync_playwright
BASE = (sys.argv[1] if len(sys.argv) > 1 else "https://pm-pipeline-tableau.pages.dev").rstrip("/")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(OUT, exist_ok=True)
cred = {"username": "quentin", "password": os.environ["DASHBOARD_PASSWORD"]}
pages = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["index", "trades", "performance", "news", "about"])
PREFIX = sys.argv[3] if len(sys.argv) > 3 else "hosted"
LOCAL = "localhost" in BASE or "127.0.0.1" in BASE
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, **({"args": ["--no-proxy-server"]} if LOCAL else {"proxy": {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")}}))
    for tag, vp, mobile in [("desktop", {"width": 1440, "height": 900}, False), ("mobile", {"width": 375, "height": 812}, True)]:
        ctx = b.new_context(viewport=vp, http_credentials=cred, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1, locale="fr-BE", timezone_id="Europe/Brussels")
        for name in pages:
            pg = ctx.new_page(); errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            r = pg.goto(f"{BASE}/{name}.html", wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(2500)
            ow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            upd = pg.evaluate("(document.getElementById('upd')||{}).textContent || ''")
            px = pg.evaluate("(document.getElementById('pxage')||{}).textContent || ''")
            f = os.path.join(OUT, f"{PREFIX}-{name}-{tag}.png")
            if name == "trades" and "sf" in sys.argv[4:]:
                pg.click("button[data-t=sf]"); pg.wait_for_timeout(800)
            pg.screenshot(path=f, full_page=(name != "news"))
            print(f"{tag:<7} {name:<12} js_errors={errs[:2]} HTTP {r.status if r else '?'} débordement={ow}px erreurs_js={len(errs)} | {upd} | {px} -> {f}")
            pg.close()
        ctx.close()
    b.close()
