# PEDAGOGY_CURRENT_STATE — État réel des contenus pédagogiques (2026-09-28)

Méthode : lecture seule de **toutes** les branches distantes (`git show` / `git ls-tree`),
aucune modification de contenu pendant cette phase. Rien n'est inventé : « absent » signifie
absent de toutes les branches.

## 1. Conclusion en une ligne

**Aucun contenu officiel prouvé n'existe dans le dépôt**, sur aucune branche : ni programme
officiel (PDF BO / Éduscol), ni registre de notions sourcé, ni lot M01 (346 notions), ni
C02 / Extraction V3. Les seules données de curriculum sont 47 notions historiques sans source.

## 2. Accès aux sources officielles

La politique réseau de l'environnement cloud **bloque** `education.gouv.fr`,
`eduscol.education.fr`, `cache.media.eduscol.education.fr`, `legifrance.gouv.fr` (403 au proxy).
Conséquence : aucun document officiel ne peut être récupéré depuis cette session. Toutes les
notions de ce chantier sont donc `UNPROVEN` (décision conforme à la consigne).

## 3. Inventaire

### 3.1 Branches (lignée vérifiée par `merge-base --is-ancestor`)
Chaîne linéaire : `main` → `cloud/mikamike-autonomous-20260926` (PR #3) → session2 → session3 →
session4 → release-candidate-1 → session6 (tête backend) → branches UI (`ui/*parent-v1*`,
`ui/*react*`). `jules-8418…` part de `main` et n'a jamais été fusionnée. Les branches
`backup/*antigravity*` suppriment 93 fichiers backend.

### 3.2 Ce qui existe réellement

| Élément | Où | Contenu réel | Exploitable ? |
|---|---|---|---|
| `CURRICULA_DATA` (`app/api/v1/parcours/curriculum_dataset.py`) | toutes branches (identique) | **47 notions** : maths primaire 5, 6e 5, 5e 6, 4e 5, 3e 5, 2de 5, 1re 5, tle 5 ; physique 5e 2 ; chimie 4e 2 ; SVT 3e 2 — **aucune source** | candidats à auditer uniquement |
| Catalogue d'exercices (`catalogue.py`) | main, session6 | **4 exercices** de maths écrits à la main | candidats à auditer |
| Catalogue Jules (`catalogue.py`, branche jules) | jules | **164 « exercices »** gabarits génériques (« Quelle est la définition ou le calcul direct de base pour : {titre} ? », réponses « oui »/« 1 ») | **non exploitable** (aucun contenu pédagogique réel) |
| `generate_catalogue.py` | jules | script qui n'écrit rien, aurait levé AttributeError (`n.niveau`) | obsolète |
| Rapports Jules `05_REPORTS/ORDRE_33…` | jules | matrice 41 notions × 4 exos « OUI » (gabarits) | obsolète, trompeur |
| `mock_curriculum.json` (front) | branches react/ui | **maquette** ; `meta.source_status` affirme « Officiel Éducation Nationale - Conforme BO » **sans aucune preuve** ; 11 chapitres, compteurs d'exercices sans contenu | **à neutraliser** (voir §5) |
| Modèle canonique `app/curriculum/*` (+ vérificateurs SymPy/unités/SVT, tuteur, quiz, chapitrage, publication, intégrité, harnais d'import) | PR #3 → session6 | code et tests, **aucune donnée** ; catalogue quiz vide (404 fail-closed) | réutilisable (logique) |
| `ARTIFACTS_REQUIRED_MANIFEST.json` | session6 | liste C02, C02-6, C02-6.1, **M01** (JSONL attendu), Extraction V3, PDF officiels — **tous `WAITING_FOR_ARTIFACT`** | référence des manques |
| Staging synthétique | session6 | lot 100 % `[SYNTHÉTIQUE]`, sources fictives rejetées hors test | tests uniquement |

### 3.3 Ce qui manque
- PDF officiels (BO / Éduscol) de toutes matières et niveaux, avec empreintes ;
- registre de notions officiel ; mappings notion ↔ chapitre prouvés ;
- **M01** (346 notions publiées) et sa ré-extraction ; C02 / C02-6 / C02-6.1 ; Extraction V3 ;
- toute banque d'exercices / quiz rattachée à une notion prouvée ;
- contenus Physique-Chimie et SVT au-delà de 6 notions historiques.

### 3.4 Obsolète / non prouvé
- 47 notions `CURRICULA_DATA` : non prouvées ; niveau « primaire » ambigu (ni CM1 ni CM2) ;
  physique et chimie séparées alors que la matière est « Physique-Chimie ».
- 164 gabarits Jules et leurs rapports « couverture OUI » : non pédagogiques.
- Le libellé « Officiel … Conforme BO » de la maquette front : **affirmation non prouvée**.

## 4. Doublons et conflits de format

| Axe | Formats rencontrés |
|---|---|
| Niveaux | `primaire, 6e…tle` (historique) · `cm1…tle` (modèle PR #3) · `6eme, 2nde_g, 1ere_g, tle_g, 2nde_gt…` (maquette) · `SIXIEME…` (staging) · **`6E…TLE` (ce chantier)** |
| Matières | `maths, physique, chimie, svt` · `mathematiques, physique-chimie, svt, sciences-et-technologie, enseignement-scientifique` · `maths, physique_chimie, svt` · **`MATHS, PHYSIQUE_CHIMIE, SVT, SCIENCES_TECHNOLOGIE, ENSEIGNEMENT_SCIENTIFIQUE`** |
| IDs de notions | `maths_5e_04` · `notion:historique:<slug>` · compétences `equations_1er_degre` (sans lien avec les IDs de notions) · **`MATHS.4E.NC.puissances`** |
| IDs d'exercices | `exo-maths-algebre-1` · `exo-maths_5e_01-0` · `P1A1-006` · `exo:fictif:contrat` · **`EX.<...>`** |
| Effectifs | Jules « 41 notions » ; manifeste/`legacy.py` « 42 » ; fichier réel **47** |

Doublons : les 4 exercices historiques recouvrent des notions historiques sous d'autres IDs ;
les 164 gabarits sont des quasi-doublons entre eux.

## 5. Risques de contamination ancien ↔ nouveau

1. **Faux label officiel** (maquette front) : risque qu'un contenu non prouvé soit présenté
   comme conforme au BO. Mesure : le registre de ce chantier interdit tout `official_wording`
   sur une notion non prouvée (invariant du modèle) ; recommandation : retirer ce libellé du front.
2. **Réimport des gabarits Jules** comme exercices : bloqué par la QA (réponses non
   auto-vérifiables, notion non prouvée → `NOTION_NOT_PROVEN` BLOCKER).
3. **Collision d'IDs** entre schémas : le nouveau schéma `SUBJ.LEVEL.DOMAIN.slug` est
   distinct de tous les anciens ; la correspondance est tracée (`legacy_ids`,
   `pedagogy/data/legacy/legacy_notions_map.json`) sans réécrire les anciens contenus.
4. **Mélange de versions de programme** (cycle 3 : version 2020 vs nouvelle version
   éventuelle ; tronc commun de maths en 1re) : chaque notion porte `official_program_version`
   et `school_year` ; la QA contrôle la cohérence avec la source.
5. **Correction silencieuse de contenus publiés (M01)** : interdite ; l'outil de comparaison
   est en lecture seule et refuse de conclure sans les deux corpus.

## 6. Décision de ce chantier

Construire l'architecture complète (modèle, preuve automatique à partir de PDF locaux,
validateurs, QA, graphe, API lecture seule, contrat tuteur, outil M01) et un **registre de
notions candidates `UNPROVEN`** couvrant 6e → Terminale, prêt à être prouvé dès que les PDF
officiels sont déposés. Aucun exercice n'est généré sur une notion non prouvée.
