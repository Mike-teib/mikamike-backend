# INVENTAIRE_SOURCE — MikaMike backend

- **Source auditée** : `G:\Mon Drive\MikaMike\APP_MIKAMIKE\backend\`
- **Date audit** : 2026-08-04 (UTC)
- **Empreintes complètes** : voir `SHA256_SOURCE.txt` (49 fichiers code/docs, hash SHA-256).
- **Référence « mojosignal »** dans la source : **AUCUNE** (vérifié par recherche récursive).

## Composition (fichiers canoniques)
| Zone | Fichiers | Rôle |
|---|---|---|
| Racine | `main.py`, `requirements.txt`, `README.md`, `.gitignore`, `A_CABLER_ESCALIER.md`, `A_CABLER_RGPD.md`, `A_CABLER_SECU.md` | app FastAPI + docs |
| `app/api/v1/mikamike/` | `catalogue.py, crud.py, learning_engine.py, router.py, schemas.py, store.py, __init__.py` | tuteur : escalier pédagogique, exercices/parcours/parents |
| `app/api/v1/paiement (paiement_comptes/)` | `crud_billing.py, database.py, models_billing.py, router_comptes.py, router_paiement.py, __init__.py` | comptes self-service + abonnement Stripe |
| `app/api/v1/escalier/` | `orchestrator.py, router.py, __init__.py` | orchestration escalier (autre agent) |
| `app/api/v1/parcours/` | `curriculum_dataset.py, router.py` | référentiel parcours (autre agent) |
| `app/api/v1/memory/` | `spaced_repetition.py, router.py, __init__.py` | mémoire / répétition espacée (autre agent) |
| `app/api/v1/session/` | `session_manager.py, router.py, __init__.py` | sessions (autre agent) |
| `app/api/v1/rgpd/` | `router.py, __init__.py` | RGPD export (autre agent) |
| `app/api/v1/security/` | `fail_closed.py, __init__.py` | garde-fous sécurité (autre agent) |
| `tests_mika/` | `conftest.py` + 9 fichiers de tests | tests mika + modules ci-dessus |
| `tests_paiement/` | `conftest.py`, `test_paiement_suite.py` | tests comptes/paiement |

## Copies concurrentes
**Aucune détectée** : un seul `main.py`, aucun doublon de module source (`.py`). Les seules multiplicités sont des **bases SQLite générées** (`mikamike.db` ET `mikamike_backend.db`) — données, non copiées (cf. `LISTE_FICHIERS_NON_COPIES.md`).

## Éléments exclus de la source (non canoniques)
- 3 bases : `billing.db`, `mikamike.db`, `mikamike_backend.db` (données locales, verrouillées à la lecture).
- 14 dossiers `__pycache__/` (bytecode), `.pytest_cache/`.
Aucun `.env`, secret, `node_modules`, ni fichier MojoSignal présent dans la source.
