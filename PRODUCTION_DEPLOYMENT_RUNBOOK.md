# PRODUCTION_DEPLOYMENT_RUNBOOK — MikaMike backend

**État au 2026-09-26 : NE PAS EXÉCUTER.** `READY_FOR_PRODUCTION = NO` (RELEASE_CANDIDATE.md §14).
Ce runbook décrit la procédure pour le jour où les bloquants sont levés ; il ne vaut pas autorisation.

## 0. Portes (toutes obligatoires, signées)

| # | porte | preuve |
|---|---|---|
| P1 | artefacts officiels importés, lot **VALIDATED** sans `autoriser_fictif`, contenus publiés par un opérateur nommé | `tools.import_lot simuler` + `tools.publication etat` |
| P2 | front conforme à `frontend-contract/` + E2E front verts (D12) | CI du front |
| P3 | fournisseur de courriel réel (UE, DPA signé, SPF/DKIM/DMARC) validé en staging | EMAIL_PROVIDER_SETUP.md §4 |
| P4 | durées de rétention signées par le DPO | DPO_RETENTION_DECISION.md §5 |
| P5 | D1 : secrets **neufs** (jamais ceux d'un environnement ayant tourné sans secret) | coffre |
| P6 | staging `enforce` observé 48 h sans anomalie, même `$SHA` | STAGING_DEPLOYMENT_RUNBOOK.md §9–10 |
| P7 | CI verte sur `$SHA` (`rc-gate`) | Actions |
| P8 | fusion de la pile #3 → … → RC par Mike | GitHub |

## 1. Environnement (différences avec le staging)

```
MIKA_ENV=production               # interdit : auth off, transport faux/journal, contenu fictif, SMTP en clair
MIKA_AUTH_MODE=enforce
MIKA_RATE_LIMIT=on
MIKA_EMAIL_TRANSPORT=smtp         # + MIKA_SMTP_* de PRODUCTION (coffre), MIKA_SMTP_SECURITE=starttls|ssl
MIKA_JWT_SECRET / MIKA_PSEUDO_SECRET = secrets de PRODUCTION (coffre, ≥ 32 caractères, distincts)
MIKA_RETENTION_*_JOURS = valeurs signées par le DPO
```

## 2. Fenêtre de maintenance

Annoncer l'indisponibilité ; mettre le reverse proxy en page de maintenance (503) ; arrêter le service :
```sh
sudo systemctl stop mikamike-backend
```

## 3. Sauvegarde (obligatoire, vérifiée, copiée hors de l'hôte)

```sh
cd "$APP" && set -a && . /etc/mikamike/production.env && set +a
.venv/bin/python -m tools.db status
.venv/bin/python -m tools.sauvegarde sauvegarder --dest "$SV/avant-$SHA-$(date -u +%Y%m%dT%H%M%SZ)"
.venv/bin/python -m tools.sauvegarde verifier --source "$SV/avant-$SHA-<horodatage>"
# copie chiffrée hors de l'hôte selon la politique d'hébergement (hors dépôt)
```

## 4. Code

```sh
sudo -u mikamike git -C "$APP" fetch origin main
sudo -u mikamike git -C "$APP" checkout --detach "$SHA"
sudo -u mikamike "$APP/.venv/bin/pip" install --require-virtualenv -r "$APP/requirements.txt"
```

## 5. Migration (une seule tâche, service arrêté)

```sh
.venv/bin/python -m tools.db upgrade
.venv/bin/python -m tools.db status     # les deux bases : OK
```
En cas d'échec : la révision en cours est annulée en bloc (atomicité par révision, testée) ; ne pas
démarrer ; appliquer ROLLBACK_RUNBOOK.md §2.

## 6. Activation

```sh
sudo systemctl start mikamike-backend     # uvicorn main:app --workers 1 --proxy-headers
```
Retirer la page de maintenance seulement après le §7.

## 7. Healthcheck et smoke (LECTURE SEULE en production)

```sh
curl -fsS https://<prod>/healthz
.venv/bin/python -m tools.smoke --url https://<prod> --mode-auth enforce
.venv/bin/python -m tools.publication etat --depot <racine du dépôt de contenu>
```
Jamais `--ecriture` en production (pas de compte de test dans la base réelle).

## 8. Surveillance renforcée (24 h)

5xx, 401 `jeton_revoque`, 429, `courriel_echec` ; seuil de retour arrière : tout 5xx reproductible,
ou échec de courriel de vérification > 5 % sur 1 h.

## 9. Rétention

Première purge **manuelle**, après validation DPO : `tools.purge_retention --sortie rapport.json`,
relecture, `MIKA_OPERATEUR=<id> tools.purge_retention --appliquer --rapport rapport.json`,
`--verifier-audit`. Aucune tâche planifiée sans décision explicite.
