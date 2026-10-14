"""Rendu de la copie de travail (dashboard-staging/site) avec les données actuelles de /workspace/dashboard/site/data.
Rien n'est écrit dans /workspace/dashboard. Usage : shot.py <préfixe> [largeurs...]"""
import sys, json, http.server, threading, shutil, os
ST = "/workspace/dashboard-staging"
for f in ("app.js", "style.css"):
    shutil.copyfile(f"{ST}/src/{f}", f"{ST}/site/{f}")
class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=ST + "/site", **k)
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
pref = sys.argv[1]; widths = [int(x) for x in sys.argv[2:]] or [1440, 375]
from playwright.sync_api import sync_playwright
out = {}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True)
    for w in widths:
        ctx = br.new_context(locale="fr-BE", timezone_id="Europe/Brussels", viewport={"width": w, "height": 900}, is_mobile=w < 800, has_touch=w < 800)
        ctx.route("**/api/live*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"available": false}'))
        def data(r):
            f = "/workspace/dashboard/site/data/" + r.request.url.split("/data/")[1].split("?")[0]
            if os.path.exists(f): r.fulfill(status=200, content_type="application/json", body=open(f, encoding="utf-8").read())
            else: r.fulfill(status=404, body="")
        ctx.route("**/data/*.json*", data)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(base + "/index.html#apercu", wait_until="networkidle"); pg.wait_for_timeout(1200)
        sec = pg.locator("#cycles").locator("xpath=ancestor::section[1]")
        sec.screenshot(path=f"{ST}/shots/{pref}-{w}.png")
        m = pg.evaluate("""() => { const vw = document.documentElement.clientWidth;
            const c = document.getElementById('cycle-mouvement'); const r = c ? c.getBoundingClientRect() : null;
            const sib = document.querySelector('#cycles .cy:not(#cycle-mouvement)'); const s = sib ? sib.getBoundingClientRect() : null;
            return {doc: document.documentElement.scrollWidth - vw, out: [...document.querySelectorAll('body *')].filter(e => { const b = e.getBoundingClientRect(); return b.width && b.right > vw + 1; }).length,
                    card: r && [Math.round(r.width), Math.round(r.height)], sib: s && [Math.round(s.width), Math.round(s.height)], txt: c ? c.innerText : null}; }""")
        m["errors"] = errs; out[w] = m
        if len(sys.argv) > 1 and "sonnette" in pref:
            pass
        pg.goto(base + "/index.html#sonnette", wait_until="networkidle"); pg.wait_for_timeout(800)
        pg.screenshot(path=f"{ST}/shots/{pref}-sonnette-{w}.png", full_page=True)
        ctx.close()
    br.close()
print(json.dumps(out, ensure_ascii=False, indent=1))
