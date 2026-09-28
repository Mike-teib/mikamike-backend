# Pilote brouillons Physique-chimie : 5e, 4e, 3e, 2de, 1re spécialité, Tle spécialité

Statut : **BROUILLONS EN ATTENTE DE REVUE HUMAINE.** Tous les items sont `MODEL_ASSISTED_DRAFT`,
`qa_status = NOT_CHECKED` et `publication_status = READY_FOR_REVIEW`. Aucun n'est dans la banque servie.
Les 18 notions sources sont `PROVEN_OFFICIAL` mais encore `NOT_REVIEWED`. L'anomalie `NOTION_NOT_APPROVED`
est donc attendue jusqu'à la revue.

## Fichiers

| Fichier | Contenu |
|---|---|
| `exercises/PC_5E.json`, `quizzes/PC_5E.json` | 54 exercices, 30 questions |
| `exercises/PC_4E.json`, `quizzes/PC_4E.json` | 54 exercices, 30 questions |
| `exercises/PC_3E.json`, `quizzes/PC_3E.json` | 54 exercices, 30 questions |
| `exercises/PC_2NDE.json`, `quizzes/PC_2NDE.json` | 54 exercices, 30 questions |
| `exercises/PC_1RE.json`, `quizzes/PC_1RE.json` | 54 exercices, 30 questions (spécialité) |
| `exercises/PC_TLE.json`, `quizzes/PC_TLE.json` | 54 exercices, 30 questions (spécialité) |

Il y a **504 items** en tout : 324 exercices et 180 questions de quiz. Chaque notion compte 5 exercices DISCOVERY,
5 APPLICATION, 5 CONSOLIDATION, 3 ADVANCED et 10 questions de quiz.

Les identifiants suivent la forme `EX.PC.<NIVEAU>.<slug>.<d|a|c|x><nn>` pour les exercices et
`QZ.PC.<NIVEAU>.<slug>.q<nn>` pour les quiz (NIVEAU = 5E, 4E, 3E, 2NDE, 1RE, TLE). Tous les items ont
`subject = PHYSIQUE_CHIMIE`.

## Notions retenues

| Niveau | Slug | notion_id | Libellé officiel | Source |
|---|---|---|---|---|
| 5E | `etats` | `PC.5E.MAT.caracteriser-les-differents-etats-de-la-matiere-solide-liquide-et-gaz` | Caractériser les différents états de la matière (solide, liquide et gaz) | SRC-C4-2020 |
| 5E | `masse-changement-etat` | `PC.5E.MAT.conservation-de-la-masse-variation-du-volume-temperature-de-changement` | Conservation de la masse, variation du volume, température de changement d'état | idem |
| 5E | `circuits-serie-derivation` | `PC.5E.NRJ.dipoles-en-serie-dipoles-en-derivation` | Dipôles en série, dipôles en dérivation | idem |
| 4E | `masse-volumique` | `PC.4E.MAT.exploiter-des-mesures-de-masse-volumique-pour-differencier-des-especes` | Exploiter des mesures de masse volumique pour différencier des espèces chimiques | idem |
| 4E | `vitesse` | `PC.4E.MVT.utiliser-la-relation-liant-vitesse-distance-et-duree-dans-le-cas-dun-m` | Utiliser la relation liant vitesse, distance et durée dans le cas d'un mouvement uniforme | idem |
| 4E | `loi-ohm` | `PC.4E.NRJ.relation-tension-courant-loi-dohm` | Relation tension-courant : loi d'Ohm | idem |
| 3E | `energie-cinetique` | `PC.3E.NRJ.energies-cinetique-relation-ec-12-mv2-potentielle-dependant-de-la-posi` | Énergies cinétique (Ec = ½ mv²), potentielle… | idem |
| 3E | `poids` | `PC.3E.MVT.force-de-pesanteur-et-son-expression-p-mg` | Force de pesanteur et son expression P = mg | idem |
| 3E | `atome` | `PC.3E.MAT.constituants-de-latome-structure-interne-dun-noyau-atomique-nucleons-p` | Constituants de l'atome, structure interne d'un noyau atomique (nucléons), électrons | idem |
| 2NDE | `quantite-matiere` | `PC.2NDE.CTM.determiner-le-nombre-dentites-et-la-quantite-de-matiere-en-mol-dune-es` | Déterminer le nombre d'entités et la quantité de matière (en mol) d'une espèce dans une masse d'échantillon | SRC-2NDE-PC-2019 |
| 2NDE | `vitesse-moyenne` | `PC.2NDE.MI.definir-le-vecteur-vitesse-moyenne-dun-point` | Définir le vecteur vitesse moyenne d'un point | idem |
| 2NDE | `periode-frequence` | `PC.2NDE.OS.relation-entre-periode-et-frequence` | Relation entre période et fréquence | idem |
| 1RE | `titrage-equivalence` | `PC.1RE.CTM.etablir-la-relation-entre-les-quantites-de-matiere-de-reactifs-introdu` | Établir la relation entre les quantités de matière de réactifs introduites pour atteindre l'équivalence | SRC-1RE-PC-2019 |
| 1RE | `energie-mecanique` | `PC.1RE.ENERGIE.exploiter-la-conservation-de-lenergie-mecanique-dans-des-cas-simples-c` | Exploiter la conservation de l'énergie mécanique dans des cas simples (chute libre, pendule sans frottement) | idem |
| 1RE | `ondes-periodiques` | `PC.1RE.OS.justifier-et-exploiter-la-relation-entre-periode-longueur-d-onde-et-ce` | Justifier et exploiter la relation entre période, longueur d'onde et célérité | idem |
| TLE | `ph-oxonium` | `PC.TLE.CTM.determiner-a-partir-de-la-valeur-de-la-concentration-en-ion-oxonium-h3` | Déterminer, à partir de [H3O+], la valeur du pH de la solution et inversement | SRC-TLE-PC-2019 |
| TLE | `equations-horaires` | `PC.TLE.MI.etablir-et-exploiter-les-equations-horaires-du-mouvement` | Établir et exploiter les équations horaires du mouvement | idem |
| TLE | `decroissance-radioactive` | `PC.TLE.CTM.exploiter-la-loi-et-une-courbe-de-decroissance-radioactive` | Exploiter la loi et une courbe de décroissance radioactive | idem |

Critère de choix : notions centrales du programme, évaluables par une réponse numérique ou un choix
non ambigu. Les notions purement expérimentales (« mettre en œuvre », « réaliser », capacités numériques) ont été
écartées : elles ne se corrigent pas automatiquement.

## Répartition des réponses

| Niveau | Exercices | Quiz | Réponses avec `significant_figures` |
|---|---|---|---|
| 5E | 24 CHOICE, 14 QUANTITY, 10 EXACT_TEXT, 5 MATH_EXPR, 1 ORDERING | 22 EXACT_TEXT, 6 QUANTITY, 1 CHOICE, 1 MATH_EXPR | 0 |
| 4E | 41 QUANTITY, 12 CHOICE, 1 EXACT_TEXT | 20 QUANTITY, 9 EXACT_TEXT, 1 CHOICE | 0 |
| 3E | 26 QUANTITY, 16 CHOICE, 9 MATH_EXPR, 3 EXACT_TEXT | 19 EXACT_TEXT, 9 QUANTITY, 2 MATH_EXPR | 0 |
| 2NDE | 42 QUANTITY, 10 CHOICE, 1 EXACT_TEXT, 1 MATH_EXPR | 18 QUANTITY, 12 EXACT_TEXT | 10 |
| 1RE | 40 QUANTITY, 14 CHOICE | 15 QUANTITY, 15 EXACT_TEXT | 31 |
| TLE | 39 QUANTITY, 13 CHOICE, 2 MATH_EXPR | 25 EXACT_TEXT, 5 QUANTITY | 33 |

## Conventions physiques

- **Valeurs numériques.** Toutes les réponses numériques sont calculées en Python dans les scripts de construction,
  jamais recopiées à la main. Les étapes affichent les valeurs intermédiaires arrondies.
- **Chiffres significatifs.** Au collège, les données sont choisies pour donner des résultats simples, sans consigne
  de chiffres significatifs. Au lycée, l'énoncé précise « avec 2 (ou 3) chiffres significatifs » et la réponse porte
  `significant_figures`. Le script refuse une valeur située à moins de 2 % d'une demi-unité du dernier chiffre
  (arrondi ambigu) : les données ont été ajustées dans ce cas.
- **Unités.** Unités SI ou usuelles (mL, km/h, mg, kHz…) avec conversion explicite dans les étapes. g = 9,81 N/kg
  (ou m/s²) au lycée, g = 9,8 N/kg au collège (Lune 1,6 N/kg et Jupiter 24,8 N/kg en 3e).
- **pH.** Le pH est donné avec une ou deux décimales, selon la consigne de l'énoncé. C'est la convention usuelle,
  mais elle ne correspond pas à des chiffres significatifs. La réponse est une QUANTITY sans unité,
  avec `tolerance_relative` (0,002 à 0,01) et sans `significant_figures`.
- **Valeurs réalistes.** Titrages (VE entre 8 et 18 mL), vitesses de lancer, demi-vies réelles (¹³¹I : 8,02 j ;
  ⁹⁹ᵐTc : 6,00 h ; ¹⁴C : 5 730 ans ; ⁶⁰Co : 5,27 ans ; ²²²Rn : 3,8 j), pH de solutions courantes.

## Contrôles effectués

1. **`python -m pedagogy.drafts check`** : PASS sur l'ensemble des brouillons, avec 0 anomalie bloquante,
   0 erreur de chargement et 0 avertissement.
2. **Validation ciblée** (validateurs `exercise` / `quiz` sur les fichiers `PC_*.json`) : 0 anomalie hors
   `NOTION_NOT_APPROVED`.
3. **Doublons** (`pedagogy.qa.duplicates`) en 1re et Tle : aucun doublon exact et aucun `TOO_SIMILAR`. Un
   exercice de 1re (titrage du diiode) a été réécrit avec d'autres données pour lever un `EXERCISE_TOO_SIMILAR`.
4. **Erreurs fréquentes.** Chaque `common_errors` est une valeur réellement fausse, hors tolérance :
   le validateur `COMMON_ERROR_ACTUALLY_CORRECT` passe.

## Limites du vérificateur et contournements

- **Unités `Bq`, `an(s)`, `jour(s)`** : désormais reconnues par `pedagogy.checks.physics`. Les 5 exercices
  de décroissance radioactive de Tle (a02, c01, c05, x02, x03) déclarent maintenant l'unité attendue
  (`expected_answer.unit` = « Bq » ou « an ») ; l'énoncé ne demande plus « le nombre seul ». Les durées en jours restent
  demandées en nombre seul (MATH_EXPR) ou converties en s ou en h.
- **Lettres capitales isolées après « en »** : « sa vitesse en A » est lu comme « en ampères ». Les points de
  trajectoire s'appellent donc « point 1 » et « point 2 » (1re, énergie mécanique, c02).
- **Réponse dans la question** (`ANSWER_IN_QUESTION`) : un distracteur ou une réponse comme « double » ne doit pas
  figurer dans l'énoncé. La question a été reformulée (« deux fois plus grande » → « est multipliée par 2 »).
- **Quiz numériques en EXACT_TEXT** : quand le choix correct ne s'écrit pas comme une grandeur analysable (pH,
  pourcentages, « 5 jours », « 17 190 ans »), la question est en EXACT_TEXT. L'équivalence est alors textuelle.
  La justesse du calcul a été vérifiée dans le script, pas par le vérificateur.
- **pH sans chiffres significatifs** : le vérificateur ne sait pas imposer un nombre de décimales. Une réponse
  « 3,6 » au lieu de « 3,60 » peut être refusée avec une tolérance de 0,002. **À décider en revue** : quel niveau
  d'exigence sur les décimales du pH ?
- **Items conceptuels (CHOICE)** : le vérificateur contrôle la structure (un seul index correct, présence dans la
  solution), pas le contenu physique. Ces items ont été relus à la main.

## Points de revue prioritaires

- **5e–3e** : le vocabulaire doit être adapté au cycle 4 (pas de « quantité de matière »). Quelques items de 4e et
  de 3e utilisent des puissances de 10 : vérifier qu'elles sont acceptables à ce niveau. Vérifier aussi les
  réponses EXACT_TEXT à variantes (« gaz / gazeux / état gazeux »…).
- **2de** : notation scientifique et chiffres significatifs, constante d'Avogadro 6,02 × 10^23 mol⁻¹, vecteur
  vitesse moyenne traité en valeur.
- **1re, titrage** : équations de réaction équilibrées (Fe²⁺/MnO4⁻, I2/S2O3²⁻, H2O2/MnO4⁻) et relation à
  l'équivalence n(A)/a = n(B)/b. Le repérage de l'équivalence est colorimétrique. Le suivi pH-métrique ou
  conductimétrique relève de la Tle.
- **1re, énergie mécanique** : origine des altitudes précisée dans chaque énoncé ; les frottements ne sont traités
  qu'en bilan (énergie dissipée). Le théorème de l'énergie cinétique et le travail n'y sont pas utilisés.
- **1re, ondes** : la conservation de la fréquence au changement de milieu est présentée comme un fait.
- **Tle, pH** : on n'utilise que l'acide chlorhydrique comme acide fort ([H3O+] = C). Aucun item ne fait appel
  au KA ni aux acides faibles (autres notions).
- **Tle, équations horaires** : axe Oz vers le haut, origine au point de lancement sauf mention contraire, et
  référentiel terrestre supposé galiléen. La portée est calculée sur sol horizontal. L'exercice du basketteur
  (x01) suppose une trajectoire non gênée.
- **Tle, décroissance** : exposants non entiers traités par 2^(−t/t½). Datation au ¹⁴C simplifiée (activité
  initiale supposée égale à celle d'un organisme actuel). Pour l'activité de 1,0 µg d'¹³¹I, on utilise λ = 1,00 × 10^-6 s⁻¹
  arrondi (valeur exacte 1,0003 × 10^-6 s⁻¹).
- **Toutes classes** : les formulations des `common_errors` décrivent des raisonnements plausibles, à confirmer
  par un enseignant. Les `estimated_time_min` sont indicatifs (3 / 4 / 6 / 10–12 min selon la bande).
