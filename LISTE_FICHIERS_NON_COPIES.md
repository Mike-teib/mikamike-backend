# LISTE_FICHIERS_NON_COPIES — MikaMike backend

Fichiers présents dans la **source** (`G:\Mon Drive\MikaMike\APP_MIKAMIKE\backend\`) **volontairement NON copiés** vers `D:\DEV\PROJETS\MIKAMIKE_BACKEND_REPO\`.

## 1. Bases de données (données locales / réelles) — exclues
| Fichier | Taille | Motif | Réversible |
|---|---|---|---|
| `billing.db` | 36 864 o | données SQLite (comptes/abonnements test) | source intacte |
| `mikamike.db` | 20 480 o | données SQLite runtime | source intacte |
| `mikamike_backend.db` | 20 480 o | données SQLite runtime | source intacte |

## 2. Caches / bytecode — exclus
- 14 dossiers `__pycache__/` (tous niveaux) — bytecode `*.pyc` régénérable.
- `.pytest_cache/` (+ `v/cache/lastfailed`, `nodeids`, etc.) — cache de tests.
- `__pycache__/main.cpython-314.pyc` (racine) et tous les `*.cpython-314*.pyc`.

## 3. Autres catégories exclues par règle
- `.env` / secrets : **aucun présent** dans la source (rien à exclure).
- `node_modules/` : **absent**.
- Fichiers MojoSignal : **absents** (0 occurrence).
- Rapports périmés : **aucun** identifié dans la source (les `A_CABLER_*.md` sont des docs de câblage à jour → **copiés**).

## Méthode d'exclusion
Copie via `robocopy /E /XD __pycache__ .pytest_cache /XF *.db *.pyc *.env *.sqlite *.sqlite3`.
Contrôle post-copie : 0 fuite de `.db`/`.pyc`/cache dans le dépôt.

## Réversibilité
**La source n'a été ni modifiée ni supprimée.** Toutes les exclusions sont de simples non-copies ; les originaux restent dans `APP_MIKAMIKE\backend\`. Les bases exclues sont de toute façon régénérées à l'exécution (tables créées à l'import).
