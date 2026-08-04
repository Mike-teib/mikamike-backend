# INVENTAIRE_DEPOT_PREPARE — MikaMike backend (dépôt local préparé)

- **Destination** : `D:\DEV\PROJETS\MIKAMIKE_BACKEND_REPO\`
- **Futur dépôt distant (NON créé, NON poussé)** : `Mike-teib/mikamike-backend`
- **Date** : 2026-08-04 · **Branche** : `fix/pre-jules-security`
- **Empreintes** : `SHA256_DEPOT_PREPARE.txt` (**52** fichiers backend code/docs).

> **Périmètre** : contrôle exclusivement local. La configuration réelle du VPS,
> du staging et de la production n'a pas été consultée pendant cette mission.

## Structure minimale requise — CONFORME
| Requis | Présent |
|---|---|
| `main.py` | ✅ |
| `app/api/v1/` | ✅ (mikamike, escalier, parcours, memory, session, rgpd, security) |
| `app/core/` | ✅ **nouveau** (`security_config.py` fail-closed) |
| `paiement_comptes/` | ✅ |
| `tests_mika/` | ✅ (conftest + 10 fichiers de tests, dont `test_security_config.py`) |
| `tests_paiement/` | ✅ (conftest + 1 suite) |
| `requirements.txt` | ✅ |

## Nouveaux fichiers depuis le commit initial `c01d9ba`
- `app/core/__init__.py`
- `app/core/security_config.py` — lecture/validation centralisée des secrets (fail-closed).
- `tests_mika/test_security_config.py` — 8 tests fail-closed.

## Fichiers modifiés (retrait du repli faible de secret)
`app/api/v1/mikamike/{router.py, learning_engine.py}`, `escalier/orchestrator.py`,
`memory/{router.py, spaced_repetition.py}`, `parcours/router.py`, `rgpd/router.py`,
`session/{router.py, session_manager.py}`, `security/fail_closed.py`,
`paiement_comptes/{router_comptes.py, router_paiement.py}`, `.gitignore`.

## Livrables (racine)
- 7 rapports d'audit : `SHA256_SOURCE.txt`, `SHA256_DEPOT_PREPARE.txt`,
  `INVENTAIRE_SOURCE.md`, `INVENTAIRE_DEPOT_PREPARE.md`, `RAPPORT_SECRETS_EXCLUS.md`,
  `RAPPORT_TESTS_AVANT_JULES.md`, `LISTE_FICHIERS_NON_COPIES.md`.
- 1 preuve de tests : `junit_pre_jules.xml` (vérifiée sans secret).

## Propreté
- **0** `.db` / `.pyc` / `__pycache__` / `.pytest_cache` / `.env` / secret réel / `node_modules`.
- **0** littéral de secret faible et **0** fallback de secret dans le code exécutable.
- Exclusivement backend **MikaMike** (0 « mojosignal » dans le code).

> `SHA256_DEPOT_PREPARE.txt` couvre le code/docs backend uniquement ; les 7 rapports
> d'audit et `junit_pre_jules.xml` en sont exclus (reproductibilité).
