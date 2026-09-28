# Pilote brouillons SVT (5e → Tle) et Enseignement scientifique (1re, Tle)

Statut : **BROUILLONS EN ATTENTE DE REVUE HUMAINE.** Tous les items sont `MODEL_ASSISTED_DRAFT`,
`qa_status = NOT_CHECKED` et `publication_status = READY_FOR_REVIEW`. Aucun n'est dans la banque servie.
Les 24 notions sources sont `PROVEN_OFFICIAL` mais encore `NOT_REVIEWED`. L'anomalie `NOTION_NOT_APPROVED`
est donc attendue jusqu'à la revue.

Selon la spécification, **la SVT ne peut jamais être déclarée servable sur le seul moteur automatique.** Ces
brouillons n'utilisent donc que des clés de correction indiscutables :

- QCM à une seule bonne réponse (`CHOICE`) ;
- vrai/faux (`BOOLEAN`) ;
- remise en ordre (`ORDERING`) et association (`MATCHING`) ;
- réponse courte à liste fermée de formes acceptées (`EXACT_TEXT`) ;
- valeur numérique (`MATH_EXPR`) ou grandeur avec unité (`QUANTITY`) lue ou calculée sur un document.

**Il n'y a aucun item `RUBRIC` et aucune question ouverte.** Les vrai/faux de type `TRUE_FALSE_ARGUED` sont
corrigés automatiquement sur le booléen seul. Le critère de justification qui les accompagne sert à la revue
et au retour pédagogique, pas à la note.

## Fichiers

| Fichier | Exercices | Quiz |
|---|---|---|
| `exercises/SVT_5E.json`, `quizzes/SVT_5E.json` | 54 | 30 |
| `exercises/SVT_4E.json`, `quizzes/SVT_4E.json` | 54 | 30 |
| `exercises/SVT_3E.json`, `quizzes/SVT_3E.json` | 54 | 30 |
| `exercises/SVT_2NDE.json`, `quizzes/SVT_2NDE.json` | 54 | 30 |
| `exercises/SVT_1RE.json`, `quizzes/SVT_1RE.json` | 54 | 30 |
| `exercises/SVT_TLE.json`, `quizzes/SVT_TLE.json` | 54 | 30 |
| `exercises/ES_1RE.json`, `quizzes/ES_1RE.json` | 54 | 30 |
| `exercises/ES_TLE.json`, `quizzes/ES_TLE.json` | 54 | 30 |

Il y a **672 items** en tout : 432 exercices et 240 questions de quiz. Chaque notion compte :

- 5 exercices DISCOVERY, 5 APPLICATION, 5 CONSOLIDATION et 3 ADVANCED ;
- 10 questions de quiz : 3 DISCOVERY, 3 APPLICATION, 3 CONSOLIDATION et 1 ADVANCED.

Chaque exercice comporte :

- une solution et une résolution pas à pas ;
- 1 à 3 indices ;
- au moins une erreur fréquente, avec la réponse erronée et son diagnostic ;
- une remédiation ;
- les compétences évaluées ;
- une durée estimée.

Chaque question de quiz a une explication et une justification pour chaque distracteur.

Les identifiants suivent ces formes :

- `EX.SVT.<NIVEAU>.<slug>.<d|a|c|x><nn>` et `QZ.SVT.<NIVEAU>.<slug>.q<nn>` ;
- `EX.ES.<NIVEAU>.<slug>.…` et `QZ.ES.<NIVEAU>.<slug>.…`.

## Notions retenues

| Niveau | Slug | notion_id (préfixe) | Libellé officiel (abrégé) | Source |
|---|---|---|---|---|
| SVT 5E | `besoins-animaux` | `SVT.5E.VIV.relier-les-besoins-en-nutriments-et-dioxygene…` | Besoins en nutriments et dioxygène des cellules animales, rôle des systèmes de transport | SRC-C4-2020 |
| SVT 5E | `besoins-plante` | `SVT.5E.VIV.relier-les-besoins-des-cellules-dune-plante…` | Besoins des cellules d'une plante chlorophyllienne, lieux de production et de stockage, transport | SRC-C4-2020 |
| SVT 5E | `effort` | `SVT.5E.CORPS.rythmes-cardiaque-et-respiratoire-et-effort-physique` | Rythmes cardiaque et respiratoire, et effort physique | SRC-C4-2020 |
| SVT 4E | `tectonique` | `SVT.4E.TER.la-terre-dans-le-systeme-solaire…` | Globe terrestre, dynamique interne, tectonique des plaques, séismes, éruptions | SRC-C4-2020 |
| SVT 4E | `classification` | `SVT.4E.VIV.caracteres-partages-et-classification` | Caractères partagés et classification | SRC-C4-2020 |
| SVT 4E | `nerveux` | `SVT.4E.CORPS.message-nerveux-centres-nerveux-nerfs-cellules-nerveuses` | Message nerveux, centres nerveux, nerfs, cellules nerveuses | SRC-C4-2020 |
| SVT 3E | `genetique` | `SVT.3E.VIV.adn-mutations-brassage-gene-meiose-et-fecondation` | ADN, mutations, brassage, gène, méiose et fécondation | SRC-C4-2020 |
| SVT 3E | `digestion` | `SVT.3E.CORPS.systeme-digestif-digestion-absorption…` | Système digestif, digestion, absorption ; aliments et nutriments | SRC-C4-2020 |
| SVT 3E | `immunite` | `SVT.3E.CORPS.reactions-immunitaires` | Réactions immunitaires | SRC-C4-2020 |
| SVT 2NDE | `derive-genetique` | `SVT.2NDE.TVOV.la-derive-genetique…` | Modification aléatoire des fréquences alléliques, plus rapide si l'effectif est faible | SRC-2NDE-SVT-2019 |
| SVT 2NDE | `erosion` | `SVT.2NDE.ECP.leau-est-le-principal-facteur…` | L'eau, principal facteur d'altération et d'érosion des roches | SRC-2NDE-SVT-2019 |
| SVT 2NDE | `pathogenes` | `SVT.2NDE.CHS.les-agents-pathogenes-virus…` | Agents pathogènes (virus, bactéries, eucaryotes), hôte, symptômes | SRC-2NDE-SVT-2019 |
| SVT 1RE | `code-genetique` | `SVT.1RE.TVOV.le-code-genetique…` | Code génétique universel, traduction de l'ARNm en protéines | SRC-1RE-SVT-2019 |
| SVT 1RE | `dorsales` | `SVT.1RE.TVOV.la-divergence-des-plaques…` | Divergence aux dorsales, nouvelle lithosphère, décompression du manteau | SRC-1RE-SVT-2019 |
| SVT 1RE | `maladie-recessive` | `SVT.1RE.CHS.dans-le-cas-dune-maladie-monogenique…` | Maladie autosomique récessive : seuls les homozygotes mutés sont atteints | SRC-1RE-SVT-2019 |
| SVT TLE | `brassage` | `SVT.TLE.TVOV.pour-deux-paires-dalleles…` | Deux paires d'allèles : quatre combinaisons, équiprobables ou non (gènes liés) | SRC-TLE-SVT-2019 |
| SVT TLE | `photosynthese` | `SVT.TLE.EPC.captee-par-les-pigments-chlorophylliens…` | Photosynthèse (photolyse de l'eau, réduction du CO2) et devenir des sucres | SRC-TLE-SVT-2019 |
| SVT TLE | `glycemie` | `SVT.TLE.CHS.la-glycemie-est…` | Glycémie proche de 1 g/L, régulée par deux hormones pancréatiques | SRC-TLE-SVT-2019 |
| ES 1RE | `demi-vie` | `ES.1RE.MATIERE.la-demi-vie…` | Demi-vie d'un noyau radioactif, caractéristique du noyau | SRC-1RE-ES-2023 |
| ES 1RE | `albedo` | `ES.1RE.SOLEIL.une-fraction-de-cette-puissance…` | Fraction diffusée (albédo), le reste absorbé par atmosphère, continents, océans | SRC-1RE-ES-2023 |
| ES 1RE | `audition` | `ES.1RE.SON.au-dela-de-80-db…` | Au-delà de 80 dB, un son peut devenir nocif selon intensité et durée | SRC-1RE-ES-2023 |
| ES TLE | `effet-de-serre` | `ES.TLE.CLIMAT.lorsque-la-concentration-des-ges…` | Hausse des GES, absorption infrarouge accrue, perturbation de l'équilibre radiatif | SRC-TLE-ES-2023 |
| ES TLE | `cmr` | `ES.TLE.VIVANT.si-on-suppose-que-la-proportion…` | Capture-marquage-recapture : quatrième proportionnelle | SRC-TLE-ES-2023 |
| ES TLE | `hardy-weinberg` | `ES.TLE.VIVANT.le-modele-mathematique-de-hardy…` | Modèle probabiliste de transmission des allèles | SRC-TLE-ES-2023 |

Le préfixe du `notion_id` suffit à retrouver la notion : il est unique dans le registre. Les notions au libellé
tronqué ou aplati par l'extraction PDF ont été écartées. Les ADVANCED d'ES Tle s'appuient sur les notions voisines
du même chapitre :

- intervalle de confiance [f − 1/√n ; f + 1/√n] pour la CMR ;
- rétroactions climatiques et stockage de l'énergie dans l'océan pour l'effet de serre.

Ces notions voisines sont `PROVEN_OFFICIAL` et restent dans le programme.

## Répartition des réponses (toutes auto-corrigeables, aucune RUBRIC)

| Niveau | CHOICE | BOOLEAN | ORDERING | MATCHING | EXACT_TEXT | MATH_EXPR | QUANTITY |
|---|---|---|---|---|---|---|---|
| SVT 5E | 9 | 10 | 6 | 5 | 11 | 6 | 7 |
| SVT 4E | 12 | 10 | 6 | 5 | 12 | 2 | 7 |
| SVT 3E | 12 | 10 | 6 | 4 | 13 | 7 | 2 |
| SVT 2NDE | 12 | 9 | 6 | 4 | 10 | 6 | 7 |
| SVT 1RE | 14 | 11 | 4 | 4 | 9 | 12 | 0 |
| SVT TLE | 12 | 9 | 5 | 5 | 10 | 5 | 8 |
| ES 1RE | 9 | 10 | 4 | 4 | 2 | 15 | 10 |
| ES TLE | 10 | 11 | 3 | 4 | 3 | 19 | 4 |

Toutes les questions de quiz sont en `EXACT_TEXT`, avec une seule réponse de référence. Le vérificateur contrôle
qu'aucun distracteur n'est équivalent à cette référence. Les unités non reconnues par le vérificateur (jours,
années, dB, ppm) sont demandées sous forme de nombre seul (`MATH_EXPR`), avec l'unité précisée dans l'énoncé.

## Validation automatique

`python -m pedagogy.drafts check` → **PASS** : 1 815 exercices, 961 quiz, 0 bloquant, 0 erreur de chargement,
0 avertissement (tous brouillons confondus).

## Points de revue humaine

Généraux :

1. **Exactitude scientifique.** Tout le contenu est un brouillon produit avec assistance d'un modèle. Chaque
   valeur numérique de référence doit être vérifiée par un·e enseignant·e de SVT ou de physique-chimie.
   Les valeurs à vérifier en priorité sont :
   - glycémie ≈ 1 g/L ;
   - demi-vies : carbone 14 ≈ 5 730 ans, iode 131 ≈ 8 jours, technétium 99m ≈ 6 h ;
   - albédo terrestre ≈ 0,30 ;
   - CO2 ≈ 280 ppm avant l'ère industrielle et ≈ 420 ppm dans les années 2020 ;
   - réchauffement ≈ +1 °C ;
   - forçages ≈ 2,2 W/m2 pour le CO2 et 2,7 W/m2 au total ;
   - part de l'énergie stockée par l'océan ≈ 90 %.
2. **Données de documents simplifiées.** Certains « documents » sont des jeux de données arrondis ou
   construits pour le calcul :
   - croisements tests ;
   - activités radioactives ;
   - audiogramme ;
   - bilans radiatifs ;
   - séries de recaptures.

   Ils ne doivent pas être présentés comme des mesures réelles sourcées. Il faut soit ajouter la mention
   « données simplifiées », soit les remplacer par des données publiées.
3. **Formes acceptées (`EXACT_TEXT`).** Il faut vérifier que les listes de formes acceptées couvrent les
   variantes légitimes : accents, articles, pluriels, synonymes. Exemples : « crossing-over / enjambement »,
   « croisement test / test-cross », « désintégration », « quatrième proportionnelle / produit en croix »,
   « dérive génétique ». Une variante correcte absente sera comptée fausse.
4. **Rotation des QCM.** Les choix sont permutés de façon déterministe. Il reste à vérifier que la lettre
   citée dans la solution correspond bien au choix correct après rotation.

Sujets sensibles (traitement factuel, sans conseil médical) :

5. **Santé.** Quatre notions touchent à la santé :
   - glycémie et diabète (SVT Tle) ;
   - maladie autosomique récessive (SVT 1re, ES Tle) ;
   - immunité (SVT 3e) ;
   - pathogènes (SVT 2de).

   Les items restent descriptifs : mécanismes, fréquences, génotypes. Ils ne contiennent aucun seuil
   diagnostique ni aucune recommandation de traitement. L'item d'hyperglycémie provoquée renvoie
   explicitement à un avis médical pour tout diagnostic. Il faut vérifier que le vocabulaire des items sur le
   diabète (types 1 et 2) n'est ni stigmatisant ni culpabilisant.
6. **Audition (ES 1re).** Les items utilisent la règle d'égale énergie : +3 dB divise par deux la durée
   d'exposition acceptable, sur une base de 80 dB pendant 8 h. Il faut confirmer que la règle est présentée
   comme une convention de prévention, et non comme un seuil médical individuel. Les mesures de protection
   citées sont celles du programme : bouchons, éloignement, pauses, volume.
7. **Climat (ES Tle).** Les formulations suivent le consensus du GIEC (AR6). Il faut vérifier que le
   vocabulaire des items de rétroaction ne laisse aucune ambiguïté entre « effet de serre naturel » et
   « renforcement anthropique ».

Points propres à certains niveaux :

8. **SVT Tle, brassage.** Les allèles sont désignés par des phénotypes de drosophile (corps gris/noir, ailes
   longues/vestigiales, yeux rouges/pourpres). La notation A/a, B/b n'est pas utilisée dans les choix de QCM,
   car le vérificateur ignore la casse et confondrait « Ab et aB » avec « AB et ab ».
9. **ES 1re, albédo.** Les albédos de surface (neige 0,85, sable 0,35, forêt 0,15, océan 0,06) sont des
   ordres de grandeur, alors que la littérature donne des plages. L'association est sans ambiguïté, mais un
   relecteur peut préférer des plages.
10. **ES Tle, CMR.** Dans l'item x01, l'intervalle pour l'effectif N = M/p est obtenu en inversant les bornes.
    Ce raisonnement va un peu au-delà du programme et doit être validé ou déplacé.
11. **ES Tle, Hardy-Weinberg.** Le programme dit que les probabilités des génotypes sont constantes « à partir
    de la seconde génération ». Les items parlent seulement de fréquences alléliques constantes et de la
    génération issue de la panmixie. Il faut vérifier la cohérence avec la formulation retenue en classe.
