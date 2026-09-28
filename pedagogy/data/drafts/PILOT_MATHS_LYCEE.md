# Pilote brouillons Maths lycée : 2de, 1re spécialité, Tle spécialité

Statut : **BROUILLONS EN ATTENTE DE REVUE HUMAINE.** Tous les items sont `MODEL_ASSISTED_DRAFT`,
`qa_status = NOT_CHECKED` et `publication_status = READY_FOR_REVIEW`. Aucun n'est dans la banque servie.
Les 9 notions sources sont `PROVEN_OFFICIAL` mais encore `NOT_REVIEWED`. L'anomalie `NOTION_NOT_APPROVED`
est donc attendue jusqu'à la revue.

## Fichiers

| Fichier | Contenu |
|---|---|
| `exercises/MATHS_2NDE.json` | 54 exercices (3 notions × 18) |
| `exercises/MATHS_1RE.json` | 54 exercices |
| `exercises/MATHS_TLE.json` | 54 exercices |
| `quizzes/MATHS_2NDE.json` | 30 questions (3 notions × 10) |
| `quizzes/MATHS_1RE.json` | 30 questions |
| `quizzes/MATHS_TLE.json` | 30 questions |

Il y a **252 items** en tout : 162 exercices et 90 questions de quiz. Chaque notion compte 5 exercices DISCOVERY,
5 APPLICATION, 5 CONSOLIDATION, 3 ADVANCED et 10 questions de quiz (3 DISCOVERY, 3 APPLICATION,
3 CONSOLIDATION, 1 ADVANCED).

Les identifiants suivent la forme `EX.MATHS.<NIVEAU>.<slug>.<d|a|c|x><nn>` pour les exercices et
`QZ.MATHS.<NIVEAU>.<slug>.q<nn>` pour les quiz (NIVEAU = 2NDE, 1RE, TLE).

## Notions retenues

| Niveau | Slug | notion_id | Libellé officiel | Source |
|---|---|---|---|---|
| 2NDE | `fonctions-ref` | `MATHS.2NDE.FON.pour-les-fonctions-affines-valeur-absolue-carre-inverse-racine-carree` | « Pour les fonctions affines, valeur absolue, carré, inverse, racine carrée et cube, résoudre graphiquement ou algébriquement une équation ou une inéquation du type ƒ(𝑥) = k, ƒ(𝑥) < k. » | SRC-2NDE-MATHS-2026 |
| 2NDE | `produit-nul` | `MATHS.2NDE.NCA.equation-de-la-forme-a-x-b-x-0-equation-produit-nul` | « Équation de la forme A(𝑥)B(𝑥) = 0 (équation produit nul). » | idem |
| 2NDE | `colinearite` | `MATHS.2NDE.GEO.determinant-de-deux-vecteurs-dans-une-base-orthonormee-critere-de-coli` | « Déterminant de deux vecteurs dans une base orthonormée, critère de colinéarité. Application à l'alignement, au parallélisme. » | idem |
| 1RE | `second-degre` | `MATHS.1RE.ALG.forme-canonique-dune-fonction-polynome-du-second-degre-discriminant-fa` | « Forme canonique d'une fonction polynôme du second degré. Discriminant. Factorisation éventuelle. Résolution d'une équation du second degré. Signe. » | SRC-1RE-MATHS-SPE-2026 |
| 1RE | `derivation` | `MATHS.1RE.AN.dans-des-cas-simples-calculer-une-fonction-derivee-en-utilisant-les-pr` | « Dans des cas simples, calculer une fonction dérivée en utilisant les propriétés des opérations sur les fonctions dérivables. » | idem |
| 1RE | `suites` | `MATHS.1RE.ALG.pour-une-suite-arithmetique-ou-geometrique-calculer-le-terme-general-l` | « Pour une suite arithmétique ou géométrique, calculer le terme général, la somme de termes consécutifs, déterminer le sens de variation. » | idem |
| TLE | `limites-suites` | `MATHS.TLE.AN.etablir-la-convergence-dune-suite-ou-sa-divergence-vers-ou` | « Établir la convergence d'une suite, ou sa divergence vers + ∞ ou – ∞. » | SRC-TLE-MATHS-SPE-2019 |
| TLE | `exp-ln` | `MATHS.TLE.AN.utiliser-lequation-fonctionnelle-de-lexponentielle-ou-du-logarithme-po` | « Utiliser l'équation fonctionnelle de l'exponentielle ou du logarithme pour transformer une écriture, résoudre une équation, une inéquation. » | idem |
| TLE | `integrales` | `MATHS.TLE.AN.calculer-une-integrale-a-laide-dune-primitive-a-laide-dune-integration` | « Calculer une intégrale à l'aide d'une primitive, à l'aide d'une intégration par parties. » | idem |

Remarques sur le périmètre :

- **Choix des libellés.** Les notions dont le libellé a été aplati par l'extraction PDF (ex. « inéquation du premier
  degré du type a ⩾ b » en 2de, « (qn) » en Tle, « Pour 0 ⩽ k ⩽ n, formules : ») ont été écartées.
- **2de, fonctions de référence.** Les items couvrent carré, inverse, racine carrée, cube et valeur absolue, en
  équation (réponse calculée) et en inéquation (ensemble de solutions choisi parmi des intervalles).
- **2de, produit nul.** On factorise par facteur commun ou par identité remarquable, puis on applique la règle.
  Aucun item ne demande le discriminant (notion de 1re).
- **1re, dérivation.** Un seul item utilise l'exponentielle (dérivée de x·eˣ), qui est au programme de 1re. Aucun
  item de 1re n'utilise ln, intégrale ou primitive (lexique de Terminale).
- **Tle, limites.** Les limites infinies (+∞, −∞) ne sont pas lisibles par le vérificateur SymPy. Elles sont donc
  demandées en QCM (exercices CHOICE, quiz EXACT_TEXT). Les limites finies sont en MATH_EXPR.
- **Tle, intégrales.** Une question porte sur l'aire entre deux courbes, une autre sur la valeur moyenne. Ce sont
  des applications directes du calcul d'intégrale par primitive.

## Répartition des réponses (auto-corrigeables)

| Niveau | Exercices | Quiz | Formes imposées |
|---|---|---|---|
| 2NDE | 47 MATH_EXPR, 7 CHOICE | 22 MATH_EXPR, 8 EXACT_TEXT | aucune |
| 1RE | 46 MATH_EXPR, 7 CHOICE, 1 QUANTITY | 25 MATH_EXPR, 5 EXACT_TEXT | `developpee` × 1 |
| TLE | 48 MATH_EXPR, 6 CHOICE | 26 MATH_EXPR, 4 EXACT_TEXT | aucune |

Les solutions multiples s'écrivent « x = a ou x = b ». Les couples (forme canonique) s'écrivent « h = … ; k = … ».

## Contrôles effectués

1. **`python -m pedagogy.drafts check`** : PASS. Il n'y a aucune anomalie bloquante, aucune erreur de chargement
   et aucun avertissement sur les IDs `EX/QZ.MATHS.2NDE/1RE/TLE.*`.
2. **Vérification SymPy indépendante** : dans le script de construction, chaque réponse est recalculée à partir de
   l'énoncé, puis comparée à la réponse attendue. Les calculs utilisent `solveset`, `diff`, `limit`, `integrate`,
   `summation` et `discriminant`, selon la notion. Le détail est le suivant :
   - **Réponses MATH_EXPR (214 items)** : exercices et quiz, recalculées.
   - **QCM et quiz EXACT_TEXT (30 items)** : le choix correct est vérifié par calcul (ensemble de solutions d'une
     inéquation, colinéarité, limite infinie, dérivée d'une primitive…).
   - **Réponse QUANTITY (1 item)** : recalculée.
   - **Items conceptuels (7)** : relus à la main (ex. « un produit est nul si et seulement si… », formule
     (uv)′, théorème de comparaison).
3. **Doublons** (`pedagogy.qa.duplicates`) : aucun doublon exact, aucun doublon de gabarit et aucun
   `TOO_SIMILAR` sur les 252 items. Le contrôle a été fait sur ces items seuls puis avec l'ensemble des brouillons.
4. **Lexique de niveau** (`level_lexicon.check_text_level`, `is_too_simple`) : aucun terme au-dessus du niveau,
   aucun item DISCOVERY jugé trop simple.

## Limites connues (points d'attention pour la revue)

- **Nombre e.** Pour le vérificateur, `e` est une lettre, pas le nombre d'Euler. Une réponse d'élève « e^x(x+1) »
  ou « e² » est donc déclarée **INVALIDE** alors qu'elle est juste. Les énoncés concernés demandent d'écrire
  `exp(…)` : « écrire exp(x) pour eˣ », « écrire exp(1) pour e ». Les choix de quiz utilisent `exp(…)`. Le
  vérificateur doit évoluer (traiter `e` comme exp(1) en contexte d'analyse) avant publication.
- **Logarithme sans parenthèses.** « ln3 » ou « ln 3 » est envoyé en revue humaine. Il faut écrire « ln(3) ».
- **Limites infinies et intervalles.** Le vérificateur ne lit ni +∞ ni les intervalles. Les limites infinies et les
  ensembles solutions d'inéquations sont donc proposés en QCM. Il n'y a pas de saisie libre pour ces réponses.
- **Formes non imposées.** L'équivalence est symbolique. Une réponse non simplifiée mais égale est acceptée :
  « √50 » pour « 5√2 », une dérivée non réduite, « ln(8)/3 » pour « ln(2) ». Seul EX.MATHS.1RE.derivation.a01 impose la
  forme `developpee`. La forme canonique est demandée par ses paramètres « h = … ; k = … », car l'expression
  elle-même serait équivalente à la forme développée. De même, « écrire ln 8 sous la forme a ln 2 » demande
  seulement a.
- **Notation des fonctions dérivées.** L'apostrophe n'est pas autorisée dans une réponse MATH_EXPR : l'élève écrit
  l'expression seule (« 6x − 5 »), pas « f'(x) = … ».
- **Arrondis.** EX.MATHS.1RE.suites.c01 attend exactement 2086,69 (arrondi au centime) : 2086,7 est refusé. Le
  séparateur de milliers est évité dans les réponses. Les seuils (plus petit entier n…) sont des entiers exacts.
- **Grandeur.** La seule réponse QUANTITY (EX.MATHS.1RE.second-degre.x01, 8 m) exige l'unité : « 8 » seul est
  refusé, « 800 cm » est accepté.
- **Intégrales en LaTeX.** Les bornes sont écrites en LaTeX dans les énoncés (`$\int_{0}^{2} … \,dx$`) : il faut
  vérifier le rendu côté application. Les solutions sont rédigées en texte linéaire.
- **Figures.** Il n'y a aucune figure : les courbes (fonctions de référence, aire entre courbes) et les points
  (alignement) sont décrits en texte. Un relecteur peut vouloir ajouter des graphiques.
- **Diagnostics d'erreur.** Les `common_errors` et `distractor_rationale` sont des hypothèses didactiques
  plausibles. Ils sont à valider par un enseignant.

## Revue humaine

Relire au minimum : la conformité au programme (notamment la place des inéquations en 2de et de
l'exponentielle en 1re), le vocabulaire (racine, discriminant, convergence, primitive), la qualité des indices et
des remédiations. Ensuite, pour approuver :

```
python -m pedagogy.drafts approve --reviewer "<nom>" --notion <notion_id> ... --item <ID> ...
```
