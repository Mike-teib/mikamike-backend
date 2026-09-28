# Pilote MATHS CP, CE1, CE2 : notions retenues

Brouillons `MODEL_ASSISTED_DRAFT` (qa_status `NOT_CHECKED`, publication_status `READY_FOR_REVIEW`). Chaque exercice et chaque question doit être relu par un humain avant d'entrer dans la banque.

Source des notions : programme du cycle 2 publié en 2025 (`SRC-C2-MATHS-2025`, `pedagogy/sources_local/official/cycle2_nouveau_2025_bo41_annexe4.pdf`). Toutes les notions retenues sont `PROVEN_OFFICIAL`, `review_status = NOT_REVIEWED`. Le contrôle `check` les signale donc comme `NOTION_NOT_APPROVED`, ce qui est attendu.

Fichiers :
- `exercises/MATHS_CP.json`, `exercises/MATHS_CE1.json`, `exercises/MATHS_CE2.json` : 3 notions × 18 exercices (5 DISCOVERY, 5 APPLICATION, 5 CONSOLIDATION, 3 ADVANCED) par niveau.
- `quizzes/MATHS_CP.json`, `quizzes/MATHS_CE1.json`, `quizzes/MATHS_CE2.json` : 3 notions × 10 questions par niveau.

Total : 162 exercices et 90 questions de quiz.

Pour chaque niveau, on a pris une notion de numération, une notion d'opérations ou de résolution de problèmes, et une notion de grandeurs et mesures. Aucune notion dont le libellé est tronqué n'a été retenue.

## CP (nombres jusqu'à 100)

| Slug | notion_id | Libellé officiel | Pourquoi |
|---|---|---|---|
| `valeur-position` | `MATHS.CP.NCRP.connaitre-la-valeur-des-chiffres-en-fonction-de-leur-position-unites-d` | Connaitre la valeur des chiffres en fonction de leur position (unités, dizaines). | C'est le cœur de la numération décimale au CP. Le programme demande de savoir expliquer pourquoi 23 ≠ 32. |
| `parties-tout` | `MATHS.CP.NCRP.resoudre-des-problemes-additifs-en-une-etape-du-type-parties-tout` | Résoudre des problèmes additifs en une étape du type parties-tout. | C'est la première structure de problème du programme. Elle couvre aussi les transformations (ajout, retrait), recherche de l'état initial comprise, que le programme traite comme des problèmes parties-tout. |
| `valeur-euros` | `MATHS.CP.GM.determiner-la-valeur-en-euro-dun-ensemble-constitue-de-pieces-et-de-bi` | Déterminer la valeur en euro d'un ensemble constitué de pièces et de billets. | Cette notion de grandeurs relie la monnaie à la numération (groupes de dix euros). Elle se corrige automatiquement. Montants entiers et au plus égaux à 100 €, comme le prévoit le programme. |

## CE1 (nombres jusqu'à 1 000)

| Slug | notion_id | Libellé officiel | Pourquoi |
|---|---|---|---|
| `valeur-position` | `MATHS.CE1.NCRP.connaitre-la-valeur-des-chiffres-en-fonction-de-leur-position-dans-un` | Connaitre la valeur des chiffres en fonction de leur position dans un nombre. | Passage aux centaines. Le programme donne des écritures du type « 5 unités, 5 centaines et 13 dizaines » et des décompositions (6 × 100) + (3 × 10) + (5 × 1). |
| `multiplicatifs` | `MATHS.CE1.NCRP.resoudre-des-problemes-multiplicatifs-en-une-etape` | Résoudre des problèmes multiplicatifs en une étape. | Structure nouvelle au CE1, et centrale. On y trouve les trois types de problèmes du programme : recherche du tout, du nombre de parts et de la valeur d'une part. Le symbole « ÷ » n'est pas utilisé, car il n'arrive qu'au CE2. |
| `unites-longueur` | `MATHS.CE1.GM.connaitre-les-relations-entre-les-unites-de-longueur-usuelles` | Connaitre les relations entre les unités de longueur usuelles. | Les relations sont 1 m = 100 cm et 1 km = 1 000 m. Les réponses sont des grandeurs avec unité, vérifiées automatiquement. Pas d'écriture à virgule et aucun résultat au-delà de 1 000, comme le prévoit le programme. |

## CE2 (nombres jusqu'à 10 000)

| Slug | notion_id | Libellé officiel | Pourquoi |
|---|---|---|---|
| `valeur-position` | `MATHS.CE2.NCRP.connaitre-la-valeur-des-chiffres-en-fonction-de-leur-position-dans-un` | Connaitre la valeur des chiffres en fonction de leur position dans un nombre. | Extension aux milliers. On compte aussi le nombre total de centaines ou de dizaines d'un nombre, et on traite le problème des « lots de cent » donné en exemple par le programme. |
| `sens-division` | `MATHS.CE2.NCRP.comprendre-le-sens-de-la-division-et-utiliser-le-symbole` | Comprendre le sens de la division et utiliser le symbole « ÷ ». | Nouveauté du CE2 : partage, groupement et division comme opération inverse de la multiplication. Seulement des divisions exactes appuyées sur les tables, puisque la division posée n'est pas au programme du CE2. |
| `perimetre` | `MATHS.CE2.GM.savoir-ce-quest-le-perimetre-dune-figure-plane` | Savoir ce qu'est le périmètre d'une figure plane. | Le périmètre est défini comme « la longueur du contour ». Pour le carré et le rectangle, on ne donne aucune formule : l'élève fait le tour de la figure, comme le prévoit le programme. |

## Points d'attention pour la relecture

- **Nombres à 4 chiffres (CE2)** : le vérificateur accepte désormais les espaces de milliers (« 4 635 » ≡ « 4635 »). Les anciens contournements `EXACT_TEXT` restent compatibles mais ne sont plus nécessaires pour les nouveaux items.
- **Euros** : l'unité « € » / « euro(s) » est désormais reconnue. Les anciens items numériques restent valides ; les nouveaux peuvent utiliser `QUANTITY` avec unité monétaire.
- **Problèmes à reste (CE1)** : `multiplicatifs.x01`, `x02`, `x03` et les quiz `q09` et `q10` reprennent les exemples du programme (« combien de boîtes pleines », « combien de pages faut-il »). Le relecteur doit vérifier que la consigne est claire pour l'élève.
- Les contrôles `TOO_SIMILAR`, `DUPLICATE_TEMPLATE` et `TOO_ADVANCED` du module `pedagogy.qa` ont aussi été lancés sur ces fichiers : aucune alerte.
