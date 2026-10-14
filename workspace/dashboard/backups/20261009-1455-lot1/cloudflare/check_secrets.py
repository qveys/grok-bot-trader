#!/usr/bin/env python3
"""Garde-fou avant publication : refuse si un secret se trouve dans les dossiers donnés.
N'affiche jamais de valeur ; seulement le nom du fichier et le type de problème."""
import os, re, sys
bad = []
tok = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
pw = os.environ.get("DASHBOARD_PASSWORD") or ""
pw_re = re.compile(r"(?<![A-Za-z0-9])" + re.escape(pw) + r"(?![A-Za-z0-9])") if pw else None
pat = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|\"(api_?key|api_?secret|private_?key|access_?token|refresh_?token|client_?secret|mnemonic|seed_?phrase)\"\s*:", re.I)
hook = re.compile(r"hooks\.slack\.com/|discord(?:app)?\.com/api/webhooks|SONNETTE_[A-Z_]+\s*=|[?&](?:token|secret|apikey|api_key|access_token)=[A-Za-z0-9_\-]{8,}|\bBearer\s+[A-Za-z0-9._\-]{16,}", re.I)
badname = re.compile(r"(^\.env|\.pem$|\.key$|^config\.json$|revx|secret)", re.I)
for root in sys.argv[1:]:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            path = os.path.join(dp, f)
            if badname.search(f) or f.startswith("."):
                bad.append((path, "nom de fichier interdit")); continue
            try:
                s = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if tok and tok in s: bad.append((path, "jeton API"))
            if pw_re and pw_re.search(s): bad.append((path, "mot de passe du site"))
            if pat.search(s): bad.append((path, "clé/secret"))
            if hook.search(s): bad.append((path, "adresse de webhook / jeton dans une URL"))
for p, why in bad:
    print("SENSIBLE:", p, "->", why, file=sys.stderr)
sys.exit(1 if bad else 0)
