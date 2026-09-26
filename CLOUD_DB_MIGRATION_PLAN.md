# CLOUD_DB_MIGRATION_PLAN — Migrations de schéma versionnées

Statut : **implémenté et testé sur bases SQLite jetables**. Aucune base réelle n'a été touchée.

## 1. Constat (revue session 2, R2-07)
Le schéma était créé **à l'import** par 5 `create_all` (`mikamike/store.py`, `memory/router.py`,
`session/router.py`, `rgpd/router.py` — qui créait les tables d'autres modules —, et
`paiement_comptes/models_billing.py`). Conséquences : DDL exécuté par un simple `import main`,
aucune version de schéma, et **aucune évolution possible** d'une table existante (`create_all`
n'ajoute ni colonne ni index à une table déjà présente).

## 2. Stratégie retenue
| Élément | Choix |
|---|---|
| Outil | **Alembic 1.20** (standard SQLAlchemy ; épinglé dans `requirements.txt`) |
| Bases | deux historiques de migration indépendants : `migrations/mika/` (MIKA_DB_URL) et `migrations/billing/` (BILLING_DB_URL) |
| Registre des modèles | `app/db/registre.py` (`metadatas(cible)`) — import paresseux, sans secret ni effet de bord |
| SQLite | `render_as_batch=True` (ALTER TABLE par recopie transactionnelle) |
| Démarrage | `MIKA_DB_INIT=check` (**défaut**, fail-closed : refus de démarrer si une base n'est pas à head) · `migrate` (applique au démarrage : dev / conteneur éphémère) · `none` (bases jetables des tests) |
| Tests | les fixtures créent le schéma explicitement (`creer_tables_pour_tests`) ; un test prouve que migrations ≡ modèles |

## 3. Révisions
| Base | Révision | Contenu |
|---|---|---|
| mika | `m0001_baseline` | `mika_tentatives`, `mika_etats`, `mika_memory_schedules`, `mika_session_states` (schéma historique exact) |
| mika | `m0002_index_tentatives` | R11 : index `(eleve_hmac, competence, ts)` — idempotent pour les bases adoptées |
| mika | `m0003_tutorat` | `mika_tutorat_sessions`, `mika_tutorat_requetes` (API tuteur, idempotence) |
| billing | `b0001_baseline` | `comptes`, `abonnements` |
| billing | `b0002_liens_compte_eleve` | autorisation compte ↔ élève (AUTH_CONTRACT.md) |

## 4. Commandes (`tools/db.py`)
```
python -m tools.db status                   # courante / head, code 1 si en retard
python -m tools.db upgrade [mika|billing]   # applique
python -m tools.db downgrade <cible> <rev>  # retour arrière (ex. m0002_index_tentatives, base)
python -m tools.db stamp-existant <cible>   # adopte une base créée par l'ancien code
python -m tools.db sql <cible>              # SQL complet hors ligne, pour revue avant production
```

## 5. Procédure pour une base EXISTANTE (créée par l'ancien `create_all`)
1. **Sauvegarde** de la base (copie du fichier SQLite / dump).
2. `python -m tools.db stamp-existant mika` : vérifie que les 4 tables du baseline existent, refuse
   une base vide, déjà versionnée ou incomplète, puis marque `m0001_baseline` **sans DDL**.
3. `python -m tools.db upgrade mika` : applique m0002 → m0003.
4. Idem `billing`.
5. `python -m tools.db status` doit renvoyer 0 ; démarrer avec `MIKA_DB_INIT=check`.

## 6. Rollback
- Schéma : `python -m tools.db downgrade mika m0002_index_tentatives` (retire les tables de tutorat) ;
  toutes les révisions ont un `downgrade` testé jusqu'à `base`.
- Données : un downgrade qui supprime une table **supprime ses données** : restaurer la sauvegarde
  de l'étape 1 si nécessaire. Aucune migration actuelle ne transforme de données existantes.

## 7. Tests (`tests_cloud/test_migrations.py`, sous-processus + SQLite jetables)
- `import main` ne crée **aucune** table ;
- upgrade head ⇒ `compare_metadata` **vide** (migrations ≡ modèles) pour les deux bases ;
- downgrade jusqu'à `base` puis ré-upgrade ;
- démarrage refusé si schéma absent (`check`), accepté après `migrate` ;
- `MIKA_DB_INIT` invalide refusé ;
- adoption d'une base historique : données conservées, arrivée à head ;
- adoption refusée : base vide / déjà versionnée / incomplète ;
- SQL hors ligne généré sans créer la base.

## 8. Règles pour la suite
- Toute modification de modèle ⇒ nouvelle révision (`alembic revision --autogenerate` via
  `app.db.migrations.config(cible)`), relue à la main ; le test `test_upgrade_head_egal_aux_modeles`
  échoue sinon.
- Toute nouvelle table portant `eleve_hmac` ⇒ ajout à `TABLES_ELEVE` (RGPD) ; le test
  `test_b2_registre_couvre_toute_table_eleve` parcourt désormais **tout** le registre.
- PostgreSQL (si choisi en production) : les migrations sont génériques ; valider `tools.db sql`
  avec le DBA avant application.
