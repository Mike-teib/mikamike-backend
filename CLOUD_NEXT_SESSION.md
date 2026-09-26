# CLOUD_NEXT_SESSION — Checkpoint permanent

> Protocole de reprise : lire ce fichier, puis `CLOUD_REVIEW_SESSION2.md`, `CLOUD_BACKLOG_MIKAMAIKE.md`,
> `CLOUD_TEST_REPORT.md`, `CLOUD_SECURITY_REPORT.md`, `AUTH_CONTRACT.md`, `FRONT_AUTH_INTEGRATION.md`,
> `MIKA_API_CONTRACT.md`, `IMPORT_CONTRACT.md`, `IMPORT_TEST_HARNESS_REPORT.md`,
> `CLOUD_DB_MIGRATION_PLAN.md`, `MIGRATION_VALIDATION_REPORT.md`. Reprendre CURRENT_TASK, sinon NEXT_TASK.
> Environnement : `./setup.sh --no-tests` (venv isolé ; le `cryptography` système de l'image cloud est
> cassé, ne PAS lancer pytest avec le Python système), puis exporter les secrets de TEST :
> `export MIKA_JWT_SECRET=test-jwt-secret-not-for-prod-0123456789 MIKA_PSEUDO_SECRET=test-pseudo-secret-not-for-prod-0123456789`.
> Avant chaque commit : `git add -A && python tools/secret_scan.py && ruff check . && python -m pytest -q`
> (le scanner renvoie 0 même s'il détecte : LIRE sa sortie).
> `tools.mutation_check` mute une COPIE jetable (on peut lancer pytest en parallèle) ;
> `--seulement a,b` rejoue un sous-ensemble. Ne jamais `pkill -f` un motif présent dans sa propre commande.

SESSION: 3 (2026-09-26)
BRANCH: cloud/mikamike-session3-20260926 (miroir : claude/elegant-cray-y17l2b)
BASE_BRANCH: cloud/mikamike-session2-20260926 (PR #4)
PR: https://github.com/Mike-teib/mikamike-backend/pull/5 (draft, empilée : merger #3 puis #4 puis #5 — jamais sans Mike)
LAST_COMPLETED_TASK: lots 1–11 (revue PR #4, R6, R7, front auth, migrations, API Mika, harnais d'import,
                     perf, sécurité, CI, rapports)
CURRENT_TASK: aucune — PR #5 en revue
NEXT_TASK: R1/R2 dès que Mike fournit les artefacts : remplacer `generer_lot` par le lot réel et exiger
           `executer_pipeline(<lot réel>, <sha épinglé>, autoriser_fictif=False).statut == "VALIDATED"`
           (IMPORT_TEST_HARNESS_REPORT.md §6). Sinon : D8 (création des liens) puis passage front en enforce.
TEST_STATUS: 4017/4017 PASS ; ruff 0 ; bandit 0 ; pip-audit 0 ; secrets arbre 0 ; MUTATION_STATUS
LAST_COMMIT: voir `git log -1`

KNOWN_BLOCKERS:
  - R1/R2 : artefacts réels (BO/Éduscol, C02, C02-6, C02-6.1, M01, Extraction V3, manifests) ABSENTS ⇒
    0 notion PROVEN réelle, catalogue du tuteur vide (start ⇒ 404) — voulu. Le pipeline est prêt et
    éprouvé sur lots synthétiques.
  - Passage en `enforce` : bloqué par D8 (aucune route de création de liens compte ↔ élève).

FILES_IN_PROGRESS: aucun

DECISIONS_REQUIRED (Mike) :
  - D1 Rotation des secrets si un env a tourné sans eux · D3 e-mail dans le jeton de compte, `prenom` élève
  - D5 Appliquer (ou non) les constats R6 au catalogue historique (« 0.5 » accepté pour « Simplifie 4/8 »,
    « 5*x » et « 3 = x » refusés) — outil prêt : `python -m tools.audit_equivalence`
  - D6 NIVEAUX_PAR_MATIERE · D7 contrat `mika-tutorat/1` avec le front
  - D8 Création des liens compte ↔ élève (BLOQUANT pour enforce) · D9 effacement par l'élève
  - D10 reconnect d'une séance expirée · D11 révocation par `jti` · D12 date de fin du mode `off`
  - D13 rétention des tutorats · D14 compréhension ratée ⇒ réussite non comptée (appliqué, à confirmer)
  - D15 `session_id` : clé composite ou identifiant serveur (S3-13)

DEPLOIEMENT (quand autorisé, rien n'a été déployé) :
  1. sauvegarde des bases ; 2. `python -m tools.db stamp-existant mika|billing` (bases historiques)
  puis `python -m tools.db upgrade` (UNE seule tâche, jamais sur plusieurs réplicas) ;
  3. `MIKA_DB_INIT=check`, `MIKA_ENV=production`, `MIKA_AUTH_MODE=enforce`, `MIKA_RATE_LIMIT=on`,
  `MIKA_PROXY_HOPS=<nb de proxys>` ; 4. rotation des secrets si D1 ; 5. front conforme à
  FRONT_AUTH_INTEGRATION.md.

REMAINING_BACKLOG: CLOUD_BACKLOG_MIKAMAIKE.md (R1, R2, R3b, R5, R6-application, R8–R10, R12–R18)

## Rapport final session 3
```
BRANCH: cloud/mikamike-session3-20260926
COMMITS: COMMITS_COUNT (depuis db03ff4)
FILES_CHANGED: FILES_COUNT

REVIEW_FINDINGS_TOTAL: 16   (CLOUD_REVIEW_SESSION2.md ; 14 corrigés, 2 documentés)
P0: 0
P1: 4   (S3-01 jeton élève après effacement RGPD, S3-02 URL Alembic %, S3-03 migration interrompue, S3-15 lot fictif publiable)
P2: 12

TESTS_TOTAL: 4017
TESTS_PASS: 4017
TESTS_FAIL: 0
TESTS_ERROR: 0

MUTATIONS_TOTAL: MUT_TOTAL
MUTATIONS_KILLED: MUT_KILLED

AUTH_STATUS: enforce par défaut ; jeton élève révoqué dès perte du lien/compte (cid) ; sub validé ; 52 tests sécurité en plus
RATE_LIMIT_STATUS: R7 livré (connexion, inscription, jetons élève, jetons invalides) ; anti-DoS victime prouvé ; par processus
FRONT_AUTH_PREP: FRONT_AUTH_INTEGRATION.md prêt ; passage enforce bloqué par D8 (création des liens)
MIKA_API_STATUS: contrat audité (39 tests, concurrence par threads) ; 3 défauts corrigés (S3-04/05/06) ; contenu réel absent (R1)
MIGRATION_STATUS: 23 tests (neuve, historique, stamp, downgrade, version incorrecte, interruption) ; 2 P1 corrigés
IMPORT_HARNESS_STATUS: pipeline synthétique complet, 12 défauts injectés, reprise, rollback, perf linéaire ; aucun artefact réel
SECURITY_STATUS: bandit 0, pip-audit 0, secrets 0 ; D1/D3/D15 ouvertes

PRODUCTION_TOUCHED: NO
PAID_API_CALLS: 0

READY_FOR_REVIEW: YES (revue humaine de la PR #5 ; merge après #3 et #4)

REMAINING_BLOCKERS: artefacts réels (R1/R2), D8 (liens compte ↔ élève) pour enforce, D5 (application R6), D12 (date enforce)
```
