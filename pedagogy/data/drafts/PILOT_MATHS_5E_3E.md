# Pilote brouillons Maths collège : 5e, 4e, 3e

Statut : **BROUILLONS EN ATTENTE DE REVUE HUMAINE.** Tous les items sont `MODEL_ASSISTED_DRAFT`,
`qa_status = NOT_CHECKED` et `publication_status = READY_FOR_REVIEW`. Aucun n'est dans la banque servie.
Les 9 notions sources sont `PROVEN_OFFICIAL` mais encore `NOT_REVIEWED`. L'anomalie `NOTION_NOT_APPROVED`
est donc attendue jusqu'à la revue.

## Fichiers

| Fichier | Contenu |
|---|---|
| `exercises/MATHS_5E.json` | 54 exercices (3 notions × 18) |
| `exercises/MATHS_4E.json` | 54 exercices |
| `exercises/MATHS_3E.json` | 54 exercices |
| `quizzes/MATHS_5E.json` | 30 questions (3 notions × 10) |
| `quizzes/MATHS_4E.json` | 30 questions |
| `quizzes/MATHS_3E.json` | 30 questions |

Il y a **252 items** en tout : 162 exercices et 90 questions de quiz. Chaque notion compte 5 exercices DISCOVERY,
5 APPLICATION, 5 CONSOLIDATION, 3 ADVANCED et 10 questions de quiz.

Les identifiants suivent la forme `EX.MATHS.<NIVEAU>.<slug>.<d|a|c|x><nn>` pour les exercices et
`QZ.MATHS.<NIVEAU>.<slug>.q<nn>` pour les quiz.

## Notions retenues

| Niveau | Slug | notion_id | Libellé officiel (extrait) | Source |
|---|---|---|---|---|
| 5E | `fractions` | `MATHS.5E.NC.additionner-et-soustraire-des-fractions-de-denominateurs-quelconques` | « Additionner et soustraire des fractions de dénominateurs quelconques. » | Programme cycle 4, BO n°10 de 2026 |
| 5E | `distributivite` | `MATHS.5E.NC.exploiter-les-relations-k-a-b-ka-kb-ou-k-a-b-ka-kb-pour-factoriser-ou` | « Exploiter les relations k(a + b) = ka + kb ou k(a – b) = ka – kb pour factoriser, ou développer une expression littérale. » | idem |
| 5E | `angles-triangle` | `MATHS.5E.EG.connaitre-la-somme-des-angles-dun-triangle-et-savoir-la-demontrer` | « Connaitre la somme des angles d'un triangle et savoir la démontrer. » | idem |
| 4E | `puissances-10` | `MATHS.4E.NC.les-puissances-de-10-sont-dabord-introduites-avec-des-exposants-positi` | « Les puissances de 10 […] afin de définir les préfixes de nano à giga et la notation scientifique […] » | Programme cycle 4 2020, repères Éduscol |
| 4E | `equations` | `MATHS.4E.NC.les-equations-sont-travaillees-tout-au-long-de-lannee-par-un-choix-pro` | « Les équations sont travaillées tout au long de l'année par un choix progressif des coefficients […] » | idem |
| 4E | `pythagore-thales` | `MATHS.4E.EG.le-theoreme-de-thales-et-sa-reciproque-dans-la-configuration-des-trian` | « Le théorème de Thalès et sa réciproque dans la configuration des triangles emboîtés […] ainsi que le théorème de Pythagore […] et sa réciproque. » | idem |
| 3E | `fonctions-affines` | `MATHS.3E.OGDF.les-fonctions-affines-et-lineaires-sont-presentees-par-leurs-expressio` | « Les fonctions affines et linéaires sont présentées par leurs expressions algébriques et leurs représentations graphiques. » | idem |
| 3E | `trigonometrie` | `MATHS.3E.EG.les-lignes-trigonometriques-cosinus-sinus-tangente-dans-le-triangle-re` | « Les lignes trigonométriques (cosinus, sinus, tangente) dans le triangle rectangle sont utilisées pour calculer des longueurs ou des angles. » | idem |
| 3E | `probabilites` | `MATHS.3E.OGDF.les-calculs-de-probabilites-a-partir-de-denombrements-sappliquent-a-de` | « Les calculs de probabilités, à partir de dénombrements, s'appliquent à des contextes simples faisant prioritairement intervenir une seule épreuve. » | idem |

Remarques sur le périmètre :

- **4E, Pythagore.** Le registre 4E ne contient pas de notion « Pythagore » séparée. Le théorème figure dans la
  notion Thalès (triangles emboîtés). Les items de cette notion couvrent donc les deux théorèmes : environ 12
  exercices et 7 questions portent sur Pythagore et sa réciproque, environ 6 exercices et 3 questions sur Thalès
  et sa réciproque.
- **5E, fractions.** La « fraction irréductible » n'est introduite qu'en 3e (repères 2020). En 5e, on demande
  seulement une fraction « simplifiée si possible », sans forme imposée : toute écriture équivalente est acceptée.
- **3E, probabilités.** Tous les items portent sur une seule épreuve, conformément au libellé. Les expériences à
  deux épreuves relèvent d'une autre notion.

## Répartition des réponses (auto-corrigeables)

| Niveau | Exercices | Quiz | Formes imposées |
|---|---|---|---|
| 5E | 49 MATH_EXPR, 5 CHOICE | 17 MATH_EXPR, 13 EXACT_TEXT | `developpee` × 9 |
| 4E | 24 MATH_EXPR, 23 QUANTITY, 7 CHOICE | 17 MATH_EXPR, 7 EXACT_TEXT, 6 QUANTITY | `notation_scientifique` × 7 |
| 3E | 40 MATH_EXPR, 10 QUANTITY, 4 CHOICE | 19 MATH_EXPR, 9 EXACT_TEXT, 2 QUANTITY | `developpee` × 4, `fraction_irreductible` × 2 |

## Contrôles effectués

1. **`python -m pedagogy.drafts check`** : PASS. Il n'y a aucune anomalie bloquante, aucune erreur de chargement
   et aucun avertissement sur les IDs `EX/QZ.MATHS.5E/4E/3E.*`.
2. **Vérification SymPy indépendante** : 200 réponses sur 252 sont recalculées à partir d'un calcul de référence
   écrit à part, puis comparées à la réponse attendue. Il s'agit de toutes les réponses MATH_EXPR et QUANTITY, y
   compris les développements, les expressions affines et les valeurs trigonométriques arrondies. Les 52 autres
   (CHOICE, EXACT_TEXT conceptuels) ont été relues à la main.
3. **Doublons de gabarit** (`similarity.template_fingerprint`, énoncés identiques aux nombres près) : aucun dans
   les 252 items.

## Limites connues (points d'attention pour la revue)

- **Factorisation.** La forme `factorisee` refuse `3(x + 5)`, car SymPy redistribue un facteur numérique. Les
  factorisations sont donc demandées sous la forme « compléter k × (…) » : on attend le contenu de la parenthèse,
  sans forme imposée.
- **Angles.** L'unité « ° » n'est pas reconnue par le vérificateur de grandeurs. Les mesures d'angles sont donc des
  MATH_EXPR entières, avec « en degrés » dans l'énoncé. Dans les quiz, les choix portent « ° » et sont en
  EXACT_TEXT. Une réponse d'élève non arrondie (ex. 48,2 au lieu de 48) est refusée.
- **Longueurs arrondies.** Les longueurs arrondies (QUANTITY) acceptent un écart relatif de 1 %.
- **Unités.** L'euro et le degré Fahrenheit ne sont pas des unités reconnues. Ces réponses sont donc de simples
  nombres (MATH_EXPR), et l'unité figure dans l'énoncé.
- **Écriture des nombres.** Les décimaux qui portent une réponse MATH_EXPR sont écrits « 0,01 », jamais
  `0{,}01` en LaTeX : le vérificateur ne lit pas `{,}`. Les grands entiers réponses sont évités, car le séparateur
  de milliers (« 10 000 ») serait lu comme un produit implicite.
- **Figures.** Il n'y a aucune figure : les configurations géométriques sont décrites en texte. Un relecteur peut
  vouloir ajouter des schémas (échelle, Thalès, cerf-volant, triangle isocèle).
- **Diagnostics d'erreur.** Les `common_errors` et `distractor_rationale` sont des hypothèses didactiques
  plausibles. Ils sont à valider par un enseignant.

## Revue humaine

Relire au minimum : la conformité au niveau, la justesse du vocabulaire (côté adjacent/opposé, image/antécédent,
etc.), la qualité des indices et des remédiations. Ensuite, pour approuver :

```
python -m pedagogy.drafts approve --reviewer "<nom>" --notion <notion_id> ... --item <ID> ...
```
