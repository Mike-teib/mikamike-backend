# Rapport QA pédagogique MikaMike

Généré par `pedagogy.qa v0.1.0` — données : `pedagogy/data`.

**Verdict : PASS** (code de sortie 0) — bank_ready : **true**

Règle : exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est INFO et ne fait jamais échouer ; les WARNING non plus.

## Totaux

| Élément | Nombre |
|---|---:|
| Notions | 3188 |
| Fichiers de notions | 35 |
| Sources officielles déclarées | 22 |
| Sources récupérées | 22 |
| Exercices | 0 |
| Quiz | 0 |
| Erreurs de chargement | 0 |
| Issues | 3235 (BLOCKER 0, ERROR 0, WARNING 3212, INFO 23) |

### Notions par statut de preuve

| Statut | Notions |
|---|---:|
| PROVEN_OFFICIAL | 3188 |

### Notions par matière

| Matière | Notions |
|---|---:|
| ENSEIGNEMENT_SCIENTIFIQUE | 309 |
| MATHS | 1394 |
| PHYSIQUE_CHIMIE | 712 |
| SCIENCES_TECHNOLOGIE | 202 |
| SVT | 571 |

### Notions par niveau

| Niveau | Notions |
|---|---:|
| 1RE | 719 |
| 2NDE | 487 |
| 3E | 77 |
| 4E | 119 |
| 5E | 140 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 88 |
| CM1 | 167 |
| CM2 | 139 |
| CP | 83 |
| TLE | 917 |

## Issues

### Par sévérité

| Sévérité | Issues |
|---|---:|
| INFO | 23 |
| WARNING | 3212 |

### Par code

| Code | Issues |
|---|---:|
| DUPLICATE_TITLE_SAME_LEVEL | 24 |
| EMPTY_PEDAGOGY | 3188 |
| NEAR_DUPLICATE_TITLE | 23 |

### Par matière

| Matière | Issues |
|---|---:|
| ENSEIGNEMENT_SCIENTIFIQUE | 309 |
| MATHS | 1434 |
| PHYSIQUE_CHIMIE | 719 |
| SCIENCES_TECHNOLOGIE | 202 |
| SVT | 571 |

### Par niveau

| Niveau | Issues |
|---|---:|
| 1RE | 741 |
| 2NDE | 488 |
| 3E | 77 |
| 4E | 119 |
| 5E | 140 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 89 |
| CM1 | 171 |
| CM2 | 144 |
| CP | 83 |
| TLE | 931 |

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
| WARNING | DUPLICATE_TITLE_SAME_LEVEL | `PC.TLE.OS.capacite-mathematique-resoudre-une-equation-differentielle-lineaire-du` | meme_titre_que:PC.TLE.ENERGIE.capacite-mathematique-resoudre-une-equation-differentielle-lineaire-du(course=SPECIALITE/SPECIALITE) |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.ainsi-les-mineraux-se-caracterisent-par-leur-composition-chimique-et-l` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.analyser-et-interpreter-des-documents-historiques-relatifs-a-la-theori` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.calculer-le-nombre-de-noyaux-restants-au-bout-de-n-demi-vies` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.certaines-roches-volcaniques-contiennent-du-verre-issu-de-la-solidific` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.certains-noyaux-sont-instables-et-se-desintegrent-radioactivite` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.citer-quelques-precautions-inherentes-a-lutilisation-de-substances-rad` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.dans-le-cas-des-solides-amorphes-lempilement-dentites-se-fait-sans-ord` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.des-structures-cristallines-existent-aussi-dans-les-organismes-biologi` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.discuter-du-statut-des-virus-vivants-ou-non-vivants` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.distinguer-en-matiere-dechelle-et-dorganisation-spatiale-atome-ou-mole` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.expliquer-lutilisation-de-noyaux-radioactifs-dans-un-contexte-medical` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.identifier-des-structures-cristallines-chez-les-etres-vivants` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.identifier-des-structures-cristallines-sur-un-echantillon-ou-une-image` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.la-cellule-unite-fondamentale-du-vivant-est-un-milieu-reactionnel-aque` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.la-decouverte-de-lunite-cellulaire-est-liee-a-linvention-du-microscope` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.la-demi-vie-dun-noyau-radioactif-est-la-duree-necessaire-pour-que-la-m` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.la-matiere-connue-de-lunivers-est-formee-principalement-dhydrogene-et` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.le-chlorure-de-sodium-solide-present-dans-les-roches-ou-issu-de-levapo` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.le-fonctionnement-cellulaire-necessite-un-apport-en-energie-la-cellule` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.lequation-dune-reaction-nucleaire-stellaire-etant-fournie-reconnaitre` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.les-noyaux-des-atomes-de-la-centaine-delements-chimiques-stables-resul` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.linstant-de-desintegration-dun-noyau-radioactif-individuel-est-aleatoi` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.lobservation-de-structures-semblables-dans-de-tres-nombreux-organismes` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.mettre-en-evidence-des-echanges-au-travers-de-la-membrane-plasmique` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.mettre-en-relation-la-structure-amorphe-ou-cristalline-dune-roche-et-l` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.plus-generalement-la-structure-microscopique-dun-cristal-conditionne-c` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.plus-recemment-linvention-du-microscope-electronique-a-permis-lexplora` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.produire-et-analyser-differentes-representations-graphiques-de-labonda` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.relier-la-presence-de-molecules-exogenes-avec-le-bon-fonctionnement-ce` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.relier-lechelle-de-la-cellule-de-ses-organites-et-des-molecules-qui-la` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.relier-lorganisation-de-la-maille-au-niveau-microscopique-a-la-structu` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.situer-les-ordres-de-grandeur-atome-molecule-organite-cellule-organism` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.un-compose-de-formule-chimique-donnee-peut-cristalliser-sous-different` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.une-roche-est-formee-de-lassociation-de-cristaux-dun-meme-mineral-ou-d` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.utiliser-une-decroissance-radioactive-pour-une-datation` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `ES.1RE.MATIERE.utiliser-une-representation-en-trois-dimensions-3d-informatisee-du-cri` | learning_objectives,common_mistakes |

## Ce qui n'a PAS pu être vérifié

- Aucun exercice dans la banque : contrôles d'exercices non exercés.
- Aucune question de quiz dans la banque : contrôles de quiz non exercés.
- Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.
