# CLOUD_BACKLOG_MIKAMAIKE — Backlog

Légende : ✅ fait (branche cloud) · 🟡 partiel · ⛔ BLOCKED (donnée/secret/décision) · ⬜ à faire

## Chiffres réels (calculés par `python -m tools.rapports`, pas à la main)
Existant du dépôt : **42 notions**, **0 PROVEN**, 42 WAITING_SOURCE, 0 exercice canonique,
0 quiz, 42 notions sans chapitre (orphelines), 5 notions « primaire » non migrables.
⇒ Tant qu'aucune source officielle n'est importée, **aucune génération n'est autorisée**.

## Phases de la mission
| Phase | Statut | Où |
|---|---|---|
| 0 Audit | ✅ | CLOUD_AUDIT_MIKAMAIKE.md |
| 1 Sécurité / RGPD / secrets | ✅ (+ décisions D1–D4) | CLOUD_SECURITY_REPORT.md, tools/secret_scan.py |
| 2 Environnement reproductible | ✅ | setup.sh, requirements-dev.txt, .env.example |
| 3 Baseline + bugs | ✅ 62 → 3462 tests, 10 bugs + 3 | CLOUD_TEST_REPORT.md |
| 4 Modèle canonique | ✅ | app/curriculum/model.py |
| 5 Provenance | ✅ | provenance.py |
| 6 Validateur chapitres/notions | ✅ | structure.py |
| 7 Texte des notions | ✅ | text_quality.py |
| 8 Maths / formules | ✅ | math_guard.py, verifiers/maths.py |
| 9 Exercices | ✅ | exercices.py |
| 10 Quiz | ✅ | quiz.py |
| 11 Vérificateurs | ✅ | verifiers/ |
| 12 Professeur Mika | ✅ moteur ; ⬜ câblage API | pedagogie/tuteur.py |
| 13 Récurrence | ✅ | pedagogie/recurrence.py |
| 14 Physique-Chimie | ✅ | verifiers/physique.py |
| 15 SVT | ✅ | verifiers/svt.py |
| 16 Sciences & technologie | ✅ | verifiers/technologie.py |
| 17 Enseignement scientifique | ✅ | verifiers/enseignement_scientifique.py |
| 18 Déduplication | ✅ | audit.py |
| 19 Backlog canonique | ✅ | backlog.py, tools/rapports.py |
| 20 Import artefacts | 🟡 outils ✅ ; ⛔ données absentes | importers.py |
| 21 API | ✅ durcissement ; ⛔ auth (D2) | app/api/v1/* |
| 22 Performance | ✅ | flux, create_all unique, DFS itératif, benchmark |
| 23 Fiabilité / reprise | ✅ | checkpoint atomique, FAILED explicite, idempotence |
| 24 Mutation / négatifs | ✅ 18/18 | tools/mutation_check.py |
| 25 CI | ✅ | .github/workflows/ci.yml |
| 26 Documentation | ✅ | CLOUD_*.md |

## Backlog restant (priorisé)
| # | Tâche | Statut | Bloquant |
|---|---|---|---|
| R1 | Importer les sources officielles (BO/Éduscol) + registre notions réel | ⛔ | artefacts du chantier local absents du dépôt |
| R2 | Adaptateurs typés C02 / C02-6.1 / Extraction V3 / M01 Maths Cycle 3 | ⛔ | échantillons réels nécessaires (formats non documentés) |
| R3 | Authentifier routes élève / RGPD (`exiger_session_active`) | ⛔ D2 | contrat front |
| R4 | Câbler `TuteurMika` dans l'API (état de tutorat en session) | ⬜ | dépend du contrat front (D7) |
| R5 | Unifier les 2 systèmes d'ID de compétences (learning engine ↔ curriculum) | ⬜ | après R1 |
| R6 | Correction du catalogue historique via SymPy (`x = 3.0`, `6/2`…) — opt-in par exercice | ⬜ D5 | change la notation élève |
| R7 | Rate-limiting `/comptes/connexion` | ⬜ D3bis | choix infra (proxy vs middleware) |
| R8 | Retirer l'e-mail du JWT ; minimiser `prenom` élève | ⛔ D3 | décision produit |
| R9 | Confirmer `NIVEAUX_PAR_MATIERE` contre les textes officiels | ⛔ D6 | source officielle |
| R10 | Rédiger les `PlanGuidage` (humain) des notions PROVEN | ⛔ | après R1 |
| R11 | Index SQL `(eleve_hmac, competence, ts)` via migration | ⬜ | outil de migration (Alembic) à choisir |
| R12 | Supprimer `junit_pre_jules.xml` (nom d'hôte de build) ou le régénérer | ⬜ | décision Mike (fichier de preuve historique) |
