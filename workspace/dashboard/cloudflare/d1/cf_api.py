"""Petit client API Cloudflare (via le proxy). Le jeton vient de l'env CLOUDFLARE_API_TOKEN ; jamais affiché."""
import json, os, urllib.request, urllib.error
ACC = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or "45be0d9d9ab486a652b81f7732f8f0d7"
_OP = urllib.request.build_opener(urllib.request.ProxyHandler({"https": os.environ.get("HTTPS_PROXY", "http://127.0.0.1:8791")}))

def call(method, path, body=None, timeout=30):
    tok = os.environ.get("CLOUDFLARE_D1_API_TOKEN") or os.environ["CLOUDFLARE_API_TOKEN"]
    req = urllib.request.Request("https://api.cloudflare.com/client/v4" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    try:
        r = _OP.open(req, timeout=timeout)
        return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}

def errs(j):
    return [(e.get("code"), e.get("message")) for e in (j or {}).get("errors", [])]
