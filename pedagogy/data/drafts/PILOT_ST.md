# Pilote brouillons SCIENCES ET TECHNOLOGIE — CP à 6e

Statut : **brouillons** (`generation_origin = MODEL_ASSISTED_DRAFT`, `qa_status = NOT_CHECKED`,
`publication_status = READY_FOR_REVIEW`). Rien n'est servi aux élèves avant la revue humaine de
la notion ET de chaque item (`python -m pedagogy.drafts approve …`).

Sources de calibrage (toutes les notions retenues sont `PROVEN_OFFICIAL`, libellé officiel complet) :

- CP, CE1, CE2 : programme de sciences et technologie du cycle 2 — BO 2026, annexe 1 (`SRC-C2-ST-2026`, NOR MENE2611650A).
- CM1 : programme de sciences et technologie du cycle 3 — BO 2026, annexe 2 (`SRC-C3-ST-2026`, NOR MENE2611650A).
- CM2, 6e : programme du cycle 3 — BO n°31 du 30 juillet 2020, version consolidée (`SRC-C3-2020`), appliqué au CM2 et en 6e en 2026-2027.

## Fichiers

| Fichier | Contenu |
|---|---|
| `exercises/ST_CP.json`, `quizzes/ST_CP.json` | 54 exercices + 30 questions |
| `exercises/ST_CE1.json`, `quizzes/ST_CE1.json` | 54 exercices + 30 questions |
| `exercises/ST_CE2.json`, `quizzes/ST_CE2.json` | 54 exercices + 30 questions |
| `exercises/ST_CM1.json`, `quizzes/ST_CM1.json` | 54 exercices + 30 questions |
| `exercises/ST_CM2.json`, `quizzes/ST_CM2.json` | 54 exercices + 30 questions |
| `exercises/ST_6E.json`, `quizzes/ST_6E.json` | 54 exercices + 30 questions |

Total : **324 exercices + 180 questions de quiz = 504 items**, soit 18 notions × (5 DISCOVERY + 5 APPLICATION +
5 CONSOLIDATION + 3 ADVANCED + 10 quiz). Chaque série de 10 quiz va du plus simple (DISCOVERY) à une
question ADVANCED finale (répartition par niveau d'environ 3-4 / 3 / 2-3 / 1).

Identifiants : `EX.ST.<NIVEAU>.<slug>.<d|a|c|x><nn>` et `QZ.ST.<NIVEAU>.<slug>.q<nn>`.

Validation : `.venv/bin/python -m pedagogy.drafts check` → **PASS**, 0 erreur de chargement, 0 bloquant,
0 avertissement sur les fichiers ST.

## Notions retenues (3 par niveau, domaines variés)

### CP

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `etats-eau` | Matière | Reconnaitre et identifier les états solides et liquides de l'eau. |
| `vivant` | Vivant | Caractériser et justifier à l'aide de critères simples ce qui est vivant, non vivant ou élaboré par des êtres vivants. |
| `objets-besoins` | Objets techniques | Identifier des activités de la vie quotidienne faisant appel à des objets techniques répondant à un besoin. |

### CE1

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `fusion-solidification` | Matière | Nommer le changement d'état (solidification et fusion). |
| `regime-alimentaire` | Vivant | Identifier le régime alimentaire d'animaux. |
| `energie-electrique` | Objets techniques | Différencier les objets selon qu'ils utilisent ou non une source d'énergie électrique. Identifier le cas échéant l'intérêt de l'utilisation de l'énergie électrique. |

### CE2

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `solide-liquide` | Matière | Différencier les états physiques solide (forme et volume propre) et liquide (volume propre, absence de forme propre et surface horizontale). |
| `chaine-alimentaire` | Vivant | Élaborer une courte chaine alimentaire. |
| `saisie-traitement` | Objets techniques / numérique | Identifier les dispositifs permettant la saisie, le traitement et la restitution d'informations (clavier, processeur, écran, etc.). |

### CM1

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `separer-melanges` | Matière | Séparer les constituants d'un mélange de solides ou d'un mélange solide-liquide par tamisage, décantation, filtration. |
| `fecondation` | Vivant | Mettre en relation le type de fécondation (interne ou externe) avec le mode de reproduction ovipare et vivipare des animaux. |
| `phases-lune` | Terre / ciel (rangée en MAT dans le référentiel) | Observer, schématiser et nommer les phases de la Lune. |

### CM2

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `ressources-energie` | Matière, énergie | Ressources renouvelables et non renouvelables. |
| `apports-alimentaires` | Vivant | Apports alimentaires : qualité et quantité. |
| `mouvements-terre` | Planète Terre | Les mouvements de la Terre sur elle-même et autour du Soleil. |

### 6e

| Slug | Domaine | Libellé officiel |
|---|---|---|
| `masse` | Matière | Tout objet matériel possède une masse qui lui est propre et qui peut être mesurée. |
| `besoins-vegetaux` | Vivant | Besoins des organismes chlorophylliens : lumière, eau, sels minéraux, dioxyde de carbone. |
| `systeme-solaire` | Planète Terre | Position de la Terre dans le système solaire. |

## Choix de format des réponses

Uniquement des réponses vérifiables automatiquement et indiscutables :
`CHOICE` (QCM, 3 choix), `MATCHING` (relier), `ORDERING` (ranger), `BOOLEAN` (vrai/faux),
`EXACT_TEXT` (un mot ou un groupe nominal court, variantes avec et sans accents acceptées),
`QUANTITY` (valeur + unité : L, h, g, kg, s) et `MATH_EXPR` pour un simple dénombrement.
Aucune réponse rédigée ; les expériences évoquées sont sans danger (pesées, arrosage de plantes,
maquette lampe/globe, filtration) et ne demandent jamais de regarder le Soleil.

## Points à vérifier par l'enseignant relecteur

1. **Position de la bonne réponse** : dans tous les QCM et quiz ST, la bonne réponse est au rang 0.
   Le mélange des choix doit être assuré à l'affichage ; sinon, permuter avant publication.
2. **Programmes différents selon le niveau** : CM1 est calibré sur le cycle 3 2026, CM2/6e sur le cycle 3 2020
   (transition 2026-2027). Vérifier qu'aucun item CM2/6e ne dépasse ou ne contredit le nouveau programme lorsque
   celui-ci s'appliquera à ces niveaux.
3. **Formulations simplifiées à valider** :
   - CM2 `ressources-energie` : bois « renouvelable si l'on replante » ; uranium « non renouvelable, non fossile ».
   - CM2 `apports-alimentaires` : groupes d'aliments (pomme de terre en féculents, beurre en matières grasses,
     œuf avec viandes/poissons), repère « au moins 5 fruits et légumes par jour », rôles simplifiés (calcium → os et dents).
   - CM2 `mouvements-terre` : saisons expliquées par l'inclinaison de l'axe (et non la distance) ; Soleil « au sud » à midi en France.
   - 6e `masse` : distinction masse / poids évoquée seulement dans un item ADVANCED (astronaute sur la Lune) ;
     « 1 L d'eau ≈ 1 kg » donné dans l'énoncé.
   - 6e `besoins-vegetaux` : expérience de Van Helmont (valeurs arrondies : ≈ 74 kg gagnés, ≈ 60 g de terre perdus) ;
     sels minéraux et eau par les racines, dioxyde de carbone et lumière par les feuilles ; champignon non chlorophyllien.
   - 6e `systeme-solaire` : 8 planètes (Pluton planète naine depuis 2006) ; ≈ 150 millions de km ; lumière ≈ 300 000 km/s
     → 500 s ; Vénus > 400 °C.
4. **Vocabulaire et lisibilité** : adapter si besoin la longueur des énoncés pour CP/CE1 (lecture par l'adulte ou audio).
5. **Unités** : les réponses `QUANTITY` acceptent les conversions (ex. 1,5 kg pour 1 500 g) ; vérifier que c'est souhaité
   pour les items où l'énoncé impose « Réponds en g ».
6. **Erreurs fréquentes et remédiations** : rédigées a priori ; à confronter aux erreurs réellement observées en classe.
