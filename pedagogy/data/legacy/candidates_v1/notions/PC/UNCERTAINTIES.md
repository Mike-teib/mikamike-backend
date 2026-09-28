# Physique-chimie — incertitudes (agent B)

Toutes les notions de `PC/*.json` sont des **candidats reconstitués de mémoire** :
`proof_status=UNPROVEN`, `source_type=CANDIDATE_UNVERIFIED`, `official_wording=null`,
`review_status=NOT_REVIEWED`, `publication_status=DRAFT`. Aucune source officielle (BO, Éduscol)
n'a pu être consultée : le réseau vers ces sites est bloqué dans l'environnement cloud.

## Sources attendues (à récupérer puis vérifier)
| Fichier | source_id | Doute |
|---|---|---|
| 5E, 4E, 3E | SRC-C4-2020 | Référence « BO n°31 du 30/07/2020 » donnée de mémoire. Vérifier qu'aucune version plus récente du programme de cycle 4 ne s'applique en 2025-2026. |
| 2NDE | SRC-2NDE-2019 | BO spécial n°1 du 22/01/2019 (de mémoire). Vérifier les éventuels allègements ou aménagements ultérieurs. |
| 1RE_SPECIALITE | SRC-1RE-2019 | Idem. |
| TLE_SPECIALITE | SRC-TLE-2019 | BO spécial n°8 du 25/07/2019 (de mémoire). Vérifier les aménagements (notions exclues des épreuves écrites, etc.). |

## Structure
- **Pas de PC en 6e** : au cycle 3, la physique-chimie fait partie de « Sciences et technologie »
  (`ST/6E.json`). Les prérequis de 5E pointent vers des notions `ST.6E.*`.
- **Cycle 4 = programme de cycle** : les attendus sont fixés pour la fin du cycle (5e-4e-3e) ; la
  répartition 5E / 4E / 3E adoptée ici est une **progression indicative** (choix fréquents en
  établissement), pas un découpage officiel. Placements particulièrement discutables :
  masse volumique (5e ou 4e), pH et solutions acides/basiques (4e ou 3e), atomes/molécules (5e ou 4e),
  vitesse du son et de la lumière (4e ou 3e), puissance/énergie électrique (3e ou 4e),
  interaction gravitationnelle (3e), distance d'arrêt (3e).
- **Codes de domaine** : cycle 4 `MAT`, `MVT`, `NRJ`, `SIG` (4 thèmes du cycle 4) ;
  lycée `MAT`, `MVT`, `NRJ`, `ONDE`. En 2nde, le programme ne comporte (de mémoire) que 3 thèmes :
  « Constitution et transformations de la matière », « Mouvement et interactions », « Ondes et
  signaux » ; les lois de l'électricité et les capteurs y sont rangés sous « Ondes et signaux ».
  Libellés de thèmes à confirmer.
- **Titres de chapitres** (`chapter`) : regroupements de travail, pas des intitulés officiels.

## Contenu à confirmer en priorité
- 2NDE : présence du **niveau d'intensité sonore** (qualitatif en 2nde ? calcul en Tle ?) ;
  « transformations nucléaires » (2nde) ; CCM et rapport frontal.
- 1RE : place exacte de la **mécanique des fluides** (1re spé) ; relation de conjugaison
  (1re ou 2nde) ; modèle du générateur réel ; énergie molaire de réaction / énergies de liaison.
- TLE : **effet Doppler**, **lunette astronomique**, **effet photoélectrique**, **Bernoulli**,
  **transferts thermiques / loi de Newton**, **électrolyse** : présents de mémoire, mais certains
  ont pu être exclus des épreuves écrites par des notes de service successives.
- TLE `t_acide_base` : le pH utilise le **logarithme décimal** ; le lien Maths pointe vers
  `MATHS.TLE.AN.fonction-logarithme-neperien` (seule ancre disponible), à affiner si une notion
  « logarithme décimal » est créée côté Maths.

## Liens inter-matières
Les `cross_subject_links` utilisent uniquement les ancres MATHS garanties et jamais une notion
de niveau supérieur au niveau PC. Certains appariements sont approximatifs (ex. f = 1/T relié à
`MATHS.6E.NC.fractions` au collège, à `fonctions-de-reference` en 2nde).

## Pilote
`pedagogy/data/pilot/PC_pilot_plan.json` est **BLOQUÉ** (`BLOCKED_NO_PROVEN_NOTION`) : aucune
notion prouvée, donc aucun exercice ne doit être produit.
