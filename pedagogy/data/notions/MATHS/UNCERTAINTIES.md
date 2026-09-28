# MATHS — incertitudes du registre candidat (agent A)

Statut global : **toutes les notions MATHS sont des candidats** (`proof_status=UNPROVEN`,
`source_type=CANDIDATE_UNVERIFIED`, `official_wording=null`, `review_status=NOT_REVIEWED`,
`publication_status=DRAFT`). Elles ont été reconstituées de mémoire (connaissance générale des
programmes). À l'origine, BO et Éduscol étaient inaccessibles dans l'environnement de génération. La référence du nouveau programme de mathématiques du cycle 3 a depuis été vérifiée sur le site officiel du ministère ; les PDF ne sont toutefois pas encore déposés localement dans le dépôt, et aucune notion n'est encore prouvée verbatim.
Aucun libellé n'est donné comme officiel. Les titres sont des noms de notions courants, pas des
citations.

## 1. Versions de programme (à confirmer en priorité)

| Fichier | Source attendue | Doute |
|---|---|---|
| 6E.json | SRC-C3-MATHS-NOUVEAU | **Source confirmée** : programme de mathématiques du cycle 3, BO n°16 du 17 avril 2025, NOR MENE2504620A, applicable en 6e à la rentrée 2025-2026. Les 48 notions restent UNPROVEN tant que leur placement et leur libellé ne sont pas vérifiés verbatim dans le PDF local. |
| 5E/4E/3E.json | SRC-C4-2020 | Version consolidée 2020 du cycle 4 supposée. Il faut vérifier qu'aucune version plus récente (nouveaux programmes collège annoncés 2024-2026) ne s'applique en 2025-2026. |
| 2NDE.json | SRC-2NDE-2019 | Programme 2019 supposé. Il faut vérifier les ajustements éventuels (automatismes, arithmétique, vocabulaire ensembliste). |
| 1RE_SPECIALITE.json | SRC-1RE-2019 | Programme 2019 supposé. |
| TLE_*.json | SRC-TLE-2019 | Programmes 2019 supposés (spécialité, maths expertes et maths complémentaires), applicables depuis 2020. |
| (non créé) 1RE_MATHS_SPECIFIQUES_1RE.json | SRC-1RE-MATHS-TC | **Fichier volontairement non créé.** L'enseignement de mathématiques du tronc commun de 1re (depuis 2023, intégré ou non à l'enseignement scientifique) n'est pas connu avec assez de précision : existence, contenu et calendrier restent à confirmer. |

## 2. Placement par niveau (le cycle 4 est un programme de cycle)

Le cycle 4 fixe des attendus **de fin de cycle**. La répartition entre 5e, 4e et 3e ci-dessous suit les repères annuels de progression tels qu'ils ont été retenus. Il faut la confirmer avec le document « repères annuels de progression » (Éduscol).
- **6E « Longueur du cercle »** et **5E « Aire du disque »** : la formule de l'aire du disque est peut-être déjà au cycle 3 (6e).
- **6E « Pourcentages »** : on suppose des pourcentages simples au cycle 3.
- **4E « Théorème de Thalès »** (triangles emboîtés) et **3E « Réciproque du théorème de Thalès »** : la répartition 4e/3e est à confirmer, en particulier pour la configuration « papillon ».
- **Cosinus en 4e** : absent volontairement. Toute la trigonométrie est placée en 3E (ancre). À vérifier.
- **4E « Médiane et étendue »**, **4E « Calcul de probabilités »**, **4E « Pourcentages d'évolution »** : le niveau est à confirmer.
- **3E « Racine carrée »** : cette notion est peut-être introduite dès la 4e avec Pythagore.
- **3E « Rotations et homothéties »** : la rotation est peut-être en 4e.
- **2NDE « Équations et inéquations du premier degré »** : on suppose que les inéquations ne sont plus au programme du cycle 4.
- **2NDE « Projeté orthogonal »** : à confirmer en seconde.
- **TLE « Calcul intégral »** : on y a placé l'intégration par parties, qui est à confirmer au programme de spécialité.
- **TLE spécialité « Algorithmes de seuil et de dichotomie »** : l'algorithmique est transversale dans les programmes de lycée. Un domaine AP séparé est un choix de modélisation.

## 3. Noms et codes de domaines

- Collège : NC, OGD, GM, EG, AP (intitulés internes / hérités). **En 6e**, le programme 2025 est désormais la référence à vérifier notion par notion. Son sommaire officiel comporte notamment « Nombres, calcul et résolution de problèmes », « Grandeurs et mesures », « Espace et géométrie », « Organisation et gestion de données et probabilités », « La proportionnalité » et « Initiation à la pensée informatique ». Les codes actuels restent des choix de modélisation jusqu'à la revue détaillée.
- Seconde : NC, GEO, FON, SP, AP. On suppose aussi une rubrique officielle « Vocabulaire ensembliste et logique », qui n'est pas modélisée.
- 1re spécialité : **les suites sont placées sous AN (Analyse)** parce que le contrat d'ancres l'impose (`MATHS.1RE.AN.suites-numeriques`). L'organisation officielle supposée les range dans « Algèbre ». De même, en Tle, « Raisonnement par récurrence » est en AN (ancre). Le programme de terminale le rattache peut-être à « Algèbre et géométrie » ou aux suites.
- 1re/Tle : ALG (second degré ; combinatoire en Tle), GEO, PROBA, AP. Il faut vérifier les intitulés exacts des parties du programme.
- Maths expertes : CPLX, ARITH, GRAPH. Maths complémentaires : MCAN, MCPROB. Ces codes sont **internes** : ils évitent les collisions d'identifiants avec la spécialité (l'identifiant ne dépend pas du `course`).

## 4. Contenus des options de terminale

- **Maths expertes** : nombres complexes (algébrique, équations polynomiales, forme exponentielle, géométrie), arithmétique (congruences, PGCD, Bézout, Gauss, Fermat), graphes et matrices (chaînes de Markov). Il faut vérifier que la répartition complexes « algèbre » / « géométrie » correspond au programme. Il faut aussi vérifier si le petit théorème de Fermat y figure explicitement.
- **Maths complémentaires** : les intitulés sont des regroupements par thème (modèles discrets, exp/ln, dérivation, intégration, équations différentielles, lois binomiale et géométrique, lois à densité, statistiques à deux variables). Le programme officiel est organisé par thèmes d'étude ou problèmes et non par notions. Il faut confirmer l'appariement. La présence de la loi géométrique, de la loi exponentielle et des lois à densité est à vérifier.
- Les prérequis des maths complémentaires pointent vers la **1re spécialité**. C'est cohérent pour des élèves qui ont abandonné la spécialité en Tle, mais c'est à confirmer.

## 5. Contenus pédagogiques non officiels

Les champs `learning_objectives`, `expected_skills`, `common_mistakes`, `difficulty`, `competency_ids` et `prerequisites` sont des **propositions didactiques** (connaissance générale). Ils ne sont pas tirés des textes. Ils devront être relus par un enseignant (review_status reste NOT_REVIEWED).

## 6. Ce qu'il faut vérifier, et où

1. Déposer les PDF officiels (BO), en priorité le programme de mathématiques cycle 3 de 2025 déjà identifié (SRC-C3-MATHS-NOUVEAU), puis SRC-C3-2020 pour Sciences et technologie, SRC-C4-2020, SRC-2NDE-2019, SRC-1RE-2019, SRC-1RE-MATHS-TC et SRC-TLE-2019. Enregistrer ensuite le sha256.
2. Pour chaque notion, rechercher un libellé verbatim dans le PDF (`pedagogy.sources.verify_notion_against_source`). Seulement alors, renseigner `official_wording`, `source_page_or_section` et `source_sha256`, et passer en PROVEN_OFFICIAL.
3. Confirmer la répartition annuelle du cycle 4 avec les repères annuels de progression (Éduscol, mathématiques cycle 4).
4. Revoir les 48 candidats de 6E.json contre le programme 2025 désormais confirmé : domaines, placement, titres et objectifs. Ne promouvoir une notion qu'après vérification verbatim dans le PDF local.
5. Décider s'il faut créer 1RE_MATHS_SPECIFIQUES_1RE.json après lecture de SRC-1RE-MATHS-TC.
