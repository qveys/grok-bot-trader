#!/usr/bin/env python3
"""Garde-fou avant publication : refuse si un secret se trouve dans les dossiers donnés.
N'affiche jamais de valeur ; seulement le nom du fichier et le type de problème."""
import os, re, sys
bad = []
tok = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
pw = os.environ.get("DASHBOARD_PASSWORD") or ""
pw_re = re.compile(r"(?<![A-Za-z0-9])" + re.escape(pw) + r"(?![A-Za-z0-9])") if pw else None
pat = re.compile(r"BEGIN [A-Z ]*PRIVATE KEY|\"(api_?key|api_?secret|private_?key|access_?token|refresh_?token|client_?secret|mnemonic|seed_?phrase)\"\s*:", re.I)
wallet = re.compile(r"0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")   # adresse de portefeuille : jamais publiée (décision Quentin, 9 oct.)
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
            if wallet.search(s): bad.append((path, "adresse de portefeuille (0x…)"))
# Identifiants de bots / groupes (UUID) : interdits dans les règles publiées (summary.json → team_rules, tous champs texte).
# Ailleurs dans les JSON : seulement un avertissement (non bloquant), sauf sous les clés « numéro d'enregistrement »
# ci-dessous (numéros d'ordre Revolut X, id de trades/décisions) qui sont autorisées.
import json as _json
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
ID_KEYS = {"id", "order_id", "client_order_id", "venue_order_id"}
def _uuid_walk(o, key, in_rules, path, out):
    if isinstance(o, dict):
        for k, v in o.items():
            _uuid_walk(v, k, in_rules or k == "team_rules", path, out)
    elif isinstance(o, list):
        for v in o:
            _uuid_walk(v, key, in_rules, path, out)
    elif isinstance(o, str) and UUID.search(o):
        if in_rules:
            out.append((path, "identifiant (UUID) dans les règles publiées (team_rules." + str(key) + ")"))
        elif key not in ID_KEYS:
            print("AVERTISSEMENT:", path, "-> identifiant (UUID) dans le champ", key, "(non bloquant)", file=sys.stderr)
for root in sys.argv[1:]:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.endswith(".json") or f.startswith("."):
                continue
            path = os.path.join(dp, f)
            try:
                doc = _json.load(open(path, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            # paquet direct éventuel : {"files": {"summary": {...}}} — même parcours
            _uuid_walk(doc, None, False, path, bad)

for p, why in bad:
    print("SENSIBLE:", p, "->", why, file=sys.stderr)
sys.exit(1 if bad else 0)
