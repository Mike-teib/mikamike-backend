# Rapport QA pédagogique MikaMike

Généré par `pedagogy.qa v0.1.0` — données : `pedagogy/data`.

**Verdict : PASS** (code de sortie 0) — bank_ready : **true**

Règle : exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est INFO et ne fait jamais échouer ; les WARNING non plus.

## Totaux

| Élément | Nombre |
|---|---:|
| Notions | 1756 |
| Fichiers de notions | 27 |
| Sources officielles déclarées | 22 |
| Sources récupérées | 22 |
| Exercices | 0 |
| Quiz | 0 |
| Erreurs de chargement | 0 |
| Issues | 1796 (BLOCKER 0, ERROR 0, WARNING 1779, INFO 17) |

### Notions par statut de preuve

| Statut | Notions |
|---|---:|
| PROVEN_OFFICIAL | 1756 |

### Notions par matière

| Matière | Notions |
|---|---:|
| MATHS | 1394 |
| PHYSIQUE_CHIMIE | 97 |
| SCIENCES_TECHNOLOGIE | 202 |
| SVT | 63 |

### Notions par niveau

| Niveau | Notions |
|---|---:|
| 1RE | 175 |
| 2NDE | 172 |
| 3E | 77 |
| 4E | 119 |
| 5E | 140 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 88 |
| CM1 | 167 |
| CM2 | 139 |
| CP | 83 |
| TLE | 344 |

## Issues

### Par sévérité

| Sévérité | Issues |
|---|---:|
| INFO | 17 |
| WARNING | 1779 |

### Par code

| Code | Issues |
|---|---:|
| DUPLICATE_TITLE_SAME_LEVEL | 23 |
| EMPTY_PEDAGOGY | 1756 |
| NEAR_DUPLICATE_TITLE | 17 |

### Par matière

| Matière | Issues |
|---|---:|
| MATHS | 1434 |
| PHYSIQUE_CHIMIE | 97 |
| SCIENCES_TECHNOLOGIE | 202 |
| SVT | 63 |

### Par niveau

| Niveau | Issues |
|---|---:|
| 1RE | 195 |
| 2NDE | 172 |
| 3E | 77 |
| 4E | 119 |
| 5E | 140 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 89 |
| CM1 | 171 |
| CM2 | 144 |
| CP | 83 |
| TLE | 354 |

## Principales anomalies (BLOCKER / ERROR / WARNING, 60 premières)

| Sévérité | Code | Objet | Détail |
|---|---|---|---|
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.appliquer-un-taux-devolution-pour-calculer-une-valeur-finale-ou-initia` | meme_titre_que:MATHS.1RE.AUTO.appliquer-un-taux-devolution-pour-calculer-une-valeur-finale-ou-initia(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.calculer-des-probabilites-conditionnelles-lorsque-les-evenements-sont` | meme_titre_que:MATHS.1RE.AUTO.calculer-des-probabilites-conditionnelles-lorsque-les-evenements-sont(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.calculer-et-interpreter-des-indicateurs-statistiques-pour-une-serie-st` | meme_titre_que:MATHS.1RE.AUTO.calculer-et-interpreter-des-indicateurs-statistiques-pour-une-serie-st(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.calculer-le-taux-devolution-equivalent-a-plusieurs-evolutions-successi` | meme_titre_que:MATHS.1RE.AUTO.calculer-le-taux-devolution-equivalent-a-plusieurs-evolutions-successi(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.calculer-un-taux-devolution-lexprimer-en-pourcentage` | meme_titre_que:MATHS.1RE.AUTO.calculer-un-taux-devolution-lexprimer-en-pourcentage(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.calculer-un-taux-devolution-reciproque` | meme_titre_que:MATHS.1RE.AUTO.calculer-un-taux-devolution-reciproque(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.determiner-graphiquement-le-signe-dune-fonction-ou-son-tableau-de-vari` | meme_titre_que:MATHS.1RE.AUTO.determiner-graphiquement-le-signe-dune-fonction-ou-son-tableau-de-vari(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.determiner-le-coefficient-directeur-dune-droite-a-partir-des-coordonne` | meme_titre_que:MATHS.1RE.AUTO.determiner-le-coefficient-directeur-dune-droite-a-partir-des-coordonne(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.determiner-le-signe-dune-expression-du-premier-degre-dune-expression-f` | meme_titre_que:MATHS.1RE.AUTO.determiner-le-signe-dune-expression-du-premier-degre-dune-expression-f(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.determiner-les-solutions-dune-equation-produit-nul` | meme_titre_que:MATHS.1RE.AUTO.determiner-les-solutions-dune-equation-produit-nul(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.developper-factoriser-reduire-une-expression-algebrique-simple` | meme_titre_que:MATHS.1RE.AUTO.developper-factoriser-reduire-une-expression-algebrique-simple(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.distinguer-p-a-b-pa-b-pb-a` | meme_titre_que:MATHS.1RE.AUTO.distinguer-p-a-b-pa-b-pb-a(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.lire-graphiquement-lequation-reduite-dune-droite` | meme_titre_que:MATHS.1RE.AUTO.lire-graphiquement-lequation-reduite-dune-droite(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.lire-un-graphique-un-histogramme-un-diagramme-en-barres-ou-circulaire` | meme_titre_que:MATHS.1RE.AUTO.lire-un-graphique-un-histogramme-un-diagramme-en-barres-ou-circulaire(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.passer-du-graphique-aux-donnees-et-vice-versa` | meme_titre_que:MATHS.1RE.AUTO.passer-du-graphique-aux-donnees-et-vice-versa(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.resoudre-graphiquement-une-equation-une-inequation-du-type-x-k-x-k-etc` | meme_titre_que:MATHS.1RE.AUTO.resoudre-graphiquement-une-equation-une-inequation-du-type-x-k-x-k-etc(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.EAUTO.tracer-une-droite-donnee-par-son-equation-reduite-ou-par-un-point-et-s` | meme_titre_que:MATHS.1RE.AUTO.tracer-une-droite-donnee-par-son-equation-reduite-ou-par-un-point-et-s(course=SPECIALITE/MATHS_SPECIFIQUES_1RE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.1RE.PS.savoir-utiliser-ou-justifier-lindependance-de-deux-evenements` | meme_titre_que:MATHS.1RE.EALEA.savoir-utiliser-ou-justifier-lindependance-de-deux-evenements(course=MATHS_SPECIFIQUES_1RE/SPECIALITE) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.TLE.CAN.derivee-seconde-dune-fonction` | meme_titre_que:MATHS.TLE.AN.derivee-seconde-dune-fonction(course=SPECIALITE/MATHS_COMPLEMENTAIRES) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.TLE.CAN.deux-primitives-dune-meme-fonction-continue-sur-un-intervalle-differen` | meme_titre_que:MATHS.TLE.AN.deux-primitives-dune-meme-fonction-continue-sur-un-intervalle-differen(course=SPECIALITE/MATHS_COMPLEMENTAIRES) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.TLE.CAN.estimer-graphiquement-ou-encadrer-une-integrale-une-valeur-moyenne` | meme_titre_que:MATHS.TLE.AN.estimer-graphiquement-ou-encadrer-une-integrale-une-valeur-moyenne(course=SPECIALITE/MATHS_COMPLEMENTAIRES) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.TLE.CAN.interpreter-une-integrale-une-valeur-moyenne-dans-un-contexte-issu-dun` | meme_titre_que:MATHS.TLE.AN.interpreter-une-integrale-une-valeur-moyenne-dans-un-contexte-issu-dun(course=SPECIALITE/MATHS_COMPLEMENTAIRES) |
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `MATHS.TLE.CAN.point-dinflexion` | meme_titre_que:MATHS.TLE.AN.point-dinflexion(course=SPECIALITE/MATHS_COMPLEMENTAIRES) |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.calcul-de-1-2-n` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.calcul-de-1-q-qn` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.calcul-du-terme-general-dune-suite-arithmetique-dune-suite-geometrique` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.calculer-des-termes-dune-suite-definie-explicitement-par-recurrence-ou` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.choisir-une-forme-adaptee-developpee-reduite-canonique-factorisee-dune` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.conjecturer-dans-des-cas-simples-la-limite-eventuelle-dune-suite` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.dans-le-cadre-de-letude-dune-suite-utiliser-le-registre-de-la-langue-n` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.determiner-deux-nombres-reels-connaissant-leur-somme-s-et-leur-produit` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.determiner-les-fonctions-polynomes-du-second-degre-sannulant-en-deux-n` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.etudier-le-signe-dune-fonction-polynome-du-second-degre-donnee-sous-fo` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.exemples-de-modes-de-generation-dune-suite-explicite-un-n-par-une-rela` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.factorisation-de-xn-1-par-x-1-de-xn-an-par-x-a` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.factorisation-dun-polynome-du-troisieme-degre-admettant-une-racine-et` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.factoriser-une-fonction-polynome-du-second-degre-en-diversifiant-les-s` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.fonction-polynome-du-second-degre-donnee-sous-forme-factorisee-racines` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.forme-canonique-dune-fonction-polynome-du-second-degre-discriminant-fa` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.modeliser-un-phenomene-discret-a-croissance-lineaire-par-une-suite-ari` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.notations-u-n-un-u-n-un` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.pour-une-suite-arithmetique-ou-geometrique-calculer-le-terme-general-l` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.proposer-modeliser-une-situation-permettant-de-generer-une-suite-de-no` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.remboursement-dun-emprunt-par-annuites-constantes` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.resolution-de-lequation-du-second-degre` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.sens-de-variation-dune-suite` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.somme-des-n-premiers-carres-des-n-premiers-cubes` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.suites-arithmetiques-exemples-definition-calcul-du-terme-general-lien` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.suites-geometriques-exemples-definition-calcul-du-terme-general-lien-a` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.sur-des-exemples-introduction-intuitive-de-la-notion-de-limite-finie-o` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALG.tour-de-hanoi` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALGO.generer-une-liste-en-extension-par-ajouts-successifs-ou-en-comprehensi` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALGO.iterer-sur-les-elements-dune-liste` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALGO.manipuler-des-elements-dune-liste-ajouter-supprimer-etc-et-leurs-indic` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.ALGO.parcourir-une-liste` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.AN.approximation-lineaire-fonction-affine-tangente-x-a-a-x-a-et-approxima` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.AN.calculer-un-taux-de-variation-la-pente-dune-secante` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.AN.calculer-une-valeur-approchee-de-a-h` | common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.AN.cercle-trigonometrique-longueur-darc-radian` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.1RE.AN.cosinus-et-sinus-dun-nombre-reel-lien-avec-le-sinus-et-le-cosinus-dans` | learning_objectives,common_mistakes |

## Ce qui n'a PAS pu être vérifié

- Aucun exercice dans la banque : contrôles d'exercices non exercés.
- Aucune question de quiz dans la banque : contrôles de quiz non exercés.
- Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.
