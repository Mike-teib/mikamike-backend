# Rapport QA pédagogique MikaMike

Généré par `pedagogy.qa v0.1.0` — données : `pedagogy/data`.

**Verdict : PASS** (code de sortie 0) — bank_ready : **true**

Règle : exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est INFO et ne fait jamais échouer ; les WARNING non plus.

## Totaux

| Élément | Nombre |
|---|---:|
| Notions | 188 |
| Fichiers de notions | 3 |
| Sources officielles déclarées | 22 |
| Sources récupérées | 22 |
| Exercices | 0 |
| Quiz | 0 |
| Erreurs de chargement | 0 |
| Issues | 189 (BLOCKER 0, ERROR 0, WARNING 188, INFO 1) |

### Notions par statut de preuve

| Statut | Notions |
|---|---:|
| PROVEN_OFFICIAL | 188 |

### Notions par matière

| Matière | Notions |
|---|---:|
| MATHS | 188 |

### Notions par niveau

| Niveau | Notions |
|---|---:|
| CE1 | 65 |
| CE2 | 58 |
| CP | 65 |

## Issues

### Par sévérité

| Sévérité | Issues |
|---|---:|
| INFO | 1 |
| WARNING | 188 |

### Par code

| Code | Issues |
|---|---:|
| EMPTY_PEDAGOGY | 188 |
| NEAR_DUPLICATE_TITLE | 1 |

### Par matière

| Matière | Issues |
|---|---:|
| MATHS | 189 |

### Par niveau

| Niveau | Issues |
|---|---:|
| CE1 | 65 |
| CE2 | 59 |
| CP | 65 |

## Principales anomalies (BLOCKER / ERROR / WARNING, 60 premières)

| Sévérité | Code | Objet | Détail |
|---|---|---|---|
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.comprendre-utiliser-et-produire-une-suite-dinstructions-qui-codent-un` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.connaitre-et-utiliser-le-code-pour-les-angles-droits` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.connaitre-et-utiliser-le-vocabulaire-lie-aux-positions-relatives` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.connaitre-le-nombre-et-la-nature-des-faces-dun-cube-ou-dun-pave` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.connaitre-les-proprietes-des-angles-et-des-egalites-de-longueur-pour-l` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.construire-des-assemblages-de-cubes-et-de-paves` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.construire-et-utiliser-des-representations-dun-espace-familier-pour-lo` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.construire-un-cube-un-pave-droit-ou-une-pyramide` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.decrire-un-cube-un-pave-ou-une-pyramide-en-utilisant-les-termes-face-s` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.nommer-un-cube-une-boule-un-pave-un-cone-ou-une-pyramide` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.reconnaitre-les-solides-usuels-suivants-cube-boule-cone-pyramide-cylin` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.reconnaitre-nommer-et-decrire-un-cercle-un-carre-un-rectangle-un-trian` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.reproduire-ou-construire-un-carre-un-rectangle-un-triangle-un-triangle` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.situer-des-personnes-ou-des-objets-les-uns-par-rapport` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.utiliser-la-regle-graduee-lequerre-et-le-compas-comme-instruments-de-t` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.utiliser-la-regle-pour-verifier-des-alignements-et-lequerre-pour-verif` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.EG.utiliser-le-vocabulaire-geometrique-approprie` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.choisir-lunite-la-mieux-adaptee-pour-exprimer-une-longueur` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.comparer-des-longueurs` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.comparer-les-valeurs-en-euro-de-deux-ensembles-constitues-de-pieces-et` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.connaitre-et-utiliser-les-unites-metre-centimetre-kilometre-et-les-sym` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.connaitre-le-lien-entre-les-euros-et-les-centimes` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.connaitre-le-sens-de-lecriture-a-virgule-dune-somme-dargent` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.connaitre-les-relations-entre-les-unites-de-longueur-usuelles` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.connaitre-quelques-longueurs-de-reference` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.constituer-avec-des-euros-et-des-centimes-deuro-une-somme-dargent-dune` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.determiner-la-valeur-en-euro-et-centime-deuro-dun-ensemble-constitue-d` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.estimer-la-longueur-dun-objet-du-quotidien` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.savoir-mesurer-la-longueur-dun-segment-en-utilisant-une-regle-graduee` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.GM.simuler-des-achats-en-manipulant-des-pieces-et-des-billets-fictifs-ren` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.additionner-et-soustraire-des-fractions-de-meme-denominateur` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comparer-des-fractions-ayant-le-meme-denominateur` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comparer-des-fractions-dont-le-numerateur-est-1` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comparer-encadrer-intercaler-des-nombres-entiers-en-utilisant-les-symb` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comprendre-et-savoir-que-la-multiplication-est-commutative` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comprendre-et-savoir-utiliser-les-expressions-egal-a-superieur-a-infer` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comprendre-et-utiliser-le-symbole` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.comprendre-et-utiliser-les-nombres-ordinaux` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-dans-les-deux-sens-les-tables-daddition` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-dans-les-deux-sens-les-tables-de-multiplication` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-des-faits-multiplicatifs-usuels` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-et-utiliser-diverses-representations-dun-nombre-et-passer-de` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-et-utiliser-la-relation-entre-unites-et` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-et-utiliser-les-mots-denominateur-et-numerateur` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-la-notion-de-parite-dun-nombre` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-la-suite-ecrite-et-la-suite-orale-des-nombres-jusqua-mille` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-la-valeur-des-chiffres-en-fonction-de-leur-position-dans-un` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.connaitre-les-nombres-ordinaux-jusqua-cent` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.construire-des-collections-de-cardinal-donne` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.denombrer-des-collections-en-les-organisant` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.faire-le-lien-entre-le-rang-dun-objet-dans-une-liste-et-le-nombre-dele` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.ordonner-des-nombres-dans-lordre-croissant-ou-decroissant` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.poser-et-effectuer-des-additions-et-des-soustractions-en-colonnes` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.reperer-un-rang-ou-une-position-dans-une-file-orientee-ou-dans-une-lis` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.resoudre-des-problemes-additifs-de-comparaison-en-une-etape` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.resoudre-des-problemes-additifs-en-deux-etapes` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.resoudre-des-problemes-additifs-en-une-etape-de-type-parties-tout` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.resoudre-des-problemes-mixtes-en-deux-etapes-une-etape-additive-et-une` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.resoudre-des-problemes-multiplicatifs-en-une-etape` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.CE1.NCRP.savoir-interpreter-representer-ecrire-et-lire-des-fractions-inferieure` | common_mistakes |

## Ce qui n'a PAS pu être vérifié

- Aucun exercice dans la banque : contrôles d'exercices non exercés.
- Aucune question de quiz dans la banque : contrôles de quiz non exercés.
- Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.
