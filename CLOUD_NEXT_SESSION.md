# CLOUD_NEXT_SESSION — Checkpoint permanent

## SESSION 5 — branche `cloud/mikamike-release-candidate-1`, PR #7 (draft, base = PR #6)
LAST_COMPLETED: lots 1, 3–16 (pile auditée ; moteur sur historique branché ; frontend-contract/ ;
  E2E complet enforce ; SMTP ; rétention exploitable ; manifeste des artefacts ; dataset synthétique ;
  matrice de migrations ; perf ; audit BOLA + S5-01 ; garde de publication ; CI rc-gate ; runbooks).
CURRENT: aucune — PR #7 en revue (CI surveillée).
NEXT: Mike — (1) déployer le staging selon STAGING_DEPLOYMENT_RUNBOOK.md ; (2) fournir les artefacts
  (ARTIFACTS_REQUIRED_MANIFEST.json) ; (3) trancher les 8 écarts d'API (FRONT_IMPLEMENTATION_PACK.md) ;
  (4) choisir le fournisseur de courriel ; (5) DPO_RETENTION_DECISION.md ; (6) fusionner #3→#7.
VERDICTS: READY_FOR_STAGING = YES (sous réserve CI rc-gate verte + secrets/hôte staging) ;
  READY_FOR_PRODUCTION = NO (RELEASE_CANDIDATE.md §14).
MIGRATIONS: inchangées (mika m0003_tutorat ; billing b0004_verif_email_revocation).
DECISIONS (conservatrices, réversibles) : moteur historique par défaut, `legacy` en retour arrière ;
  aucune route de quiz inventée ; écarts d'API documentés, non corrigés (changement de contrat) ;
  données utilisateurs synthétiques séparées du lot de contenu ; SQLite / une instance.
PR: https://github.com/Mike-teib/mikamike-backend/pull/7 — NE PAS MERGER sans Mike.

## SESSION 4 — branche `cloud/mikamike-session4-autonomous`, PR #6 (draft, empilée sur #5)
LAST_COMPLETED: R19 + révocation + cycle de vie du compte ; contrat front exécutable ; observabilité ;
  garde de publication ; import en deux temps ; chapitrage prouvé ; qualité de texte ; récurrence ;
  math guard ; physique-chimie ; SVT (raisonnement structuré) ; techno (S4-02) ; provenance ES ;
  quiz (4 types) ; progression sur historique ; dashboard parent fermé ; rétention RGPD ;
  sécurité (S4-03..06) ; migrations double/concurrentes ; perf multi-élèves ; RELEASE_CANDIDATE.md.
CURRENT: aucune — PR #6 en revue (CI surveillée).
NEXT: artefacts réels (R1/R2, R21) ; décisions DPO (R24) ; front (R20, R22, R25) ; fusion par Mike.
TESTS: 4065 → 4531 (0 échec). MUTATIONS: tous les mutants ciblés tués.
SECURITY: P0 0 · P1 0 · P2 infra (R17, R18). MIGRATIONS: mika m0003_tutorat ; billing b0004_verif_email_revocation.
BLOCKERS: WAITING_FOR_ARTIFACT (C02, C02-6, C02-6.1, M01, Extraction V3, PDF) ; fournisseur de courriel réel ;
  front + E2E front (D12) ; validation DPO des durées de rétention.
DECISIONS (conservatrices, réversibles) : rétention en simulation par défaut ; LE historique inchangé
  (nouveau modèle à part) ; cycles 2 / techno 4 non modélisés ; ordre de grandeur ambigu ⇒ revue ;
  négation ⇒ revue (jamais VALID) ; 422 sans écho ; champs inconnus refusés.
PR: https://github.com/Mike-teib/mikamike-backend/pull/6 — NE PAS MERGER sans Mike.
CI_STATUS: vert jusqu'à 81e83b3 ; têtes suivantes : voir la PR.


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
           (IMPORT_TEST_HARNESS_REPORT.md §6). Côté front : écrans D8 (inviter / saisir le code),
           `POST /session/nouvelle`, puis tests E2E front (condition D12).
TEST_STATUS: 4065/4065 PASS ; ruff 0 ; bandit 0 ; pip-audit 0 ; secrets arbre 0 ; mutation 73/73 complète (local) + 9/9 mutants des décisions
LAST_COMMIT: voir `git log -1`

KNOWN_BLOCKERS:
  - R1/R2 : artefacts réels (BO/Éduscol, C02, C02-6, C02-6.1, M01, Extraction V3, manifests) ABSENTS ⇒
    0 notion PROVEN réelle, catalogue du tuteur vide (start ⇒ 404) — voulu. Le pipeline est prêt et
    éprouvé sur lots synthétiques.
  - Passage en `enforce` (D12) : backend prêt (D8 livré, E2E backend vert) ; attend le front conforme
    et ses tests E2E verts. Aucun déploiement de production avant.

FILES_IN_PROGRESS: aucun

DECISIONS_PRISES (Mike, session 3) — toutes mises en œuvre :
  - D8  lien parent ↔ élève par invitation à code unique, expirable, non devinable, validée par le parent
  - D5  correction symbolique : équivalences démontrées seulement ; ambigu ⇒ NEEDS_HUMAN_REVIEW
  - D12 enforce seulement quand front + flux parent/enfant + tests E2E sont verts
  - D14 compréhension finale ratée ⇒ exercice non compté réussi
  - D15 session_id généré par le serveur, cryptographiquement aléatoire

DECISIONS_REQUIRED (Mike) :
  - D1 Rotation des secrets si un env a tourné sans eux · D3 e-mail dans le jeton de compte, `prenom` élève
  - D6 NIVEAUX_PAR_MATIERE · D7 contrat `mika-tutorat/1` avec le front
  - D9 effacement par l'élève · D10 reconnect d'une séance expirée · D11 révocation par `jti`
  - D13 rétention des tutorats · R19 vérification de l'e-mail parent avant acceptation d'invitation

DEPLOIEMENT (quand autorisé, rien n'a été déployé) :
  1. sauvegarde des bases ; 2. `python -m tools.db stamp-existant mika|billing` (bases historiques)
  puis `python -m tools.db upgrade` (UNE seule tâche, jamais sur plusieurs réplicas) ;
  3. `MIKA_DB_INIT=check`, `MIKA_ENV=production`, `MIKA_AUTH_MODE=enforce`, `MIKA_RATE_LIMIT=on`,
  `MIKA_PROXY_HOPS=<nb de proxys>` ; 4. rotation des secrets si D1 ; 5. front conforme à
  FRONT_AUTH_INTEGRATION.md.

REMAINING_BACKLOG: CLOUD_BACKLOG_MIKAMAIKE.md (R1, R2, R5, R8–R10, R12–R14, R16–R20)

## Rapport final session 3
```
BRANCH: cloud/mikamike-session3-20260926
COMMITS: 10 (depuis db03ff4)
FILES_CHANGED: 52

REVIEW_FINDINGS_TOTAL: 16   (CLOUD_REVIEW_SESSION2.md ; 14 corrigés, 2 documentés)
P0: 0
P1: 4   (S3-01 jeton élève après effacement RGPD, S3-02 URL Alembic %, S3-03 migration interrompue, S3-15 lot fictif publiable)
P2: 12

TESTS_TOTAL: 4065
TESTS_PASS: 4065
TESTS_FAIL: 0
TESTS_ERROR: 0

MUTATIONS_TOTAL: 82 (39 sessions 1–2 + 34 session 3 + 9 décisions D5/D8/D15)
MUTATIONS_KILLED: 82 (73 en exécution complète + 9 vérifiés individuellement)

AUTH_STATUS: enforce par défaut ; jeton élève révoqué dès perte du lien/compte (cid) ; sub validé ; 52 tests sécurité en plus
RATE_LIMIT_STATUS: R7 livré (connexion, inscription, jetons élève, jetons invalides) ; anti-DoS victime prouvé ; par processus
FRONT_AUTH_PREP: FRONT_AUTH_INTEGRATION.md prêt (invitations D8, session serveur D15) ; passage enforce selon D12 (création des liens)
MIKA_API_STATUS: contrat audité (39 tests, concurrence par threads) ; 3 défauts corrigés (S3-04/05/06) ; contenu réel absent (R1)
MIGRATION_STATUS: 23 tests (neuve, historique, stamp, downgrade, version incorrecte, interruption) ; 2 P1 corrigés
IMPORT_HARNESS_STATUS: pipeline synthétique complet, 12 défauts injectés, reprise, rollback, perf linéaire ; aucun artefact réel
SECURITY_STATUS: bandit 0, pip-audit 0, secrets 0 ; D1/D3/D15 ouvertes

PRODUCTION_TOUCHED: NO
PAID_API_CALLS: 0

READY_FOR_REVIEW: YES (revue humaine de la PR #5 ; merge après #3 et #4)

REMAINING_BLOCKERS: artefacts réels (R1/R2) ; front conforme + tests E2E front (condition D12)
```
