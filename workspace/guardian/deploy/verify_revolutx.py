#!/usr/bin/env python3
"""Test de l'étape 4 : appel signé GET /1.0/balances sur Revolut X.

Usage :
  REVX_API_KEY=... REVX_PRIVATE_KEY_PATH=/etc/grok-bot/private.pem python3 verify_revolutx.py
Sortie attendue : "OK — soldes : [...]" (liste vide tant que l'exchange n'est pas alimenté).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from guardian.revolutx import RevolutXClient, RevolutXError  # noqa: E402

key = os.environ.get("REVX_API_KEY", "")
pk = os.environ.get("REVX_PRIVATE_KEY_PATH", "")
if not key or not pk:
    sys.exit("Définir REVX_API_KEY et REVX_PRIVATE_KEY_PATH")

client = RevolutXClient(key, pk)
try:
    balances = client.balances()
except RevolutXError as exc:
    sys.exit(f"ÉCHEC — {exc}\n401 = signature/clé invalide ; 403 = permissions de la clé")
print(f"OK — soldes : {balances or '{} (exchange vide, normal avant dépôt)'}")
pairs = client.markets()
eur = [p for p in pairs if p.endswith("-EUR")]
print(f"OK — {len(pairs)} paires actives, dont {len(eur)} en EUR ; min BTC-EUR : "
      f"{pairs.get('BTC-EUR', {}).get('minOrderInQuoteAsset', '?')} EUR")
