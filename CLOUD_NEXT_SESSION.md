# CLOUD_NEXT_SESSION — Checkpoint permanent

> Protocole de reprise : lire ce fichier, puis `CLOUD_AUDIT_MIKAMAIKE.md`,
> `CLOUD_BACKLOG_MIKAMAIKE.md`, `CLOUD_TEST_REPORT.md`. Reprendre CURRENT_TASK, sinon NEXT_TASK.
> Environnement : `./setup.sh` (venv isolé ; le `cryptography` système de l'image cloud est cassé).

LAST_COMPLETED_TASK: Lot 4 — math guards (SymPy sécurisé), vérificateurs PC/SVT/techno/ES, exercices, quiz, dédup
CURRENT_TASK: Lot 5 — pédagogie Mika (tuteur 8 temps) + récurrence (app/curriculum/pedagogie)
NEXT_TASK: Lot 6 — audit dédup global, outil backlog, importeurs d'artefacts (checkpoint/manifest), perf, docs finales
BRANCH: cloud/mikamike-autonomous-20260926 (miroir poussé aussi sur claude/funny-thompson-igpvnl)
LAST_COMMIT: (voir `git log -1`)
TEST_STATUS: 283/283 PASS (baseline 62) ; CI GitHub verte sur tous les commits poussés
KNOWN_BLOCKERS:
  - Artefacts du chantier local (registre notions, C02, Extraction V3, M01) absents du dépôt → import BLOCKED (outils prêts, données absentes)
  - Aucune source officielle (BO/Eduscol) dans le dépôt → toutes les notions NOT_EVIDENCED
FILES_IN_PROGRESS: aucun
DECISIONS_REQUIRED:
  - D1 Rotation des secrets si un env a tourné sans MIKA_*_SECRET (littéral faible public dans l'historique)
  - D2 Authentifier les routes élève/RGPD (change le contrat front)
  - D3 Retirer l'e-mail du JWT ; minimisation du `prenom` élève
  - D4 Réécriture d'historique Git (non recommandée ; rotation suffit)
REMAINING_BACKLOG: lots 5 → 6 (cf. CLOUD_BACKLOG_MIKAMAIKE.md) ; PR https://github.com/Mike-teib/mikamike-backend/pull/3
