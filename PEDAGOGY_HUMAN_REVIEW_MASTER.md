# MikaMike — dossier maître de relecture humaine du pilote

## Statut

Ce document organise la relecture humaine avant toute approbation ou publication.

État de référence avant cette mise à jour :

- 3 188 notions `PROVEN_OFFICIAL` issues de 23 PDF officiels avec page et SHA-256 ;
- 1 814 exercices brouillons et 960 quiz brouillons réels dans le jeu de validation global ;
- 108 notions représentées dans les brouillons (pilote + historique) ;
- pilote principal : 96 notions, à raison de 3 notions par niveau et par matière couverte ;
- 86 exercices historiques rattachés à 15 `notion_id` distincts ; l'ancien exercice n°115 reste volontairement `UNMAPPED` ;
- les fichiers `_EXEMPLE_*.json` sont des fixtures de test et sont explicitement exclus du chargement, de la file de revue et de l'approbation ;
- banque servie aux élèves : 0 exercice, 0 quiz ;
- aucune approbation humaine automatique.

Le principe reste : **preuve documentaire ≠ approbation pédagogique**. Une notion doit être `PROVEN_OFFICIAL` puis `APPROVED` humainement avant qu'un contenu associé devienne éligible.

## Ce qui est déjà fermé automatiquement

Les points suivants ne doivent plus être considérés comme des blocages de relecture :

- séparateurs de milliers français : `1 200` est accepté comme `1200` ;
- constante d'Euler : `e^x`, `e²` et `exp(...)` sont interprétés correctement ; `2e` reste distinct de `e²` ;
- unités reconnues : `€`, `°`, `Bq`, `an(s)`, `jour(s)` ;
- factorisation scolaire : une écriture comme `3(x+5)` peut satisfaire `required_form=factorisee` ;
- QCM : à l'approbation, les choix sont permutés de façon déterministe avec remappage de la bonne réponse et des diagnostics ;
- API élève : les champs de correction privés (`correct_answer`, `reference_answer`, `explanation`, rationales) ne sont pas envoyés avec la question ;
- les cinq anciens exercices PC Terminale de décroissance qui demandaient « le nombre seul » utilisent maintenant réellement `Bq` ou `an`.

## Règles de relecture

Pour chaque notion :

1. vérifier le libellé officiel, la page source et l'adéquation au niveau ;
2. relire les 18 exercices puis les 10 quiz du pilote ;
3. vérifier la solution, les étapes, les indices, les erreurs fréquentes et la remédiation ;
4. vérifier le niveau de langue et la difficulté réelle ;
5. vérifier que les variantes de réponse légitimes sont acceptées ;
6. ne jamais approuver un item par simple héritage de l'approbation de sa notion ;
7. approuver par petits lots, puis rejouer `python -m pedagogy.drafts check` avant le lot suivant ;
8. ne rien publier automatiquement après approbation.

## Ordre de revue recommandé

### Vague 1 — Mathématiques cycle 2 : CP, CE1, CE2

Fichier : `pedagogy/data/drafts/PILOT_MATHS_CP_CE2.md`

Priorités humaines :

- clarté orale/écrite des consignes pour CP/CE1 ;
- problèmes multiplicatifs avec reste au CE1 ;
- vocabulaire de numération et monnaie ;
- vérifier que les exemples avancés restent dans les limites du programme.

### Vague 2 — Mathématiques cycle 3 : CM1, CM2, 6e

Fichier : `pedagogy/data/drafts/PILOT_MATHS_CM1_6E.md`

Priorités humaines :

- CM1 : confirmer le prolongement « reconstitution du tout » pour fraction d'une quantité ;
- CM1 : proportionnalité sans tableau ni produit en croix ;
- CM2 : calibrage des problèmes mixtes en plusieurs étapes ;
- 6e : vérifier les items d'angles mobilisant des propriétés de triangles particuliers ;
- décider où ajouter des schémas (aires, triangles, géométrie).

### Vague 3 — Mathématiques collège : 5e, 4e, 3e

Fichier : `pedagogy/data/drafts/PILOT_MATHS_5E_3E.md`

Priorités humaines :

- conformité précise au niveau ;
- vocabulaire côté adjacent/opposé, image/antécédent, médiane, probabilités ;
- équilibre Pythagore/Thalès en 4e ;
- arrondis des longueurs ;
- besoin de figures pour Thalès, triangles, échelles et trigonométrie ;
- valider les diagnostics `common_errors` et les remédiations.

### Vague 4 — Mathématiques lycée : 2de, 1re, Tle

Fichier : `pedagogy/data/drafts/PILOT_MATHS_LYCEE.md`

Priorités humaines :

- place des inéquations en 2de et de l'exponentielle en 1re ;
- vocabulaire racine, discriminant, convergence, primitive ;
- rendu des intégrales LaTeX dans l'application ;
- politique d'arrondi ;
- figures/courbes absentes à compléter si nécessaire ;
- diagnostics d'erreurs et qualité des remédiations.

### Vague 5 — Sciences et technologie : CP → 6e

Fichier : `pedagogy/data/drafts/PILOT_ST.md`

Priorités humaines :

- arbitrer les affectations d'année des notions de cycle : environ 39 notions sont des choix internes de placement ;
- transition programme cycle 3 entre CM1, CM2 et 6e ;
- formulations simplifiées : énergie, groupes d'aliments, saisons, masse/poids, besoins des végétaux, système solaire ;
- lisibilité CP/CE1 et besoin d'audio ;
- vérifier si les conversions d'unités doivent être acceptées quand l'énoncé impose une unité précise.

### Vague 6 — Physique-chimie : 5e → Tle

Fichier : `pedagogy/data/drafts/PILOT_PC.md`

Priorités humaines :

- arbitrer les affectations d'année du cycle 4 conjointement avec la SVT : environ 111 notions PC/SVT de cycle 4 nécessitent une décision de placement ;
- 5e–3e : vocabulaire et puissances de 10 ;
- 2de : chiffres significatifs, notation scientifique, constante d'Avogadro, vecteur vitesse ;
- 1re : titrages et équations de réaction, énergie mécanique, ondes ;
- Tle : pH, équations horaires, décroissance radioactive ;
- décider la politique sur le nombre de décimales du pH ;
- valider les `common_errors` et `estimated_time_min`.

### Vague 7 — SVT et enseignement scientifique

Fichier : `pedagogy/data/drafts/PILOT_SVT_ES.md`

Priorités humaines :

- vérifier toutes les valeurs scientifiques de référence ;
- marquer explicitement « données simplifiées » lorsque les jeux de données sont construits pour l'exercice ;
- compléter les variantes `EXACT_TEXT` légitimes ;
- santé : vocabulaire factuel, non diagnostique et non stigmatisant ;
- audition : présenter +3 dB / durée comme convention de prévention, pas comme seuil médical individuel ;
- climat : distinguer clairement effet de serre naturel et renforcement anthropique ;
- SVT Tle : notation du brassage ;
- ES 1re : valeurs d'albédo comme ordres de grandeur ;
- ES Tle : valider ou déplacer l'item CMR x01 ;
- ES Tle : formulation Hardy-Weinberg « à partir de la seconde génération ».

## Arbitrages de cycle à ne pas automatiser

Deux ensembles doivent rester en attente d'une décision pédagogique humaine :

- environ 111 notions de PC/SVT du cycle 4, dont le programme est commun au cycle mais que le registre affecte à une année pour pouvoir servir une progression ;
- environ 39 notions de sciences et technologie dont le placement annuel a été choisi dans les modules `pedagogy/ingest/`.

Aucun script ne doit transformer ces choix internes en vérité officielle : le PDF officiel prouve l'appartenance au cycle, pas nécessairement l'année retenue.

## Exercices historiques

- 87 exercices historiques ont été audités ;
- 86 sont repris ;
- ils couvrent 15 `notion_id` distincts ;
- le n°115 reste `UNMAPPED`.

Décision recommandée pour le n°115 : le conserver hors banque tant qu'une notion officielle suffisamment précise ne couvre pas explicitement son problème multiplicatif en plusieurs étapes. Ne pas le rattacher artificiellement à une notion voisine.

## File de relecture en lecture seule

Avant toute approbation, générer la file courante :

```bash
python -m pedagogy.drafts review-plan
```

Le rapport est écrit par défaut dans `reports/DRAFTS_REVIEW_PLAN.json` et contient, pour chaque notion :
matière, niveau, titre, statut de preuve, statut de revue, nombre d'exercices, nombre de quiz et indicateur
`ready_for_human_review`. La CI publie aussi ce rapport comme artefact `pedagogy-human-review-plan`.

Cette commande ne déplace, n'approuve et ne publie aucun contenu.

## Procédure d'approbation

Exemple pour une notion et quelques items seulement :

```bash
python -m pedagogy.drafts approve \
  --reviewer "<nom_du_relecteur>" \
  --notion <NOTION_ID> \
  --item <EXERCISE_ID> \
  --item <QUIZ_ID>

python -m pedagogy.drafts check
```

La commande `approve` exécute désormais un **préflight complet avant la première écriture** :
toutes les notions et tous les items demandés doivent exister, les notions doivent être prouvées,
les items doivent être valides, et chaque item doit dépendre d'une notion déjà approuvée ou approuvée
dans le même lot. Une demande invalide s'arrête avant toute mutation.

Avant tout lot suivant :

- inspecter le diff de la banque ;
- vérifier la permutation des QCM ;
- vérifier que la clé de correction ne fuit pas dans le payload élève ;
- rejouer la CI pédagogie ;
- ne pas activer de publication ou d'intégration dans `main` sans décision séparée.

## Critères STOP

Arrêter un lot et ne rien approuver si l'un des cas suivants apparaît :

- doute sur le niveau ou l'année d'une notion ;
- libellé tronqué ou source ambiguë ;
- réponse correcte pouvant être rejetée ;
- plusieurs réponses raisonnables à une question supposée fermée ;
- donnée scientifique présentée comme réelle alors qu'elle est construite ;
- item de santé pouvant être lu comme conseil ou diagnostic ;
- solution qui dépend d'une lettre/position de QCM au lieu du texte de la réponse ;
- exercice qui nécessite une figure absente pour être non ambigu.

## État attendu après cette phase

Cette phase peut produire des notions et items `APPROVED` dans la banque de travail, mais **ne doit pas à elle seule les publier aux élèves**. La publication et le déploiement restent une décision séparée.
