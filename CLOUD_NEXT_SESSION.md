# CLOUD_NEXT_SESSION — Checkpoint permanent

> Protocole de reprise : lire ce fichier, puis `CLOUD_REVIEW_SESSION1.md`, `CLOUD_BACKLOG_MIKAMAIKE.md`,
> `CLOUD_TEST_REPORT.md`, `AUTH_CONTRACT.md`, `MIKA_API_CONTRACT.md`, `IMPORT_CONTRACT.md`,
> `CLOUD_DB_MIGRATION_PLAN.md`. Reprendre CURRENT_TASK, sinon NEXT_TASK.
> Environnement : `./setup.sh --no-tests` (venv isolé ; le `cryptography` système de l'image cloud est
> cassé, ne PAS lancer pytest avec le Python système), puis exporter les secrets de TEST :
> `export MIKA_JWT_SECRET=test-jwt-secret-not-for-prod-0123456789 MIKA_PSEUDO_SECRET=test-pseudo-secret-not-for-prod-0123456789`.
> Avant chaque commit : `git add -A && python tools/secret_scan.py && ruff check . && python -m pytest -q`.
> Ne jamais lancer pytest pendant `tools.mutation_check` (il modifie temporairement le code source).

SESSION: 2 (2026-09-26)
BRANCH: cloud/mikamike-session2-20260926 (miroir : claude/compassionate-clarke-k43csf)
BASE_BRANCH: cloud/mikamike-autonomous-20260926 (PR #3, head fb77fb8)
PR: https://github.com/Mike-teib/mikamike-backend/pull/4 (draft, empilée sur la PR #3 — ne pas merger sans Mike ;
    ordre de merge : PR #3 puis PR #4)
LAST_COMPLETED_TASK: Lot F — performance, tests d'attaque, CI (mutation + migrations), documentation
CURRENT_TASK: aucune — PR #4 en revue
NEXT_TASK: R1/R2 dès que Mike fournit les artefacts (procédure : IMPORT_CONTRACT.md §7) ;
           sinon D8/D12 (liens compte↔élève + passage du front en `enforce`) avec le front.
TEST_STATUS: 3767/3767 PASS ; ruff 0 ; bandit 0 ; pip-audit 0 ; secrets arbre 0 ; mutation 39/39 (CI run 21 sur 53794c4)
LAST_COMMIT: voir `git log -1` (checkpoint final session 2)

KNOWN_BLOCKERS:
  - R1/R2 : artefacts du chantier local (BO/Éduscol, registre, mappings, C02, C02-6, C02-6.1, M01,
    Extraction V3, index exercices/quiz, manifests SHA256) ABSENTS ⇒ 0 notion PROVEN, 0 génération,
    catalogue du tuteur vide (start ⇒ 404) — voulu (fail-closed).
  - Le front doit envoyer `Authorization: Bearer …` avant de passer en `MIKA_AUTH_MODE=enforce` (défaut).

FILES_IN_PROGRESS: aucun

DECISIONS_REQUIRED (Mike) :
  - D1 Rotation MIKA_PSEUDO_SECRET / MIKA_JWT_SECRET si un env a tourné sans eux
  - D3 Retirer l'e-mail du JWT de compte ; minimisation du `prenom` élève ; D3bis rate-limiting
  - D5 Correction symbolique du catalogue historique · D6 NIVEAUX_PAR_MATIERE
  - D7 Valider le contrat `mika-tutorat/1` avec le front
  - D8 Parcours de création des liens compte ↔ élève (aucune route publique aujourd'hui)
  - D9 Effacement RGPD demandé par l'élève lui-même (défaut : parent lié uniquement)
  - D10 `reconnect` d'une séance expirée (aujourd'hui : réactivée) · D11 révocation des jetons élève
  - D12 Date de fin du mode `off` côté front · D13 Rétention des tutorats

DEPLOIEMENT (quand autorisé, rien n'a été déployé) :
  1. sauvegarde des bases ; 2. `python -m tools.db stamp-existant mika|billing` (bases historiques)
  puis `python -m tools.db upgrade` ; 3. `MIKA_DB_INIT=check`, `MIKA_ENV=production`,
  `MIKA_AUTH_MODE=enforce` ; 4. rotation des secrets si D1.

REMAINING_BACKLOG: CLOUD_BACKLOG_MIKAMAIKE.md (R1, R2, R3b, R5–R10, R12–R14)
