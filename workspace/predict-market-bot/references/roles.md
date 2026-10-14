# Rôles — qui fait quoi

- **Scan** — prix publics + historique (`scan_crypto`, `last_scan.json`, `scan_history.jsonl`).
- **Research** — brief marché / contexte (`research_briefs/`, `last_research.json`).
- **Predict** — décisions d’achat ou non (`last_predict.json`, carnet de décisions).
- **Risk** — validation, `live_place`, alertes (`validate_order`, `check_alerts`, gardes live).
- **Compound** — post-mortems après vente (journal trades, leçons, pauses de type).
- **Orchestrator** — coordination du pipeline Scan→Research→Predict→Risk→Compound.
- **Grok Bot** — uniquement méta / interface utilisateur (pas de trading autonome).
