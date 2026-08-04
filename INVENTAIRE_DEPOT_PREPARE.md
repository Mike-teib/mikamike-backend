# INVENTAIRE_DEPOT_PREPARE — MikaMike backend (dépôt local préparé)

- **Destination** : `D:\DEV\PROJETS\MIKAMIKE_BACKEND_REPO\`
- **Futur dépôt distant (NON créé, NON poussé)** : `Mike-teib/mikamike-backend`
- **Date** : 2026-08-04 (UTC)
- **Empreintes** : `SHA256_DEPOT_PREPARE.txt` (49 fichiers backend).
- **Intégrité** : 49/49 fichiers **identiques** à la source (SHA-256 égaux), seul `.gitignore` a été réécrit (version complète).

## Structure minimale requise — CONFORME
| Requis | Présent |
|---|---|
| `main.py` | ✅ |
| `app/api/v1/` | ✅ (mikamike, escalier, parcours, memory, session, rgpd, security) |
| `paiement_comptes/` | ✅ |
| `tests_mika/` | ✅ (conftest + 9 tests) |
| `tests_paiement/` | ✅ (conftest + 1 suite) |
| `requirements.txt` | ✅ |

## Contenu racine
```
app/                     paiement_comptes/        tests_mika/        tests_paiement/
.gitignore               main.py                  README.md          requirements.txt
A_CABLER_ESCALIER.md     A_CABLER_RGPD.md         A_CABLER_SECU.md
SHA256_SOURCE.txt        SHA256_DEPOT_PREPARE.txt
INVENTAIRE_SOURCE.md     INVENTAIRE_DEPOT_PREPARE.md
RAPPORT_SECRETS_EXCLUS.md  RAPPORT_TESTS_AVANT_JULES.md  LISTE_FICHIERS_NON_COPIES.md
```

## Propreté
- **0** base `.db`, **0** `.pyc`, **0** `__pycache__`, **0** `.pytest_cache` dans le dépôt.
- **0** secret / `.env` / `node_modules`.
- **0** référence « mojosignal ».
- Exclusivement backend **MikaMike**.

> Note : les 7 fichiers d'audit (`SHA256_*`, `INVENTAIRE_*`, `RAPPORT_*`, `LISTE_*`) documentent la préparation ; ils sont volontairement **hors** du périmètre hashé de `SHA256_DEPOT_PREPARE.txt` (qui ne couvre que le code/docs backend, pour reproductibilité).
