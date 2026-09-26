# ROLLBACK_RUNBOOK — retour arrière MikaMike backend

Trois niveaux, du plus léger au plus lourd. Toujours commencer par une **sauvegarde de l'état
présent** (même dégradé) : on ne restaure jamais sans pouvoir revenir.

```sh
cd "$APP" && set -a && . /etc/mikamike/<env>.env && set +a
.venv/bin/python -m tools.sauvegarde sauvegarder --dest "$SV/incident-$(date -u +%Y%m%dT%H%M%SZ)"
```

## 1. Retour fonctionnel sans code ni schéma (secondes)

| symptôme | bascule | effet |
|---|---|---|
| comportement de progression contesté | `MIKA_PROGRESSION_MOTEUR=legacy` puis redémarrage | ancien calcul ; mêmes tables, aucune conversion (testé : `test_legacy_retour_arriere_sans_migration`) |
| front non prêt pour les jetons (staging) | `MIKA_AUTH_MODE=observe` | journalise sans refuser ; **interdit en production** |
| fournisseur de courriel en panne | aucune : l'inscription continue (201), le renvoi répond 503 | réessayer plus tard ; changer `MIKA_SMTP_*` si besoin |
| contenu publié erroné | `python -m tools.publication retirer <contenu_id> --depot <racine> --operateur <id>` | retiré du catalogue du tuteur immédiatement |
| lot de contenu erroné | `python -c "from pathlib import Path; from app.curriculum.depot import DepotContenu; DepotContenu(Path('<racine>')).rollback()"` | réactive le lot précédent (revalidé) ; la base élève n'est pas touchée |

## 2. Retour du code (minutes)

```sh
sudo systemctl stop mikamike-backend
sudo -u mikamike git -C "$APP" checkout --detach "$SHA_PRECEDENT"
sudo -u mikamike "$APP/.venv/bin/pip" install --require-virtualenv -r "$APP/requirements.txt"
.venv/bin/python -m tools.db status
```
- Si `status` est **OK** (le code précédent connaît le schéma courant) : démarrer.
- Sinon (`MIKA_DB_INIT=check` refuserait de démarrer) : appliquer le §3 **avant** de démarrer.

## 3. Retour du schéma (vers la PR #5, b0003)

Seule la base billing a évolué depuis la PR #5 (b0004) ; la base mika est inchangée (m0003).

```sh
sudo systemctl stop mikamike-backend
.venv/bin/python -m tools.db downgrade billing b0003_invitations_lien
.venv/bin/python -m tools.db status
```
Perte **documentée et testée** (`test_rollback_runbook_vers_pr5_puis_retour_donnees_conservees`) :
table `verifications_email` (jetons en cours : les parents redemandent un courriel) et colonne
`comptes.jeton_version` (la révocation par version est perdue : **faire tourner `MIKA_JWT_SECRET`**
si une déconnexion ou une suppression de compte récente doit rester effective). Comptes, liens,
invitations, tentatives et états sont conservés.

Retour vers une version plus ancienne que la PR #5 : `downgrade billing b0002_liens_compte_eleve`
(perte : invitations) — à éviter ; préférer la restauration (§4).

## 4. Restauration complète (dernier recours)

Application **arrêtée** :
```sh
.venv/bin/python -m tools.sauvegarde verifier  --source "$SV/avant-$SHA-<horodatage>"
.venv/bin/python -m tools.sauvegarde restaurer --source "$SV/avant-$SHA-<horodatage>" --confirmer
sudo -u mikamike git -C "$APP" checkout --detach "$SHA_PRECEDENT"
.venv/bin/python -m tools.db status
sudo systemctl start mikamike-backend
```
Les bases remplacées sont conservées à côté (`*.avant-restauration-<date>`). Toute écriture faite
entre la sauvegarde et la restauration est perdue : la noter dans le rapport d'incident (RGPD : un
effacement demandé entre-temps doit être REJOUÉ après restauration).

## 5. Après tout retour arrière

```sh
curl -fsS https://<hôte>/healthz
.venv/bin/python -m tools.smoke --url https://<hôte> --mode-auth <mode courant>
```
Puis rapport d'incident : cause, niveau de retour, données perdues, effacements RGPD à rejouer.
