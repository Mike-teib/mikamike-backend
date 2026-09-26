# STAGING_DEPLOYMENT_RUNBOOK — MikaMike backend, release candidate 1

Cible : un hôte Linux de **préproduction** (jamais la production), Python 3.11, un reverse proxy TLS
devant `uvicorn`. Aucune commande ne contient de secret : les valeurs viennent du coffre du
déploiement et sont injectées en variables d'environnement. **Jamais de données réelles d'élèves en
staging** (base vide ou dataset synthétique uniquement).

Conventions : `APP=/srv/mikamike/app` (code), `DATA=/srv/mikamike/data` (bases SQLite),
`SV=/srv/mikamike/sauvegardes`, fichier d'environnement `/etc/mikamike/staging.env` (droits 600,
propriétaire du service). `$SHA` = SHA de la release candidate validée en CI (verrou `rc-gate` vert).

## 0. Pré-requis (bloquants)

| # | condition | vérification |
|---|---|---|
| 0.1 | CI verte sur `$SHA` (tests, migrations, contrat front, mutations, sécurité, `rc-gate`) | onglet Actions de la PR |
| 0.2 | secrets **dédiés au staging** dans le coffre : `MIKA_JWT_SECRET`, `MIKA_PSEUDO_SECRET` (≥ 32 caractères, distincts, jamais ceux de la production) | coffre |
| 0.3 | fournisseur de courriel : relais SMTP de **test** (EMAIL_PROVIDER_SETUP.md) ou `MIKA_EMAIL_TRANSPORT=journal` (aucun envoi) | coffre |
| 0.4 | une seule instance applicative (limitation R7 en mémoire par processus, SQLite) | plan d'hébergement |

## 1. Fichier d'environnement (noms seulement ; valeurs depuis le coffre)

```
MIKA_ENV=staging
MIKA_JWT_SECRET=<coffre>
MIKA_PSEUDO_SECRET=<coffre>
MIKA_DB_URL=sqlite:////srv/mikamike/data/mika.db
BILLING_DB_URL=sqlite:////srv/mikamike/data/billing.db
MIKA_DB_INIT=check
MIKA_AUTH_MODE=observe            # enforce seulement après D12 (front + E2E front verts)
MIKA_RATE_LIMIT=on
MIKA_PROXY_HOPS=1                 # nombre de reverse proxys de confiance
MIKA_EMAIL_VERIFICATION=requise
MIKA_EMAIL_TRANSPORT=smtp         # ou journal ; jamais faux hors poste de dev
MIKA_SMTP_HOST=<coffre>  MIKA_SMTP_FROM=<coffre>  MIKA_SMTP_USER=<coffre>  MIKA_SMTP_PASSWORD=<coffre>
MIKA_PROGRESSION_MOTEUR=historique
CORS_ORIGINS=https://<front-staging>
MIKA_APP_URL=https://<front-staging>
```
Référence complète : `.env.example` (durées de rétention : DPO_RETENTION_DECISION.md, non validées).

## 2. Installation du code

```sh
sudo -u mikamike git -C "$APP" fetch origin cloud/mikamike-release-candidate-1
sudo -u mikamike git -C "$APP" checkout --detach "$SHA"
sudo -u mikamike python3.11 -m venv "$APP/.venv"
sudo -u mikamike "$APP/.venv/bin/pip" install --require-virtualenv -r "$APP/requirements.txt"
```

## 3. Sauvegarde (même sur une base vide : prouve la procédure)

```sh
cd "$APP" && set -a && . /etc/mikamike/staging.env && set +a
.venv/bin/python -m tools.db status
.venv/bin/python -m tools.sauvegarde sauvegarder --dest "$SV/avant-$SHA-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python -m tools.sauvegarde verifier --source "$SV/avant-$SHA-<horodatage>"
```

## 4. Migration (UNE seule tâche, application arrêtée ou non encore démarrée)

```sh
.venv/bin/python -m tools.db stamp-existant mika      # UNIQUEMENT pour une base historique sans alembic_version
.venv/bin/python -m tools.db stamp-existant billing   # idem
.venv/bin/python -m tools.db upgrade
.venv/bin/python -m tools.db status                   # attendu : mika m0003_tutorat OK, billing b0004_verif_email_revocation OK
.venv/bin/python -m tools.db upgrade                  # deuxième passage : sans effet (idempotent, testé)
```

## 5. Données de démonstration (facultatif, synthétiques uniquement)

```sh
.venv/bin/python -m tools.staging_dataset generer --sortie /tmp/staging-rc1   # affiche SHA contenu + SHA utilisateurs
.venv/bin/python -m tools.staging_dataset verifier --dossier /tmp/staging-rc1 --sha <SHA contenu affiché>
.venv/bin/python -m tools.staging_dataset charger --dossier /tmp/staging-rc1   # refus en production (code 2)
```

## 6. Activation

```sh
sudo systemctl restart mikamike-backend
# ExecStart attendu du service :
#   /srv/mikamike/app/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers
```
Un démarrage refusé cite la variable fautive (jamais sa valeur) : corriger l'environnement, relancer.

## 7. Healthcheck

```sh
curl -fsS https://<staging>/healthz           # {"status":"ok",...}
.venv/bin/python -m tools.db status
```

## 8. Smoke tests

```sh
.venv/bin/python -m tools.smoke --url https://<staging> --mode-auth observe
.venv/bin/python -m tools.smoke --url https://<staging> --mode-auth observe --ecriture --email <boîte-de-test>@<domaine-equipe>
node contrat_front/verifier_contrat.mjs https://<staging>          # vérificateur de contrat front (Node ≥ 22)
.venv/bin/python -m tools.purge_retention                            # SIMULATION uniquement
.venv/bin/python -m tools.artefacts verifier                         # attendu : WAITING_FOR_ARTIFACT (code 4)
```
Critère : toutes les lignes `OK`, `n/n vérifications vertes`.

## 9. Observation (48 h)

Journaux JSON `event=http_request` : aucun 5xx inattendu, `jeton_revoque` cohérent avec les
déconnexions, 429 limités aux tests, aucune adresse e-mail ni jeton dans les journaux.

## 10. Passage `observe` → `enforce` (décision D12, pas avant)

Conditions : front conforme au pack (`frontend-contract/`) + E2E front verts. Puis
`MIKA_AUTH_MODE=enforce`, redémarrage, `tools.smoke --mode-auth enforce` vert.

## 11. Retour arrière

ROLLBACK_RUNBOOK.md.
