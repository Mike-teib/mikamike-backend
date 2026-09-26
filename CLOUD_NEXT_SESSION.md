# CLOUD_NEXT_SESSION — Checkpoint permanent

> Protocole de reprise : lire ce fichier, puis `CLOUD_AUDIT_MIKAMAIKE.md`,
> `CLOUD_BACKLOG_MIKAMAIKE.md`, `CLOUD_TEST_REPORT.md`. Reprendre CURRENT_TASK, sinon NEXT_TASK.
> Environnement : `./setup.sh` (venv isolé ; le `cryptography` système de l'image cloud est cassé,
> ne PAS lancer pytest avec le Python système).
> Avant chaque commit : `git add -A && python tools/secret_scan.py && python -m pytest -q`
> (le scanner ne voit que les fichiers suivis : un fichier neuf doit être ajouté avant le scan).

LAST_COMPLETED_TASK: Lot 6 — backlog, audit dédup, import strict, perf, mutation 18/18, CI, docs
CURRENT_TASK: aucune (backlog réalisable dans ce dépôt traité) — PR en revue
NEXT_TASK: R4 câbler TuteurMika dans l'API dès que le contrat front est décidé (D7) ; sinon R11 (migration + index)
BRANCH: cloud/mikamike-autonomous-20260926 (miroir poussé sur claude/funny-thompson-igpvnl)
PR: https://github.com/Mike-teib/mikamike-backend/pull/3 (draft, ne pas merger sans Mike)
LAST_COMMIT: voir `git log -1` (docs finales)
TEST_STATUS: 3462/3462 PASS (baseline 62/62) ; ruff 0 ; bandit 0 ; pip-audit 0 ; mutants 18/18 tués
KNOWN_BLOCKERS:
  - R1/R2 Artefacts du chantier local (sources BO/Éduscol, registre notions, mappings, C02, C02-6.1,
    Extraction V3, M01 Maths Cycle 3) ABSENTS du dépôt → import BLOCKED (outil prêt : app/curriculum/importers.py,
    format dans CLOUD_DATA_MODEL.md)
  - Conséquence : 42 notions existantes NOT_EVIDENCED, 0 génération autorisée (voulu)
FILES_IN_PROGRESS: aucun
DECISIONS_REQUIRED:
  - D1 Rotation MIKA_PSEUDO_SECRET / MIKA_JWT_SECRET si un env a tourné sans eux (littéral faible public dans c01d9ba)
  - D2 Authentifier les routes élève/RGPD (aujourd'hui : quiconque connaît un pseudo-id peut exporter/effacer)
  - D3 Retirer l'e-mail du JWT ; minimisation du `prenom` élève ; D3bis rate-limiting connexion
  - D4 Réécriture d'historique Git : non recommandée (rotation suffit)
  - D5 Activer la correction symbolique (SymPy) sur le catalogue historique (change la notation)
  - D6 Confirmer NIVEAUX_PAR_MATIERE contre les textes officiels
  - D7 Contrat API du tuteur Mika (endpoints, stockage de l'état de tutorat)
REMAINING_BACKLOG: R1–R12 (CLOUD_BACKLOG_MIKAMAIKE.md) ; tous BLOCKED par données/décisions sauf R4 (après D7), R11
