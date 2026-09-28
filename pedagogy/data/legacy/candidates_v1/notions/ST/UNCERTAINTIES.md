# Sciences et technologie 6e — incertitudes (agent B)

Toutes les notions de `ST/6E.json` sont des **candidats reconstitués de mémoire** :
`proof_status=UNPROVEN`, `source_type=CANDIDATE_UNVERIFIED`, `official_wording=null`,
source attendue `SRC-C3-2020` (référence « BO n°31 du 30/07/2020 », donnée de mémoire, non vérifiée).

## Organisation de la 6e à vérifier (priorité haute)
- En 6e (cycle 3), physique-chimie, SVT et technologie ne sont **pas** des matières séparées :
  elles relèvent de l'enseignement unique « Sciences et technologie » (sujet `SCIENCES_TECHNOLOGIE`).
  Le modèle interdit les notions `PC.6E.*` et `SVT.6E.*`.
- **L'organisation exacte de cet enseignement à la rentrée 2025-2026 doit être vérifiée** :
  de mémoire, la réforme de la 6e (rentrée 2023) a retiré l'heure de technologie de la grille
  horaire de 6e et réorganisé l'enseignement ; il existe peut-être un programme de sciences du
  cycle 3 réécrit ou aménagé depuis. Les notions du domaine `TEC` (objets techniques, matériaux,
  chaînes d'énergie et d'information, programmation) sont donc **les plus incertaines** : elles
  peuvent avoir été déplacées vers le cycle 4 (technologie de 5e) ou réduites.
- Le programme de cycle 3 couvre CM1-CM2-6e : ce qui est traité spécifiquement en 6e relève de
  repères de progressivité (à confirmer), pas d'un découpage strict.

## Domaines retenus (tous les thèmes de ST 6e dans un même fichier)
| Code | Thème (de mémoire) |
|---|---|
| MME | Matière, mouvement, énergie, information |
| TEC | Matériaux et objets techniques |
| VIV | Le vivant, sa diversité et les fonctions qui le caractérisent |
| TER | La planète Terre. Les êtres vivants dans leur environnement |

Libellés de thèmes et titres de chapitres = reconstitutions, pas des citations.

## Points de contenu à confirmer
- Circuit électrique simple en 6e (souvent traité au cycle 3, niveau exact incertain).
- Signal et information : place et étendue (codage binaire / morse).
- Mouvement de la Terre et saisons : ST 6e ou géographie / cycle 4 ?
- Programmation par blocs : ST 6e ou uniquement mathématiques / technologie cycle 4 ?

## Pilote
`pedagogy/data/pilot/ST_pilot_plan.json` est **BLOQUÉ** (`BLOCKED_NO_PROVEN_NOTION`).
