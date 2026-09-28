# Rapport QA pédagogique MikaMike

Généré par `pedagogy.qa v0.1.0` — données : `pedagogy/data`.

**Verdict : PASS** (code de sortie 0) — bank_ready : **true**

Règle : exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est INFO et ne fait jamais échouer ; les WARNING non plus.

## Totaux

| Élément | Nombre |
|---|---:|
| Notions | 905 |
| Fichiers de notions | 15 |
| Sources officielles déclarées | 22 |
| Sources récupérées | 22 |
| Exercices | 0 |
| Quiz | 0 |
| Erreurs de chargement | 0 |
| Issues | 915 (BLOCKER 0, ERROR 0, WARNING 905, INFO 10) |

### Notions par statut de preuve

| Statut | Notions |
|---|---:|
| PROVEN_OFFICIAL | 905 |

### Notions par matière

| Matière | Notions |
|---|---:|
| MATHS | 703 |
| SCIENCES_TECHNOLOGIE | 202 |

### Notions par niveau

| Niveau | Notions |
|---|---:|
| 3E | 37 |
| 4E | 34 |
| 5E | 105 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 88 |
| CM1 | 167 |
| CM2 | 139 |
| CP | 83 |

## Issues

### Par sévérité

| Sévérité | Issues |
|---|---:|
| INFO | 10 |
| WARNING | 905 |

### Par code

| Code | Issues |
|---|---:|
| EMPTY_PEDAGOGY | 905 |
| NEAR_DUPLICATE_TITLE | 10 |

### Par matière

| Matière | Issues |
|---|---:|
| MATHS | 713 |
| SCIENCES_TECHNOLOGIE | 202 |

### Par niveau

| Niveau | Issues |
|---|---:|
| 3E | 37 |
| 4E | 34 |
| 5E | 105 |
| 6E | 158 |
| CE1 | 94 |
| CE2 | 89 |
| CM1 | 171 |
| CM2 | 144 |
| CP | 83 |

## Principales anomalies (BLOCKER / ERROR / WARNING, 60 premières)

| Sévérité | Code | Objet | Détail |
|---|---|---|---|
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.deux-triangles-semblables-peuvent-etre-definis-par-la-proportionnalite` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.le-reperage-setend-a-la-sphere-latitude-longitude` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.le-theoreme-de-thales-et-sa-reciproque-dans-la-configuration-du-papill` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.les-eleves-identifient-des-transformations-dans-des-frises-des-pavages` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.les-eleves-produisent-et-mettent-en-relation-differentes-representatio` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.les-eleves-transforment-a-la-main-ou-a-laide-dun-logiciel-une-figure-p` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.les-lignes-trigonometriques-cosinus-sinus-tangente-dans-le-triangle-re` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.pour-faire-le-lien-entre-les-transformations-et-les-configurations-du` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.un-logiciel-de-geometrie-est-utilise-pour-visualiser-des-solides-et-le` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.une-caracterisation-angulaire-de-cette-definition-peut-etre-donnee-et` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.EG.une-definition-et-une-caracterisation-des-triangles-semblables-sont-do` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.GM.la-formule-donnant-le-volume-dune-boule-est-utilisee` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.GM.le-travail-sur-les-grandeurs-mesurables-et-les-unites-est-poursuivi` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.GM.les-eleves-connaissent-et-utilisent-leffet-des-transformations-au-prog` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.la-double-distributivite-est-abordee-le-lien-est-fait-avec-la-simple-d` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.la-factorisation-dune-expression-du-type-a2-b2-permet-de-resoudre-des` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.la-notion-de-fraction-irreductible-est-abordee-en-lien-avec-celles-de` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.la-notion-de-fraction-irreductible-est-introduite` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.la-racine-carree-est-utilisee-dans-le-cadre-de-la-resolution-de-proble` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.le-travail-est-consolide-notamment-lors-des-resolutions-de-problemes` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.le-travail-sur-les-expressions-litterales-est-consolide-avec-des-trans` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.les-puissances-de-base-quelconque-dexposants-negatifs-sont-introduites` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.NC.lutilisation-dun-tableur-dun-logiciel-de-programmation-ou-dune-calcula` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.dans-des-cas-tres-simples-il-est-cependant-possible-dintroduire-des-ex` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.le-champ-des-problemes-de-geometrie-relevant-de-la-proportionnalite-es` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.le-constat-de-la-stabilisation-des-frequences-sappuie-sur-la-simulatio` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.le-lien-est-fait-entre-taux-devolution-et-coefficient-multiplicateur-a` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.le-travail-sur-les-representations-graphiques-le-calcul-en-particulier` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-calculs-de-probabilites-a-partir-de-denombrements-sappliquent-a-de` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-denombrements-sappuient-alors-uniquement-sur-des-tableaux-a-double` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-eleves-simulent-une-experience-aleatoire-a-laide-dun-tableur-ou-du` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-fonctions-affines-et-lineaires-sont-presentees-par-leurs-expressio` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-fonctions-sont-utilisees-pour-modeliser-des-phenomenes-continus-et` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.les-notions-de-variable-de-fonction-dantecedent-dimage-sont-formalisee` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.un-indicateur-de-dispersion-est-introduit-letendue` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.un-nouveau-type-de-diagramme-est-introduit-les-histogrammes-pour-des-c` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.3E.OGDF.un-travail-est-mene-sur-le-passage-dun-mode-de-representation-dune-fon` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.la-definition-du-cosinus-dun-angle-dun-triangle-rectangle-decoule-grac` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.le-reperage-se-fait-dans-un-pave-droit-abscisse-ordonnee-altitude` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.le-theoreme-de-thales-et-sa-reciproque-dans-la-configuration-des-trian` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.les-cas-degalite-des-triangles-sont-presentes-et-utilises-pour-resoudr` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.les-eleves-produisent-et-mettent-en-relation-une-representation-en-per` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.EG.les-eleves-sont-amenes-a-transformer-a-la-main-ou-a-laide-dun-logiciel` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.GM.des-grandeurs-produits-par-exemple-trafic-energie-et-des-grandeurs-quo` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.GM.le-lexique-des-formules-setend-au-volume-des-pyramides-et-du-cone-le-l` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.GM.les-conversions-dunites-sont-travaillees` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.GM.les-eleves-connaissent-et-utilisent-leffet-dun-agrandissement-ou-dune` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.GM.les-eleves-sont-sensibilises-au-controle-de-la-coherence-des-resultats` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.la-notion-de-solution-dune-equation-est-formalisee` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.la-notion-dinverse-est-introduite-les-operations-entre-fractions-sont` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.la-propriete-de-distributivite-simple-est-formalisee-et-est-utilisee-p` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.la-racine-carree-est-introduite-en-lien-avec-des-situations-geometriqu` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.la-structure-dune-expression-litterale-somme-ou-produit-est-etudiee` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.le-produit-et-le-quotient-de-decimaux-relatifs-sont-abordes` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.le-quotient-de-deux-nombres-decimaux-peut-ne-pas-etre-un-nombre-decima` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.le-recours-au-calcul-litteral-vient-completer-pour-tout-ou-partie-des` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.le-travail-sur-les-formules-est-poursuivi-parallelement-a-la-presentat` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.les-eleves-determinent-la-liste-des-nombres-premiers-inferieurs-ou-ega` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.les-eleves-sont-conduits-a-comparer-des-nombres-rationnels-a-en-utilis` | learning_objectives,common_mistakes |
| WARNING | EMPTY_PEDAGOGY | `MATHS.4E.NC.les-equations-sont-travaillees-tout-au-long-de-lannee-par-un-choix-pro` | learning_objectives,common_mistakes |

## Ce qui n'a PAS pu être vérifié

- Aucun exercice dans la banque : contrôles d'exercices non exercés.
- Aucune question de quiz dans la banque : contrôles de quiz non exercés.
- Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.
