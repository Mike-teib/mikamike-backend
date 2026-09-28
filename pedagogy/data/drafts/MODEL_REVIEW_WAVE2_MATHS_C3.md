# Pré-relecture modèle — Vague 2 Mathématiques CM1, CM2, 6e

## Portée

Pré-relecture assistée uniquement. **Aucune approbation humaine et aucune publication.**

Fichiers examinés :

- `pedagogy/data/drafts/exercises/MATHS_CM1.json`
- `pedagogy/data/drafts/quizzes/MATHS_CM1.json`
- `pedagogy/data/drafts/exercises/MATHS_CM2.json`
- `pedagogy/data/drafts/quizzes/MATHS_CM2.json`
- `pedagogy/data/drafts/exercises/MATHS_6E.json`
- `pedagogy/data/drafts/quizzes/MATHS_6E.json`

Total : **162 exercices + 90 quiz = 252 items**, sur 9 notions.

## Contrôles généraux

Pour chaque niveau :

- 54 exercices ;
- 30 quiz ;
- 3 notions ;
- aucun énoncé anormalement long détecté (max : CM1 185 caractères, CM2 231, 6e 160) ;
- aucune dérive évidente vers des notions manifestement hors niveau détectée lors de cette passe.

## CM1 — fraction d'une quantité

Le pilote limite volontairement l'opérateur fractionnaire aux fractions unitaires.

Contrôle ciblé :

- aucune utilisation détectée de fractions non unitaires comme opérateur du type « deux tiers de … », « trois quarts de … » ;
- les items standards restent sur `1/2`, `1/3`, `1/4`, etc.

Deux items restent un **prolongement à confirmer humainement** :

- `EX.MATHS.CM1.fraction-quantite.x01` :
  « Un tiers d'un paquet de biscuits, c'est 6 biscuits. Combien y a-t-il de biscuits dans le paquet entier ? »
  → 18 ;
- `QZ.MATHS.CM1.fraction-quantite.q10` :
  « Un tiers de la somme de Jules vaut 5 €. Quelle somme Jules a-t-il en tout ? »
  → 15.

Le raisonnement est correct et utilise seulement trois tiers identiques, mais il s'agit de **reconstituer le tout à partir d'une fraction unitaire**. Le dossier pilote le signalait déjà : à valider ou déplacer selon la progression réellement choisie en CM1.

## CM1 — proportionnalité

Recherche automatique dans les énoncés, questions, solutions et indices :

- aucune occurrence de « produit en croix » ;
- aucune occurrence de « coefficient de proportionnalité » ;
- aucun tableau de proportionnalité imposé.

La stratégie reste de type linéarité multiplicative / raisonnement en langage naturel, conforme au périmètre annoncé par le pilote.

**Pré-revue modèle : aucun blocage détecté.**

## CM2 — problèmes mixtes en plusieurs étapes

Les items contrôlés restent dans une chaîne courte de calculs.

Exemples représentatifs :

- cinéma : deux produits puis addition ;
- pommes/poires : deux produits, addition, puis monnaie rendue ;
- randonnée : doublement, soustraction, addition ;
- pizzas/boissons : deux produits, addition, puis partage ;
- sortie scolaire : produit, addition, partage.

Les exercices avancés restent dans **2 à 4 étapes logiques**, sans méthode algébrique ou technique hors niveau détectée.

**Pré-revue modèle : aucun blocage détecté.**

## 6e — somme des angles d'un triangle

La notion porteuse du pilote est :

`MATHS.6E.EG.connaitre-la-valeur-de-la-somme-des-mesures-des-angles-dun-triangle`.

Plusieurs items utilisent en plus les propriétés de triangles particuliers :

- triangle rectangle : angle droit de 90° ;
- triangle isocèle : angles à la base égaux ;
- triangle équilatéral : trois angles égaux ;
- triangle rectangle isocèle.

Items concernés notamment :

- `EX.MATHS.6E.angles-triangle.a02`
- `EX.MATHS.6E.angles-triangle.c01`
- `EX.MATHS.6E.angles-triangle.c02`
- `EX.MATHS.6E.angles-triangle.c03`
- `EX.MATHS.6E.angles-triangle.x01`
- `EX.MATHS.6E.angles-triangle.x02`
- `QZ.MATHS.6E.angles-triangle.q02`, `q03`, `q04`, `q05`, `q07`.

Les calculs relus sont cohérents avec la somme 180°.

**Point humain obligatoire :** confirmer que les propriétés des triangles particuliers sont déjà acquises/réactivées à ce moment de la progression. Si oui, les items peuvent rester rattachés à la notion porteuse actuelle. Sinon, ajouter la notion voisine à `source_notions` ou déplacer les items.

Aucun rattachement n'est modifié automatiquement pendant cette pré-relecture.

## Verdict de pré-relecture modèle

- aucun blocker modèle détecté sur les 252 items ;
- aucun contenu modifié pendant cette vague ;
- aucune notion ni aucun item approuvé ;
- deux arbitrages pédagogiques restent explicitement humains :
  1. reconstitution du tout à partir d'une fraction unitaire en CM1 ;
  2. mobilisation des propriétés des triangles particuliers en 6e.

## Points à faire confirmer humainement

1. progression CM1 pour la reconstitution du tout ;
2. calibrage du nombre d'étapes des problèmes mixtes CM2 selon la période de l'année ;
3. statut des propriétés des triangles particuliers avant les items 6e ;
4. besoin de schémas pour aire, triangles et géométrie ;
5. qualité des `common_errors`, indices et remédiations.
