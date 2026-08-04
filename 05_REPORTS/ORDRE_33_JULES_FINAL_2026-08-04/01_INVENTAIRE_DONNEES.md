# INVENTAIRE DES DONNÉES PÉDAGOGIQUES

## Curriculums
- Source canonique : `app/api/v1/parcours/curriculum_dataset.py` (Dictionnaire `CURRICULA_DATA`)
- Niveaux présents : primaire, 6e, 5e, 4e, 3e, 2de, 1re, tle (pour "maths")

## Exercices, Solutions, Remédiations, Prérequis
- Source canonique : `app/api/v1/mikamike/catalogue.py` (Dictionnaire `EXERCICES`)
- Exercices réellement présents : Seulement 4 exercices.
  - "exo-maths-algebre-1" (5e, equations_1er_degre)
  - "exo-maths-calcul-litteral-1" (5e, calcul_litteral)
  - "exo-maths-priorites-1" (6e, priorites_operatoires)
  - "exo-maths-fractions-1" (6e, fractions)
## Graphes de compétences
- Source canonique : `app/api/v1/mikamike/learning_engine.py` (Dictionnaire `GRAPHE_MATHS_COLLEGE`) et `app/api/v1/parcours/curriculum_dataset.py` (Via les `prerequisite_ids`).

## États de maîtrise
- Source canonique : `app/api/v1/mikamike/learning_engine.py` (`EtatMaitrise`) et la persistance via `crud.py` dans la base de données.

## Éléments manquants

- Niveau primaire | Notion: maths_prim_01 (Addition et soustraction) : 4 exercices manquants.
- Niveau primaire | Notion: maths_prim_02 (Tables de multiplication) : 4 exercices manquants.
- Niveau primaire | Notion: maths_prim_03 (Division euclidienne) : 4 exercices manquants.
- Niveau primaire | Notion: maths_prim_04 (Fractions simples) : 4 exercices manquants.
- Niveau primaire | Notion: maths_prim_05 (Périmètre et aires de base) : 4 exercices manquants.
- Niveau 6e | Notion: maths_6e_01 (Nombres décimaux) : 4 exercices manquants.
- Niveau 6e | Notion: maths_6e_02 (Priorités opératoires) : 4 exercices manquants.
- Niveau 6e | Notion: maths_6e_03 (Fractions et égalités) : 4 exercices manquants.
- Niveau 6e | Notion: maths_6e_04 (Angles et mesure) : 4 exercices manquants.
- Niveau 6e | Notion: maths_6e_05 (Périmètres et Aires) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_01 (Nombres relatifs et opérations) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_02 (Priorités opératoires complètes) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_03 (Calcul littéral et réductions) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_04 (Équations du 1er degré) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_05 (Proportionnalité et pourcentages) : 4 exercices manquants.
- Niveau 5e | Notion: maths_5e_06 (Triangles et hauteurs) : 4 exercices manquants.
- Niveau 4e | Notion: maths_4e_01 (Calcul littéral et développements) : 4 exercices manquants.
- Niveau 4e | Notion: maths_4e_02 (Équations du 1er degré avancées) : 4 exercices manquants.
- Niveau 4e | Notion: maths_4e_03 (Théorème de Pythagore direct) : 4 exercices manquants.
- Niveau 4e | Notion: maths_4e_04 (Théorème de Thalès direct) : 4 exercices manquants.
- Niveau 4e | Notion: maths_4e_05 (Puissances de 10 et notation scientifique) : 4 exercices manquants.
- Niveau 3e | Notion: maths_3e_01 (Réciproque du théorème de Pythagore) : 4 exercices manquants.
- Niveau 3e | Notion: maths_3e_02 (Réciproque du théorème de Thalès) : 4 exercices manquants.
- Niveau 3e | Notion: maths_3e_03 (Fonctions affines et linéaires) : 4 exercices manquants.
- Niveau 3e | Notion: maths_3e_04 (Trigonométrie dans le triangle rectangle) : 4 exercices manquants.
- Niveau 3e | Notion: maths_3e_05 (Probabilités et arbre de choix) : 4 exercices manquants.
- Niveau 2de | Notion: maths_2de_01 (Généralités sur les fonctions) : 4 exercices manquants.
- Niveau 2de | Notion: maths_2de_02 (Équations et inéquations du 2nd degré) : 4 exercices manquants.
- Niveau 2de | Notion: maths_2de_03 (Vecteurs et colinéarité) : 4 exercices manquants.
- Niveau 2de | Notion: maths_2de_04 (Équations de droites) : 4 exercices manquants.
- Niveau 2de | Notion: maths_2de_05 (Statistiques et dispersion) : 4 exercices manquants.
- Niveau 1re | Notion: maths_1re_01 (Second degré et discriminant) : 4 exercices manquants.
- Niveau 1re | Notion: maths_1re_02 (Dérivation et nombre dérivé) : 4 exercices manquants.
- Niveau 1re | Notion: maths_1re_03 (Suites arithmétiques et géométriques) : 4 exercices manquants.
- Niveau 1re | Notion: maths_1re_04 (Produit scalaire) : 4 exercices manquants.
- Niveau 1re | Notion: maths_1re_05 (Probabilités conditionnelles) : 4 exercices manquants.
- Niveau tle | Notion: maths_tle_01 (Limites et continuité) : 4 exercices manquants.
- Niveau tle | Notion: maths_tle_02 (Fonction exponentielle) : 4 exercices manquants.
- Niveau tle | Notion: maths_tle_03 (Fonction logarithme népérien) : 4 exercices manquants.
- Niveau tle | Notion: maths_tle_04 (Intégration et primitives) : 4 exercices manquants.
- Niveau tle | Notion: maths_tle_05 (Géométrie dans l'espace) : 4 exercices manquants.
