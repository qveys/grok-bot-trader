# La sonnette — mode d'emploi (Predict et Risk)

## C'est quoi ?

Un petit programme (gratuit, sans IA) regarde les prix toutes les 30 secondes.
Quand un prix que tu as choisi est touché, il **sonne** : il réveille ta routine
(PM-Predict ou PM-Risk) avec un message en français simple.

Il lit les prix déjà récoltés par l'équipe (`state/price_ticks/`). Il ne va pas
chercher les prix lui-même. Il ne passe **jamais** d'ordre et ne vend rien.

Le programme lui-même est dans `/workspace/tools/sonnette/` (ne pas modifier).

## Le seul fichier à écrire : `state/zones_reveil.json`

Une **zone** = « préviens-moi si ce prix est touché ». Exemple :

```json
{
  "zones": [
    {
      "id": "Z-SOL-98",
      "paire": "SOL-EUR",
      "sens": "sous",
      "prix": 98.0,
      "bot": "predict",
      "raison": "Support du jour",
      "expire": "2026-10-09T17:00:00+02:00",
      "actif": true
    }
  ]
}
```

Chaque ligne :

| Champ    | Ce qu'il faut mettre |
|----------|----------------------|
| `id`     | Un nom unique, par ex. `Z-SOL-98`. Deux zones ne peuvent pas avoir le même nom. |
| `paire`  | `BTC-EUR`, `ETH-EUR` ou `SOL-EUR` (rien d'autre). |
| `sens`   | `sous` = sonne si le prix descend à ce niveau ou plus bas. `au-dessus` = sonne si le prix monte à ce niveau ou plus haut. |
| `prix`   | Le prix en euros, un nombre (ex. `98.0`). |
| `bot`    | Qui réveiller : `predict` ou `risk`. |
| `raison` | Une phrase courte : pourquoi cette zone (facultatif, conseillé). |
| `expire` | Date et heure de fin, format `2026-10-09T17:00:00+02:00` (facultatif mais conseillé). Après, la zone est ignorée. |
| `actif`  | `true` = la zone marche. `false` = en pause. |

### Comment ajouter, changer ou enlever une zone

1. Ouvre `state/zones_reveil.json`.
2. Ajoute un bloc `{ ... }` dans la liste `"zones"` (sépare les blocs par une virgule).
3. Pour mettre en pause : `"actif": false`. Pour supprimer : enlève le bloc.
4. Enregistre. C'est pris en compte en 30 secondes, sans rien redémarrer.

Si une zone est mal écrite (paire inconnue, prix négatif, etc.), elle est **ignorée**
et une ligne l'explique dans `/workspace/tools/sonnette/state/sonnette.log`.
Les autres zones continuent de marcher. Si tout le fichier est cassé (virgule oubliée),
aucune zone ne marche : vérifie avec `/workspace/tools/sonnette/status.sh`.

## Les règles de la sonnette Predict

Réglage : `/workspace/tools/sonnette/config.json` (blocs `predict`, `idle`, `heure_limite`, `nuit`, `zones_distance`). Zones : `state/zones_reveil.json`, écrites par Predict.

- **Pas d'horaire fixe.** Toutes les **30 s** (`loop_seconds: 30`), elle compare le prix de BTC, ETH et SOL aux zones de `state/zones_reveil.json`, et elle sonne quand le prix touche une zone.
- **Active de 00h00 à 24h00, 7 jours sur 7** (`window_start "00:00"`, `window_end "24:00"`, `days 0 à 6`), heure de Bruxelles.
- **Chaque zone sonne au maximum 1 fois par jour.**
- **Predict est réveillé au maximum 6 fois par jour en tout** (`max_per_day: 6`). C'est un plafond, pas un programme : sans zone touchée, il n'y a pas de sonnerie. Les essais ne comptent pas.
- Deux autres sonneries comptent dans ces 6 :
  - **« sans décision »** (`idle`) : aucune décision D-xxx depuis **4 h** (`heures_sans_decision: 4`) et au moins **5 €** libres sous le plafond (`marge_min_eur: 5`). Au maximum **1 toutes les 4 h** (`intervalle_min_h: 4`) et **2 par nuit** (`max_par_nuit: 2`). La nuit va de **22h00 à 09h00** (`nuit`). En cas d'échec, nouvel essai après 5 min.
  - **« heure limite »** (`heure_limite`) : **une fois par trade**, quand son heure limite arrive. Risk ferme ou garde le trade **dans les 5 minutes** (`delai_risk_min: 5`). En cas d'échec, nouvel essai après 5 min, 3 essais au maximum.
- **Zones trop loin** : elle signale toute paire dont la zone la plus proche est à **plus de 1 %** du prix (`zones_distance.max_pct: 1.0`).
- **Prix trop vieux** : si le dernier prix a plus de **3 minutes** (`stale_seconds: 180`), elle ne sonne pas, pour ne pas réveiller sur un vieux prix.

Message reçu, par exemple : « SOL est passé sous 98 € (97,85 €) à 3h41. Predict, à toi de juger. »
La sonnette ne décide rien : c'est à Predict de juger.

## Les règles de la sonnette Risk (argent réel)

Elle ne sonne **que si une position en argent réel est ouverte**
(lue dans `guardian/state.json`, `state/positions.json`, `state/live_orders.jsonl`,
et les ordres ouverts Revolut X en lecture seule). Les positions **simulées ne sonnent jamais**
(c'est `watch_stops.py` qui s'en occupe).

Risk n'a **rien à écrire** pour le prix d'arrêt : la sonnette prend le prix d'arrêt
enregistré avec la position (`stop_price_eur`, ou sinon `stop_pct` appliqué au prix d'achat).

| Type (`kind`) | Quand | Combien de fois |
|---------------|-------|-----------------|
| `stop_hit`    | Le prix est au niveau du prix d'arrêt ou plus bas | Tout de suite, à toute heure. Rappel toutes les 10 min si toujours en dessous, 6 fois max par jour. |
| `stop_near`   | Le prix est à moins de 1 % au-dessus du prix d'arrêt | 1 fois par position et par jour. |
| `daily_loss`  | Perte du jour ≥ 12 % (argent réel) | 1 fois par jour, et encore 1 fois si on atteint 15 % (la limite). |
| `drawdown`    | Baisse depuis le plus haut ≥ 6 % (argent réel) | 1 fois par jour, et encore 1 fois à 8 % (la limite). |
| `stale_price` | Plus de prix reçus depuis 10 min | 1 fois, puis au maximum toutes les 30 min. |
| `manual_zone` | Une zone avec `"bot": "risk"` est touchée | 1 fois par zone et par jour. |

Pour `daily_loss` et `drawdown`, il faut en plus qu'un achat réel soit ouvert **ou** fait aujourd'hui.
Ils se calculent sur le **capital réel**, écrit toutes les 5 min dans `state/live_equity.json` :
l'argent EUR sur Revolut X (disponible + réservé) + la valeur du crypto **acheté par le bot**.
Le crypto que Quentin avait déjà (`hors_bot`) n'est **pas** compté. Un dépôt ou un retrait d'euros
(sans ordre du bot) n'est pas une perte ni un gain : la référence est décalée et c'est noté dans `ajustements`.
La perte du jour repart de zéro chaque jour à minuit. Si Revolut X ne répond pas, le fichier dit `"stale": true`
et ces deux alertes ne sonnent pas.

Quand un prix d'arrêt est touché, un fichier d'alerte est aussi écrit :
`/workspace/tools/sonnette/state/ALERTE_RISK_URGENTE.json` (`"actif": true`).
**Aucune vente n'est automatique** : Risk doit agir (LIVE_ONCE + live_place, comme d'habitude).

Un message avec `"test": true` est un essai : rien à faire.

## Vérifier que tout marche

```bash
/workspace/tools/sonnette/status.sh
```

Ça affiche : en marche ou non, l'âge du dernier prix, les dernières sonneries,
les compteurs du jour, et si on est en mode **dry** (rien n'est envoyé) ou **réel**.
