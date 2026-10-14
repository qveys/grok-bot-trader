#!/usr/bin/env python3
"""Pose DASHBOARD_PASSWORD (secret chiffré) sur le projet Pages, pour production ET preview.
Lit le mot de passe et le jeton API dans l'environnement ; n'affiche jamais leurs valeurs."""
import json, os, sys, urllib.request
ACC = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "45be0d9d9ab486a652b81f7732f8f0d7")
PROJ = sys.argv[1] if len(sys.argv) > 1 else "pm-pipeline-tableau"
tok, pw = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("DASHBOARD_PASSWORD")
if not tok or not pw:
    sys.exit("CLOUDFLARE_API_TOKEN / DASHBOARD_PASSWORD absents de l'environnement")
proxy = os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")
op = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
url = f"https://api.cloudflare.com/client/v4/accounts/{ACC}/pages/projects/{PROJ}"
var = {"DASHBOARD_PASSWORD": {"type": "secret_text", "value": pw}}
body = json.dumps({"deployment_configs": {"production": {"env_vars": var}, "preview": {"env_vars": var}}}).encode()
req = urllib.request.Request(url, data=body, method="PATCH", headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
try:
    r = json.load(op.open(req, timeout=60))
except urllib.error.HTTPError as e:
    sys.exit("HTTP %s: %s" % (e.code, e.read()[:300].decode("utf-8", "replace")))
res = r.get("result") or {}
for env in ("production", "preview"):
    ev = ((res.get("deployment_configs") or {}).get(env) or {}).get("env_vars") or {}
    d = ev.get("DASHBOARD_PASSWORD") or {}
    print(env, "DASHBOARD_PASSWORD:", "présent" if d else "ABSENT", "type=" + str(d.get("type")))
print("success:", r.get("success"), "subdomain:", res.get("subdomain"))
