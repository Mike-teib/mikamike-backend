# RAPPORT_SECRETS_EXCLUS — MikaMike backend

- **Date** : 2026-08-04
- **Destination contrôlée** : `D:\DEV\PROJETS\MIKAMIKE_BACKEND_REPO\`
- **Branche** : `fix/pre-jules-security`

> **Périmètre** : le contrôle porte exclusivement sur le dépôt local. La
> configuration réelle du VPS, du staging et de la production n'a pas été
> consultée pendant cette mission.

## 1. Secrets réels dans le dépôt
| Recherche | Résultat |
|---|---|
| Clés Stripe `sk_live` / `sk_test` | **0** |
| Jetons GitHub `ghp_` / `github_pat_` | **0** |
| Clés privées `BEGIN … PRIVATE KEY` | **0** |
| Mots de passe / chaînes de connexion réelles | **0** |
| Données réelles d'élève | **0** |
| Fichiers `.env` / secrets / `*.db` | **0** |

## 2. Correction appliquée (secrets de secours faibles)
Auparavant, un secret de démonstration faible servait de **valeur de secours**
dans `os.getenv(...)` (pseudonymisation HMAC + repli du secret JWT), à travers
~10 emplacements. Ce littéral a été **entièrement retiré du code exécutable**
(vérifié : 0 occurrence). Le repli faible n'existe plus.

- Nouveau module central **`app/core/security_config.py`** : lit et **valide**
  `MIKA_PSEUDO_SECRET` et `MIKA_JWT_SECRET` en **fail-closed** (refus si absent,
  vide, trop court ou générique). Ne journalise ni n'affiche jamais la valeur ;
  ne génère aucun secret. Les deux secrets restent **distincts** (aucun repli de
  l'un sur l'autre).
- Secrets Stripe : plus de valeur par défaut (`os.environ.get("STRIPE_SECRET_KEY")`
  → `None` si non configuré ; la garde renvoie une erreur 500 explicite).

## 3. Variables d'environnement attendues (NOMS uniquement — valeurs `[SECRET MASQUÉ]`)
```
MIKA_PSEUDO_SECRET     MIKA_JWT_SECRET       (obligatoires, fail-closed, distincts)
MIKA_DB_URL            BILLING_DB_URL        (config, défauts SQLite locaux)
MIKA_TOKEN_TTL_H       MIKA_APP_URL          (config non sensible)
STRIPE_SECRET_KEY      STRIPE_WEBHOOK_SECRET  STRIPE_PRICE_ID   (optionnels)
```

## 4. Données réelles exclues (rappel)
`billing.db`, `mikamike.db`, `mikamike_backend.db` — bases SQLite locales/de test,
non copiées, couvertes par `.gitignore` (`*.db`). Détail : `LISTE_FICHIERS_NON_COPIES.md`.

## 5. `.gitignore`
Le motif trop large `*_secret*` (qui ignorait à tort ce rapport) a été **retiré**
et remplacé par des exclusions ciblées (`.env`, `secrets/`, `*.key`, `*.pem`,
`*.p12/pfx`, `credentials*.json`, `service-account*.json`, `*.secret`).

**VERDICT SECRETS (dépôt local) : PROPRE — 0 secret réel, 0 repli faible, comportement fail-closed.**
