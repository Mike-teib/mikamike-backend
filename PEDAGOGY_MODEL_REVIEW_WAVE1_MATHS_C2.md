# Pré-relecture modèle — Vague 1 Mathématiques CP, CE1, CE2

## Portée

Cette passe est une **pré-relecture assistée**, pas une approbation humaine.

Fichiers examinés :

- `pedagogy/data/drafts/exercises/MATHS_CP.json`
- `pedagogy/data/drafts/quizzes/MATHS_CP.json`
- `pedagogy/data/drafts/exercises/MATHS_CE1.json`
- `pedagogy/data/drafts/quizzes/MATHS_CE1.json`
- `pedagogy/data/drafts/exercises/MATHS_CE2.json`
- `pedagogy/data/drafts/quizzes/MATHS_CE2.json`

Total : **162 exercices + 90 quiz = 252 items**, sur 9 notions.

Aucun item n'est approuvé ou publié par cette revue.

## Contrôles réalisés

### Structure

Pour chaque niveau :

- 54 exercices ;
- 30 quiz ;
- 3 notions ;
- exercices répartis en 15 DISCOVERY, 15 APPLICATION, 15 CONSOLIDATION et 9 ADVANCED.

### CP / CE1 — niveau numérique et opérations

Recherche automatique sur les énoncés, questions, solutions et explications :

- aucun symbole `÷` utilisé prématurément en CP ou CE1 ;
- aucun nombre décimal introduit prématurément ;
- aucune anomalie de structure détectée.

### CP — monnaie

La notion pilote porte sur la valeur d'un ensemble de pièces et billets.

Contrôles :

- montants entiers ;
- aucune écriture décimale ;
- après correction ci-dessous, tous les montants affichés dans les questions et choix restent dans la plage annoncée par le pilote (≤ 100 €).

Correction effectuée pendant la pré-relecture :

- `QZ.MATHS.CP.valeur-euros.q04`
- ancien distracteur : `205 €`, construit par concaténation de « 20 » et « 5 » ;
- nouveau distracteur : `20 €`, erreur plausible « oubli du billet de 5 € » ;
- bonne réponse inchangée : `25 €`.

Motif : `205 €` sortait du domaine numérique CP annoncé dans le dossier pilote, même comme distracteur.

### CE1 — unités de longueur

La relation `1 km = 1 000 m` est réellement mobilisée dans plusieurs items.

Les réponses numériques vérifiées utilisent des unités cohérentes (`cm`, `m`) et aucune réponse décimale n'est introduite.

Exemples relus :

- `1 km → 1 000 m` ;
- complément de 700 m à 1 km ;
- 4 tours de 250 m pour 1 km ;
- complément de 350 m + 400 m à 1 km.

### CE1 — problèmes multiplicatifs avec reste

Les cinq items signalés dans le PILOT ont été relus :

- `EX.MATHS.CE1.multiplicatifs.x01` : 74 cartes, pochettes de 10 → **8 pochettes nécessaires** ;
- `EX.MATHS.CE1.multiplicatifs.x02` : 50 roses, bouquets de 8 → **6 bouquets complets** ;
- `EX.MATHS.CE1.multiplicatifs.x03` : 130 personnes, cars de 40 → **4 cars minimum** ;
- `QZ.MATHS.CE1.multiplicatifs.q09` : 75 œufs, boîtes de 6 → **12 boîtes pleines** ;
- `QZ.MATHS.CE1.multiplicatifs.q10` : 189 photos, 10 par page → **19 pages nécessaires**.

La distinction entre « nombre de groupes complets » et « nombre de contenants nécessaires pour tout ranger » est explicite dans les consignes et les solutions.

**Pré-revue modèle : aucun blocage détecté sur ces cinq items.**

La validation humaine doit néanmoins confirmer que le vocabulaire est suffisamment clair pour le CE1.

### CE2 — sens de la division

Sur les 28 items de la notion pilote :

- aucune réponse décimale ;
- aucun exercice fondé sur une division avec reste comme réponse attendue ;
- pas de dérive vers la division posée hors périmètre détectée lors de cette passe.

### CE2 — périmètre

Recherche automatique dans les exercices :

- aucune formule du type `2 × (L + l)` imposée ;
- aucune mention d'une « formule du périmètre » qui court-circuiterait l'approche par longueur du contour.

Cela reste cohérent avec la règle du pilote : travailler le périmètre comme longueur du contour.

## Lisibilité

Longueur maximale des énoncés d'exercices observée :

- CP : 174 caractères ;
- CE1 : 195 caractères ;
- CE2 : 273 caractères.

Un item CE2 mérite une attention humaine spécifique :

- `EX.MATHS.CE2.valeur-position.x01`
- devinette de 273 caractères sur un nombre à quatre chiffres.

Le contenu est cohérent, mais la longueur justifie une vérification de lisibilité et, dans l'application, la possibilité d'un accompagnement audio.

## Verdict de pré-relecture modèle

Après la correction du distracteur `205 €` :

- **aucun blocker modèle identifié** sur la vague CP–CE2 ;
- aucune approbation humaine n'est enregistrée ;
- la revue enseignant reste requise avant tout `pedagogy.drafts approve`.

## Points à faire confirmer humainement

1. clarté des problèmes à reste au CE1 ;
2. charge de lecture de la devinette CE2 longue ;
3. adéquation des erreurs fréquentes/remédiations aux erreurs réellement observées en classe ;
4. éventuel besoin d'audio systématique au CP/CE1 ;
5. éventuel besoin d'illustrations pour les items de monnaie et périmètre.
