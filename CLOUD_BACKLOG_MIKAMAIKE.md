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

## Session cloud 2 (branche `cloud/mikamike-session2-20260926`, PR #4)
| Lot | Statut | Où |
|---|---|---|
| Revue contradictoire PR #3 (28 findings, 2 P0) | ✅ | CLOUD_REVIEW_SESSION1.md, tests_cloud/test_review_session1.py |
| Authentification élève / parent / RGPD | ✅ (création des liens : D8) | AUTH_CONTRACT.md, app/core/auth.py |
| Migrations DB (Alembic), plus de create_all à l'import | ✅ | CLOUD_DB_MIGRATION_PLAN.md, migrations/, tools/db.py |
| API tuteur Mika `mika-tutorat/1` branchée | ✅ (contenu réel : après import) | MIKA_API_CONTRACT.md, app/api/v1/tutorat/ |
| Contrat d'import v2 (C02, C02-6, C02-6.1, M01, Extraction V3, PDF, manifests SHA256) | ✅ outils ; ⛔ données absentes | IMPORT_CONTRACT.md, importers.py, depot.py |
| Intégrité croisée (verrou de génération) | ✅ | app/curriculum/integrite.py |
| Backlog réel hiérarchique | ✅ | backlog.py (`par_hierarchie`), tools/rapports.py |
| Performance (SQL, flux, index, cache) | ✅ | tests_cloud/test_performance.py |
| Tests d'attaque | ✅ | tests_cloud/test_attaques.py (+ auth, import) |
| CI (mutation + migrations) | ✅ | .github/workflows/ci.yml |

## Backlog restant (priorisé, après session 2)
| # | Tâche | Statut | Bloquant |
|---|---|---|---|
| R1 | Importer les sources officielles (BO/Éduscol) + registre notions réel | ⛔ | artefacts du chantier local absents du dépôt (procédure prête : IMPORT_CONTRACT.md §7) |
| R2 | Adaptateurs typés C02 / C02-6.1 / Extraction V3 / M01 | ⛔ | échantillons réels nécessaires ; en attendant : rôle + type `opaque` |
| R3 | ~~Authentifier routes élève / RGPD~~ | ✅ S2 | — |
| R3b | Parcours produit de création des liens compte ↔ élève (D8) + passage du front en `enforce` (D12) | ⛔ | décision produit / front |
| R4 | ~~Câbler TuteurMika dans l'API~~ | ✅ S2 | contrat à valider avec le front (D7) |
| R5 | Unifier les ID de compétences (learning engine ↔ notions) — le tuteur lit les prérequis par ID de notion | ⬜ | après R1 |
| R6 | Correction du catalogue historique via SymPy — opt-in par exercice | ⬜ D5 | change la notation élève |
| R7 | Rate-limiting `/comptes/connexion` et `/auth/eleve/jeton` | ⬜ D3bis | choix infra |
| R8 | Retirer l'e-mail du JWT de compte ; minimiser `prenom` élève | ⛔ D3 | décision produit |
| R9 | Confirmer `NIVEAUX_PAR_MATIERE` contre les textes officiels | ⛔ D6 | source officielle |
| R10 | Rédiger les `PlanGuidage` (humain) des notions PROVEN, avec clé de compréhension | ⛔ | après R1 |
| R11 | ~~Index SQL (eleve_hmac, competence, ts)~~ | ✅ S2 | migration m0002 |
| R12 | Supprimer / régénérer `junit_pre_jules.xml` | ⬜ | décision Mike |
| R13 | Révocation des jetons élève (D11), rétention des tutorats (D13), reconnect d'une séance expirée (D10) | ⬜ | décisions produit |
| R14 | Retirer la compatibilité des jetons de compte sans `typ` (7 jours après déploiement) | ⬜ | déploiement |
