# Format commun des journaux de bord (Quentin, 8 oct. 2026, 23h15)

Chaque bot tient `knowledge/bot_journals/<bot>.md` dans ce format exact. Exemple : `knowledge/bot_journals/grok-bot.md`.

```
# Journal — PM-Xxx
_Mis à jour : 8 oct. 2026, 23h20_

## 1. Mon rôle
2 lignes max : ce que je fais / ce que je ne fais pas.

## 2. Les règles que j'applique
_Source : règles d'équipe, version du <date heure>._
- **Règle (mots simples)** : ce que je fais concrètement pour la tenir.
(seulement les règles qui me concernent, sans recopier tout le fichier)

## 3. En cours / à faire
- Positions ou décisions ouvertes (D-xxx), prochaine échéance avec l'heure. « Rien » si rien.

## 4. Journal
### 8 oct. 2026   (jour le plus récent en haut)
- **23h00** · 📌 texte d'une ligne (D-xxx si lié)
```

Types d'entrée : ✅ fait · 📌 décision · 🔔 alerte · ⚠️ problème · 💡 leçon · 📜 règle reçue.

Points fixes :
- Heure de Bruxelles au format `23h00` : pas de « ~ », pas de « 13:1x », pas de date brute.
- Une ligne par entrée. Seulement ce qui compte : les passages « rien de nouveau » restent dans le journal des routines (`state/routine_runs.jsonl`), pas ici.
- Français simple, sans jargon.
- 7 jours dans le fichier ; le reste va dans `knowledge/bot_journals/archives/<bot>-AAAA-MM.md`.
- Avant la première réécriture : copier l'ancien fichier dans `knowledge/bot_journals/archives/<bot>-avant-format.md`.
- La section 2 reformule les règles avec ses propres mots, pour montrer qu'on les a comprises et comment on les applique.
- Mettre à jour les sections 2 et 3 dès qu'une règle ou une position change.
