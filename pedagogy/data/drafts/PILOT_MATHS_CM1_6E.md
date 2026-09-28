# Pilote brouillons MATHS — CM1, CM2, 6e

Statut : **brouillons** (`generation_origin = MODEL_ASSISTED_DRAFT`, `qa_status = NOT_CHECKED`,
`publication_status = READY_FOR_REVIEW`). Rien n'est servi aux élèves avant la revue humaine de
la notion ET de chaque item (`python -m pedagogy.drafts approve …`).

Source de calibrage : *Programme de mathématiques pour le cycle 3*, BO n°16 du 17 avril 2025
(`SRC-C3-MATHS-NOUVEAU`, PDF local `pedagogy/sources_local/official/programme-mathematiques-cycle3-2025.pdf`).
Toutes les notions retenues sont `PROVEN_OFFICIAL` ; leur libellé est complet (pas de « … ») et non altéré.

## Fichiers

| Fichier | Contenu |
|---|---|
| `exercises/MATHS_CM1.json`, `quizzes/MATHS_CM1.json` | 54 exercices + 30 questions |
| `exercises/MATHS_CM2.json`, `quizzes/MATHS_CM2.json` | 54 exercices + 30 questions |
| `exercises/MATHS_6E.json`, `quizzes/MATHS_6E.json` | 54 exercices + 30 questions |

Total : **162 exercices + 90 questions de quiz = 252 items**, soit 9 notions × (5 DISCOVERY + 5 APPLICATION +
5 CONSOLIDATION + 3 ADVANCED + 10 quiz). Les quiz sont répartis 3 / 3 / 3 / 1 selon les mêmes niveaux.

Identifiants : `EX.MATHS.<NIVEAU>.<slug>.<d|a|c|x><nn>` et `QZ.MATHS.<NIVEAU>.<slug>.q<nn>`.

## Notions retenues et justification

### CM1

| Slug | Notion | Pourquoi |
|---|---|---|
| `fraction-quantite` | `MATHS.CM1.NCRP.determiner-une-fraction-dune-quantite-ou-dune-grandeur` | Fractions : notion centrale du CM1. Programme : au CM1, la fraction devient opérateur **uniquement pour les fractions unitaires** (« un tiers de 12 billes, un quart de 100 mètres »), dénominateurs ≤ 20. Tous les items respectent cette limite (1/2 à 1/12). |
| `comparaison-mult` | `MATHS.CM1.NCRP.resoudre-des-problemes-de-comparaison-multiplicative` | Résolution de problèmes, structure explicitement listée. Plusieurs items reprennent le piège signalé par le programme (énoncé contenant « plus » alors qu'il faut diviser). |
| `proportionnalite` | `MATHS.CM1.PROP.savoir-resoudre-un-probleme-de-proportionnalite` | Grandeurs et proportionnalité. Programme : **linéarité multiplicative seulement**, raisonnements en langage naturel (« 3 fois plus de pains, je paie 3 fois plus »), **pas de tableau, pas de coefficient, pas de produit en croix**, toujours dans le cadre des grandeurs. Les solutions sont rédigées ainsi ; les items ADVANCED enchaînent deux raisonnements multiplicatifs (passer par 2 objets). |

### CM2

| Slug | Notion | Pourquoi |
|---|---|---|
| `fractions-addition` | `MATHS.CM2.NCRP.additionner-et-soustraire-des-fractions` | Fractions. Dénominateurs ≤ 60 (fractions décimales jusqu'à 100). Majorité d'items à même dénominateur ; les items CONSOLIDATION/ADVANCED s'appuient sur les relations usuelles (1/2 = 2/4, 1/10 = 10/100) données dans l'énoncé ou connues en calcul mental. |
| `problemes-mixtes` | `MATHS.CM2.NCRP.resoudre-des-problemes-mixtes-en-plusieurs-etapes` | Résolution de problèmes (additif + multiplicatif), 2 à 4 étapes ; nombres décimaux limités à décimal × entier et division par un entier à un chiffre (ou partage simple), conformes aux opérations du CM2. |
| `aire-rectangle` | `MATHS.CM2.GM.determiner-laire-dun-carre-ou-dun-rectangle` | Grandeurs et mesures. Unités cm², dm², m² uniquement (celles du programme CM2) ; dimensions entières ; distinction aire / périmètre travaillée dans les erreurs fréquentes. |

### 6e

| Slug | Notion | Pourquoi |
|---|---|---|
| `produit-decimaux` | `MATHS.6E.NCRP.calculer-le-produit-de-deux-nombres-decimaux` | Nouveauté de la 6e. Démarche du programme : se ramener à un produit d'entiers, placer la virgule, **contrôler par un ordre de grandeur** (items dédiés). |
| `pourcentage` | `MATHS.6E.NCRP.appliquer-un-pourcentage-a-une-grandeur-ou-a-un-nombre` | Pourcentages (chapitre « Les fractions ») : p % = p/100, repères 50 %, 25 %, 10 %, 1 %, décompositions (15 % = 10 % + 5 %), remises et augmentations simples. |
| `angles-triangle` | `MATHS.6E.EG.connaitre-la-valeur-de-la-somme-des-mesures-des-angles-dun-triangle` | Géométrie. La notion voisine « L'utiliser pour calculer des angles… » a un titre dépendant (pronom « L' ») : elle n'a pas été retenue comme notion porteuse, mais son usage (calcul du 3e angle) est la mise en œuvre naturelle de la notion choisie. Quelques items mobilisent aussi les propriétés angulaires des triangles particuliers (même chapitre). |

Notions écartées volontairement : titres tronqués (« … »), titres altérés (ex. « la fraction a b »),
et notions au libellé non autonome (« L'utiliser pour… »).

## Choix de format des réponses

- `MATH_EXPR` pour les nombres, fractions (`5/7`, équivalents acceptés : `10/14`, `1 + 2/5`…) et décimaux (virgule ou point).
- `QUANTITY` avec unité pour les longueurs, masses, contenances, durées et aires (`cm²`, `m²`…).
- Les montants en euros et les angles en degrés sont en `MATH_EXPR` (le vérificateur ne connaît ni `€` ni `°`) ;
  l'énoncé précise « en euros » / « en degrés », et la solution écrit « euros » / « degrés » en toutes lettres.
- `CHOICE` pour les 14 exercices QCM (3 ou 4 choix, un seul correct, position de la bonne réponse variée).

## Contrôle automatique

`python -m pedagogy.drafts check` : **PASS**, 0 bloquant, 0 erreur de chargement, 0 avertissement sur
les identifiants `EX.MATHS.{CM1,CM2,6E}.*` et `QZ.MATHS.{CM1,CM2,6E}.*` (seule l'anomalie tolérée
`NOTION_NOT_APPROVED` subsiste, les notions n'étant pas encore relues).

Toutes les valeurs numériques ont été calculées par script (`fractions.Fraction`, `decimal.Decimal`), et les
90 clés de quiz ainsi que les 162 réponses attendues ont été relues une à une.

## Limites et points d'attention pour la relecture

1. **Nombres ≥ 1 000 en réponse** : le vérificateur n'accepte pas l'écriture française « 1 200 » (espace des
   milliers) comme égale à 1200. Aucune réponse attendue n'atteint donc 1 000 ; les grands nombres
   n'apparaissent que dans les énoncés et les étapes de calcul.
2. **Réponses fractionnaires** : une réponse équivalente non simplifiée ou simplifiée est acceptée
   (`5/10` ≡ `1/2`). Si l'on veut exiger une forme (irréductible, entier), il faudra ajouter un `required_form`.
3. **Unités** : en `QUANTITY`, une réponse juste dans une autre unité (`0,5 m` pour `50 cm`) est acceptée, sauf
   ajout de `required_form = unite_imposee`.
4. **Pas de figures** : les exercices de géométrie et d'aire sont rédigés sans schéma ; un relecteur peut
   souhaiter ajouter des illustrations (quadrillage, triangle codé).
5. **Calibrage** : les formulations suivent le programme 2025, mais le choix des nombres (taille, période de
   l'année) reste à valider par un enseignant. Au CM1, la notion de fraction d'une quantité est volontairement
   limitée aux fractions unitaires ; la « reconstitution du tout » (`fraction-quantite.x01`, quiz q10) est un
   prolongement à confirmer.
6. **Proximité de notions** : quelques items d'`angles-triangle` utilisent les triangles isocèles, rectangles
   et équilatéraux (notion voisine `connaitre-et-utiliser-les-proprietes-angulaires-des-triangles-particul`) ;
   `source_notions` ne contient que la notion porteuse, comme demandé.

## Régénération

Le contenu est écrit explicitement dans un générateur Python (hors dépôt, espace de travail de la session :
`cm1.py`, `cm2.py`, `s6.py`, `common.py`, `build.py`). Les fichiers JSON du dépôt sont la référence ; toute
correction de relecture peut être faite directement dans les JSON.
