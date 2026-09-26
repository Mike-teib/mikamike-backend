# CLOUD_NEXT_SESSION — Checkpoint permanent

> Protocole de reprise : lire ce fichier, puis `CLOUD_AUDIT_MIKAMAIKE.md`,
> `CLOUD_BACKLOG_MIKAMAIKE.md`, `CLOUD_TEST_REPORT.md`. Reprendre CURRENT_TASK, sinon NEXT_TASK.
> Environnement : `./setup.sh` (venv isolé ; le `cryptography` système de l'image cloud est cassé).

LAST_COMPLETED_TASK: Lot 1 — audit, rapport sécurité, setup.sh, pyproject (ruff/pytest), nettoyage imports
CURRENT_TASK: Lot 2 — corrections bugs B1–B10 + durcissement API + CVE dépendances
NEXT_TASK: Lot 3 — modèle canonique programmes + provenance + validateurs (app/curriculum)
BRANCH: cloud/mikamike-autonomous-20260926 (miroir poussé aussi sur claude/funny-thompson-igpvnl)
LAST_COMMIT: (voir `git log -1`)
TEST_STATUS: 62/62 PASS (baseline)
KNOWN_BLOCKERS:
  - Artefacts du chantier local (registre notions, C02, Extraction V3, M01) absents du dépôt → import BLOCKED (outils prêts, données absentes)
  - Aucune source officielle (BO/Eduscol) dans le dépôt → toutes les notions NOT_EVIDENCED
FILES_IN_PROGRESS: aucun
DECISIONS_REQUIRED:
  - D1 Rotation des secrets si un env a tourné sans MIKA_*_SECRET (littéral faible public dans l'historique)
  - D2 Authentifier les routes élève/RGPD (change le contrat front)
  - D3 Retirer l'e-mail du JWT ; minimisation du `prenom` élève
  - D4 Réécriture d'historique Git (non recommandée ; rotation suffit)
REMAINING_BACKLOG: lots 2 → 6 (cf. CLOUD_BACKLOG_MIKAMAIKE.md)
