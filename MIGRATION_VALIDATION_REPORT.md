# MIGRATION_VALIDATION_REPORT — Validation des migrations Alembic (session cloud 3)

Périmètre : bases « mika » (m0001 → m0003) et « billing » (b0001 → b0002), SQLite jetables, en
sous-processus. **Aucune base réelle touchée.** Tests : `tests_cloud/test_migrations.py` (session 2,
11 tests) + `tests_cloud/test_migrations_validation.py` (session 3, 12 tests) + S3-02/S3-03 dans
`tests_cloud/test_review_session2.py`.

## Défauts trouvés et corrigés (CLOUD_REVIEW_SESSION2.md)
| # | Défaut | Correctif |
|---|---|---|
| S3-02 (P1) | URL contenant `%` (mot de passe encodé) ⇒ toutes les commandes et le démarrage plantaient | `%` doublé dans la config Alembic |
| S3-03 (P1) | Migration interrompue sur SQLite : tables créées sans version, relance impossible (`table already exists`) | DDL réellement transactionnel (`ddl_transactionnel_sqlite`) : une révision est appliquée entièrement ou pas du tout |
| — (P2) | `tools.db` : version inconnue ⇒ trace Python | message `erreur: …` et code 1 |

## Matrice de validation
| Scénario | Résultat | Test |
|---|---|---|
| Base neuve : `status` (1) → `upgrade` → `status` (0) ; relance idempotente | ✅ | `test_base_neuve_cli_upgrade_status` |
| Upgrade pas à pas m0001 → m0002 → m0003 | ✅ | `test_upgrade_pas_a_pas_chaque_revision` |
| Migrations ≡ modèles (`compare_metadata` vide) | ✅ | `test_upgrade_head_egal_aux_modeles` |
| Base historique (ancien `create_all`) + données → `stamp-existant` → `upgrade` : **empreinte SHA-256 du contenu identique** | ✅ | `test_base_historique_adoptee_donnees_preservees` |
| `stamp-existant` sur base déjà versionnée / vide / incomplète : refus | ✅ | idem + `test_adoption_refusee_si_base_non_conforme` |
| Downgrade m0003 → m0001 et b0002 → b0001 puis upgrade : données des tables conservées identiques | ✅ | `test_downgrade_puis_upgrade_preserve_les_donnees_conservees` |
| Downgrade qui retire une table : ses données sont perdues (documenté, restaurer la sauvegarde) | ✅ | `test_downgrade_documente_la_perte_des_tables_retirees` |
| Version incorrecte (inconnue ou « future ») : `status` = 1, `upgrade` = erreur propre, démarrage refusé | ✅ | `test_version_incorrecte_refus_propre` (×2) |
| Migration interrompue (3 points de coupure, dont m0001 sur base vide et b0002) : version inchangée, aucune table partielle, données préservées, reprise jusqu'à head | ✅ | `test_migration_interrompue_rollback_et_reprise` (×3) |
| Downgrade interrompu : rien de défait à moitié | ✅ | `test_downgrade_interrompu_atomique` |
| Import de l'application : aucune table créée | ✅ | `test_import_de_l_application_ne_cree_aucune_table` |
| Démarrage `check` refusé sans schéma, `migrate` puis `check` accepté, mode invalide refusé | ✅ | tests session 2 |
| SQL hors ligne (revue DBA) sans créer la base | ✅ | `test_sql_hors_ligne_pour_revue` |

Mutants dédiés (tous tués) : `url_alembic_non_echappee`, `ddl_sqlite_non_transactionnel`,
`migration_non_atomique_validation`, `cli_db_trace_sur_erreur`.

## Limites
- PostgreSQL non disponible dans l'environnement cloud : DDL transactionnel natif côté PostgreSQL ;
  valider `python -m tools.db sql <cible>` avec le DBA avant toute application.
- Un downgrade qui supprime une table supprime ses données : **sauvegarde obligatoire** avant
  toute opération (CLOUD_DB_MIGRATION_PLAN.md §5–6).
- Plusieurs processus appliquant `upgrade` en même temps : non protégé (verrou applicatif absent) ;
  en production, appliquer les migrations par une seule tâche de déploiement, jamais `MIKA_DB_INIT=migrate`
  sur plusieurs réplicas.

## Session 5 — release candidate 1 (`tests_cloud/test_migrations_rc1.py`)

| scénario | résultat |
|---|---|
| **matrice de toutes les têtes** : 4 départs mika × 5 départs billing (de `base` à head), montés ensemble à head, puis démarrage `MIKA_DB_INIT=check` et parcours réel (inscription, vérification, soumission, dashboard) | 20/20 : schéma = modèles, données de départ conservées, parcours 201/200/200/200 |
| rollback du runbook : base remplie **par l'API** à head → `downgrade billing b0003_invitations_lien` → `upgrade` | comptes, abonnements, tentatives identiques (empreintes) ; perte documentée : `verifications_email`, `jeton_version` remis à 0 |
| coupure dans b0004 en partant de b0002 | atomicité **par révision** : b0003 reste validée, b0004 annulée sans table partielle, données intactes ; relance ⇒ head |

Conséquence runbook : après un rollback vers b0003, les jetons émis avant restent valables jusqu'à
expiration (la révocation par version est perdue) ; si une révocation était en cours, faire tourner
`MIKA_JWT_SECRET` (ROLLBACK_RUNBOOK.md).
