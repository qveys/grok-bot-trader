#!/usr/bin/env python3
"""Captures ciblées des nouvelles sections (bureau + 375 px). Usage : shot_sections.py BASE [prefix]"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
PREFIX = sys.argv[2] if len(sys.argv) > 2 else "local"
LOCAL = "localhost" in BASE
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
cred = {"username": "quentin", "password": os.environ.get("DASHBOARD_PASSWORD", "")}
targets = [("index", None, "Argent réel : ce que", "home-reel-details"), ("index", None, "Sonnette", "home-sonnette"),
           ("performance", None, "Vendre d’abord, racheter plus bas", "perf-vendre-dabord"), ("performance", None, "Argent réel", "perf-reel"),
           ("trades", "sf", None, "trades-vendre-dabord")]
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True,
                          **({"args": ["--no-proxy-server"]} if LOCAL else {"proxy": {"server": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")}}))
    for tag, vp, mobile in [("desktop", {"width": 1440, "height": 900}, False), ("mobile", {"width": 375, "height": 812}, True)]:
        ctx = b.new_context(viewport=vp, http_credentials=cred, is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1, locale="fr-BE", timezone_id="Europe/Brussels")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        cur = None
        for page, tab, text, name in targets:
            if page != cur or tab:
                pg.goto(f"{BASE}/{page}.html", wait_until="networkidle", timeout=60000); pg.wait_for_timeout(2000); cur = page
                pg.add_style_tag(content="header,#hdr{position:static!important}")
            if tab:
                pg.click(f"button[data-t={tab}]"); pg.wait_for_timeout(700)
                loc = pg.locator("#app")
            else:
                loc = pg.locator("section.section", has=pg.locator("h2", has_text=text)).first
            bad = pg.locator("text=Erreur d'affichage").count()
            ow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            f = os.path.join(OUT, f"{PREFIX}-{name}-{tag}.png")
            loc.screenshot(path=f)
            print(f"{tag:<7} {name:<22} débordement={ow}px erreur_affichage={bad} js={len(errs)} -> {f}")
        ctx.close()
    b.close()
