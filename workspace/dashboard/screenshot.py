#!/usr/bin/env python3
"""Captures headless (Chrome système, sans toucher au bureau) + contrôle de débordement horizontal mobile."""
import json, sys
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8080/"
PAGES = ["index", "trades", "performance", "research", "news", "about"]
OUT = "/workspace/dashboard/screenshots/"
report = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-proxy-server"])
    for label, vp, mobile in (("desktop", {"width": 1366, "height": 900}, False), ("mobile", {"width": 375, "height": 812}, True)):
        ctx = b.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile, locale="fr-BE", timezone_id="Europe/Brussels")
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        for pg in PAGES:
            page.goto(BASE + pg + ".html", wait_until="networkidle")
            page.wait_for_timeout(1200)
            name = {"index": "home"}.get(pg, pg)
            info = page.evaluate("""() => {
              const vw = document.documentElement.clientWidth; const sw = document.documentElement.scrollWidth;
              const off = [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width>0 && r.right > vw + 1 && !e.closest('.table-wrap,.pricebar,.tabs'); }).slice(0,8).map(e => e.tagName + '.' + e.className + ' →' + Math.round(e.getBoundingClientRect().right));
              const px = document.getElementById('pxage'); 
              return {priceAge: px ? px.textContent : null, clientWidth: vw, scrollWidth: sw, overflow: sw > vw, offenders: off, height: document.documentElement.scrollHeight};
            }""")
            report[f"{label}/{pg}"] = info
            page.screenshot(path=f"{OUT}{name}_{label}.png", full_page=False)
            page.screenshot(path=f"{OUT}{name}_{label}_full.png", full_page=True)
            if pg in ("index", "performance"):
                page.add_style_tag(content=".site-header{position:relative!important}")
            if pg == "index":  # carte « Argent réel »
                card = page.locator(".card", has=page.locator("h3", has_text="Argent réel")).first
                card.screenshot(path=f"{OUT}home_real_card_{label}.png")
            if pg == "performance":  # section par crypto (ETH sélectionné par défaut)
                sec = page.locator("section", has=page.locator("#pairtabs")).first
                sec.screenshot(path=f"{OUT}performance_pairs_{label}.png")
                report[f"{label}/pair_markers"] = page.evaluate("Chart.getChart(document.getElementById('pc')).data.datasets.map(d => d.label + ':' + d.data.length)")
                page.locator(".card", has=page.locator("text=Trades réels depuis")).count()
                realsec = page.locator("section", has=page.locator("h2", has_text="Argent réel")).first
                realsec.screenshot(path=f"{OUT}performance_real_{label}.png")
            if mobile and pg == "index":  # menu hamburger ouvert
                page.click("#navbtn"); page.wait_for_timeout(300)
                page.screenshot(path=f"{OUT}home_mobile_menu.png")
                report["mobile/menu_open"] = page.evaluate("document.getElementById('nav').classList.contains('open')")
        report[f"{label}/js_errors"] = errs
        ctx.close()
    b.close()
print(json.dumps(report, indent=1))
