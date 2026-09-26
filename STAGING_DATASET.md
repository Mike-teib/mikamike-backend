# STAGING_DATASET — Jeu de données synthétique de staging

Code : `app/curriculum/staging_synthetique.py` (génération pure, déterministe),
`tools/staging_dataset.py` (CLI `generer` / `verifier` / `charger`).
Tests : `tests_cloud/test_staging_dataset.py`.

> **100 % FICTIF.** Aucune donnée réelle d'élève (les élèves de MikaMike sont mineurs), aucun
> extrait réel de programme officiel. Tous les textes commencent par `[SYNTHÉTIQUE]`. Les sources
> sont `fictive=True`, leurs URL pointent vers `https://example.invalid/staging/…` et leurs
> « PDF » sont des fichiers synthétiques de quelques lignes. Les comptes parents utilisent le
> domaine réservé `@example.com`, les élèves sont des pseudo-identifiants `eleve-synth-XXX`,
> sans prénom (libellés « Élève 001 », « Parent 001 » seulement).

## 1. Contenu

| Élément | Détail |
|---|---|
| Sources | 1 par programme, `fictive=True`, `sha256_document` = empreinte du PDF synthétique du lot |
| Programmes | 1 par (matière, cycle), rentrée 2025, niveaux conformes à `NIVEAUX_PAR_MATIERE` / `CYCLE_DU_NIVEAU` |
| Chapitres | 2 par niveau, intitulés génériques inventés |
| Notions | 3 par chapitre, `TEXT_EXACT`, preuve `PROVEN` (extrait synthétique contenant le texte, empreinte exacte) ; prérequis chaînés (chaque notion dépend de la précédente du même niveau), sans cycle |
| Enseignement scientifique | `preuve.disciplines_indiquees` = `disciplines_mobilisees` (IMPORT_CONTRACT §10) |
| Exercices | 2 par notion, vérificateur adapté à la matière : `maths_symbolique` (maths, calculs de ST et d'ES), `physique_grandeur` (PC, énergie en ES), `svt_vocabulaire` et `texte_exact` (SVT, ST) ; indices et erreurs fréquentes (jamais valides) |
| QCM (`QuestionQuiz`) | 1 par notion |
| Quiz complémentaires (`quiz_types.py`) | 1 `QuestionVraiFaux` par chapitre + 1 `QuestionClassement` par chapitre de maths |
| Chapitrage | structure du document + preuves `section_pdf` ⇒ rattachements **PROUVE** |
| Familles | 6 parents, 9 élèves, 10 liens parent ↔ élève |
| Progression | 120 tentatives datées (7 → 12 septembre 2026, UTC), avec et sans aide, sur 34 (élève, notion) |

### Volumétrie par matière

| Matière | Programmes | Niveaux | Chapitres | Notions | Exercices | QCM | Vrai/faux | Classement |
|---|---|---|---|---|---|---|---|---|
| mathematiques | 3 (cycle3, cycle4, lycée) | CM2, 6e, 5e, 3e, 2de, Tle | 12 | 36 | 72 | 36 | 12 | 12 |
| physique-chimie | 2 (cycle4, lycée) | 5e, 3e, 2de, 1re | 8 | 24 | 48 | 24 | 8 | 0 |
| svt | 2 (cycle4, lycée) | 4e, 2de, Tle | 6 | 18 | 36 | 18 | 6 | 0 |
| sciences-et-technologie | 1 (cycle3) | CM1, CM2, 6e | 6 | 18 | 36 | 18 | 6 | 0 |
| enseignement-scientifique | 1 (lycée) | 1re, Tle | 4 | 12 | 24 | 12 | 4 | 0 |
| **Total** | **9** | 18 couples matière × niveau | **36** | **108** | **216** | **108** | **36** | **12** |

Par couple (matière, niveau) : 2 chapitres, 6 notions, 12 exercices, 6 QCM (détail affiché par
`generer`).

### Familles (fictives)

| Parent | Enfants |
|---|---|
| parent-synth-001@example.com | eleve-synth-001 (CM2), eleve-synth-002 (6e) — *parent avec 2 enfants* |
| parent-synth-002@example.com | eleve-synth-003 (5e) |
| parent-synth-003@example.com | eleve-synth-003 (5e), eleve-synth-004 (3e) — *eleve-synth-003 a 2 parents* |
| parent-synth-004@example.com | eleve-synth-005 (4e) |
| parent-synth-005@example.com | eleve-synth-006 (2de), eleve-synth-007 (1re) |
| parent-synth-006@example.com | eleve-synth-008 (Tle), eleve-synth-009 (CM1) |

### Historiques de progression

Chaque (élève, notion) suit un profil ; le niveau obtenu par
`app.curriculum.pedagogie.progression.diagnostiquer` est **vérifié à la génération** :

| Profil (niveau moteur) | Tentatives (jour, correcte, aide) | Couples |
|---|---|---|
| MAITRISEE | J0 ✓, J0 ✓, J1 ✓, J2 ✓ (autonomes) | 6 |
| EN_COURS | J0 ✗, J0 ✓ aidée, J1 ✓, J1 ✓ | 6 |
| FRAGILE | J0 ✓, J0 ✗, J1 ✗, J1 ✗ aidée | 6 |
| NON_ACQUISE | J0 ✗, J0 ✗ aidée, J1 ✗, J2 ✗ | 8 |
| NON_EVALUEE | J0 ✓ aidée, J1 ✗ (R1 : < 3 observations) | 8 |

## 2. Arborescence générée : contenu publiable et données utilisateurs SÉPARÉS

`ecrire_lot_staging(<d>)` renvoie `LotStaging(sha_contenu, sha_utilisateurs)` et écrit :

```
<d>/contenu/        lot d'import v2 PUBLIABLE — AUCUNE donnée utilisateur
<d>/utilisateurs/   familles + progression FICTIVES — jamais dans un lot de contenu
```

### 2.1 `<d>/contenu/` (lot d'import v2)

```
sources/<programme>.pdf        source_document          source_pdf
structures/<programme>.json    structure_document       structure_pdf
SHA256_SOURCE.txt              manifest_sha256          manifest_sha256
referentiel.json               referentiel              referentiel
mapping.jsonl                  mapping_notion_chapitre  mapping_chapitre_notion
exercices.jsonl                index_contenus           index_exercices   {"kind": "exercice", "data": …}
quiz.jsonl                     index_contenus           index_quiz        {"kind": "quiz", "data": …}
quiz_complementaires.jsonl     opaque                   rapport           {"type": "vrai_faux"|"classement", "data": …}
IMPORT_MANIFEST.json           (ecrire_manifest_v2, lot_id staging-synthetique-v1, date 2026-09-01)
```

Résultat attendu de l'import épinglé (`importer(dossier, sha256_manifest=sha, rentree=2026,
autoriser_fictif=True)`) : **VALIDATED**, 0 anomalie, 108/108 notions générables, chapitrage
PROUVE pour les 108 notions. Sans `autoriser_fictif` : **REJECTED** (`SOURCE_FICTIVE_HORS_TEST`).
`DepotContenu(racine).publier(<d>/contenu, sha)` est donc refusé hors mode test (rien n'est copié) ;
avec `DepotContenu(racine, autoriser_fictif=True)` le lot publié ne contient aucune donnée
utilisateur (aucun e-mail, aucun `eleve-synth`, ni familles ni progression — testé par balayage
des fichiers copiés).

### 2.2 `<d>/utilisateurs/`

```
familles.json                  parents (@example.com), élèves (eleve-synth-XXX), liens
progression.jsonl              une tentative par ligne (pseudo_id, exercice, notion, résultat, aide, date UTC)
UTILISATEURS_MANIFEST.json     {"format": "mika-staging-utilisateurs/1",
                                "fichiers": [{"chemin", "sha256", "taille"}],
                                "sha_lot_contenu": <SHA du manifest de contenu>}
```

### 2.3 SHA par défaut (graine `mikamike-staging-v1`)

| Manifeste | SHA-256 |
|---|---|
| `contenu/IMPORT_MANIFEST.json` (à épingler) | `495e8becfddff7ca7051c501f084513690b7bcc81aef571a8ba0d5e566887193` |
| `utilisateurs/UTILISATEURS_MANIFEST.json` | `4c4434578f5e8ccd57e453c3a4ee7c03a8173696c34ef540cee122bd10a220d5` |

Recalculés et affichés par `generer` ; ils changent si le code du générateur ou la graine change.

## 3. Commandes

```bash
source .venv/bin/activate
# secrets / bases de STAGING (jamais ceux de production)
export MIKA_JWT_SECRET=… MIKA_PSEUDO_SECRET=… MIKA_DB_URL=… BILLING_DB_URL=…

# 1. Générer (dossier vide ou inexistant) : écrit contenu/ + utilisateurs/, affiche les deux SHA
#    (sha256_manifest_contenu = à épingler) et la volumétrie
python -m tools.staging_dataset generer --sortie /tmp/lot-staging [--graine mikamike-staging-v1]

# 2. Vérifier : import strict épinglé de /tmp/lot-staging/contenu + intégrité croisée + quiz
#    complémentaires (code 0 si tout est vert ; --dossier accepte aussi directement le dossier contenu/)
python -m tools.staging_dataset verifier --dossier /tmp/lot-staging --sha <sha contenu> [--rentree 2026]

# 3. Charger familles + tentatives (depuis /tmp/lot-staging/utilisateurs, empreintes vérifiées)
#    dans les bases configurées (schéma appliqué au préalable)
python -m tools.db upgrade
python -m tools.staging_dataset charger --dossier /tmp/lot-staging [--sha-utilisateurs <sha utilisateurs>]
```

Codes de sortie de `charger` : 0 succès · 1 erreur (données utilisateurs altérées, fichier en trop
ou manquant, données non synthétiques, schéma absent) · **2 refus production** · **3 base non synthétique**.

## 4. Garanties

- **Fictif** : textes préfixés, sources fictives, URL `example.invalid`, e-mails `@example.com`,
  pseudo-identifiants, aucun prénom ni champ nominatif ; le lot ne devient jamais VALIDATED en
  mode production (source fictive ⇒ tout le lot refusé). Testé par balayage de tous les fichiers.
- **Déterministe** : aucune horloge ni hasard global (`random.Random` initialisé par graine +
  identifiant), JSON à clés triées ; deux générations ⇒ mêmes octets, même SHA.
- **Idempotent** : `charger` réutilise les comptes existants (par e-mail), ne recrée pas un lien
  existant, n'insère pas une tentative déjà présente (élève, exercice, notion, horodatage,
  résultat, aide) ; les états de maîtrise sont RECALCULÉS par le moteur sur l'historique
  (`moteur.evaluer`), jamais lus dans le lot.
- **Jamais en production** : `MIKA_ENV=production|prod` ⇒ refus (code 2) avant toute connexion ;
  une base billing contenant un compte hors `@example.com` ⇒ refus (code 3), rien n'est écrit.
- **Comptes** : mot de passe aléatoire (`secrets.token_urlsafe(32)`) haché, jamais affiché ni
  conservé ; `email_verifie=True` ; rôle `parent` ; abonnement `aucun` (créé par `creer_compte`).
- **Séparation** : le lot de contenu publiable ne contient aucune donnée utilisateur ;
  `utilisateurs/` est vérifié (empreintes, tailles, aucun fichier en trop ou manquant, via
  `UTILISATEURS_MANIFEST.json`) avant tout chargement ; toute altération ⇒ refus (code 1), rien
  n'est écrit.

## 5. Limites

- **Quiz complémentaires hors index canonique** : `index_contenus` n'accepte que `QuestionQuiz`
  (`kind: quiz`) et `verifier_integrite` ne contrôle que ce type ; les questions de `quiz_types.py`
  sont donc livrées en `opaque` et vérifiées à part (`quiz_types.valider`, commande `verifier`).
- **Pas de plans de guidage** (`plans_guidage`) ni de questions d'association / réponse courte.
- **Pédagogie non validée** : contenus simples et répétitifs (calculs, vocabulaire), destinés à
  éprouver la chaîne technique, pas à enseigner. Les niveaux choisis ne couvrent pas tous les
  couples matière × niveau (18 sur 26 possibles).
- Connexion des parents de démonstration : aucun mot de passe n'est connu et le dépôt n'expose
  pas de route de réinitialisation ; pour se connecter en staging, créer un compte séparé via
  l'inscription (ou étendre l'outil). Les tableaux de bord restent consultables en
  `MIKA_AUTH_MODE=off` (jamais en production).
- Les tentatives sont horodatées en septembre 2026 (dates fixes, déterminisme) : elles
  vieillissent avec le temps réel ; `mika_tentatives` n'est pas purgée automatiquement
  (`app/core/retention.py`).
