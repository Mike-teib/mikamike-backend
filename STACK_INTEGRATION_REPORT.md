# STACK_INTEGRATION_REPORT — Pile #3 → #4 → #5 → #6 (session cloud 5, 2026-09-26)

Branche d'intégration : `cloud/mikamike-release-candidate-1`, construite **localement** à partir de
la tête de la PR #6 (`470e89e`). Aucune branche distante n'a été fusionnée ni modifiée.

## 1. Historique et dépendances

| PR | branche | base | tête | commits propres | fichiers (diff vs base) |
|---|---|---|---|---|---|
| [#3](https://github.com/Mike-teib/mikamike-backend/pull/3) | `cloud/mikamike-autonomous-20260926` | `main` (`232e464`) | `fb77fb8` | 11 | 79 (+6507 / −186) |
| [#4](https://github.com/Mike-teib/mikamike-backend/pull/4) | `cloud/mikamike-session2-20260926` | #3 (`fb77fb8`) | `db03ff4` | 10 | 86 (+5384 / −345) |
| [#5](https://github.com/Mike-teib/mikamike-backend/pull/5) | `cloud/mikamike-session3-20260926` | #4 (`db03ff4`) | `90a95e9` | 11 | 63 (+5142 / −132) |
| [#6](https://github.com/Mike-teib/mikamike-backend/pull/6) | `cloud/mikamike-session4-autonomous` | #5 (`90a95e9`) | `470e89e` | 11 | 84 (+7472 / −58) |

Vérifications (commande : `git merge-base --is-ancestor <base> <tête>`) :

- chaque base est un **ancêtre strict** de la tête suivante : la pile est linéaire ;
- `main` n'a pas bougé depuis l'ouverture de la #3 (`232e464`) : aucun rebase nécessaire ;
- total `main..470e89e` : 43 commits, 194 fichiers, +24 155 / −371.

**Conséquence : intégrer la pile revient à partir de `470e89e`.** Aucun conflit n'existe, donc
aucun conflit n'a été résolu, et rien n'a été écrasé. Une fusion `#3 → #4 → #5 → #6` dans cet ordre
est une succession d'avances rapides (fast-forward).

Hors pile : la PR [#1](https://github.com/Mike-teib/mikamike-backend/pull/1) (Jules, `jules-8418647…`)
part de `main` et n'est **pas** intégrée. Elle a été remplacée fonctionnellement par la pile et ne
doit pas être fusionnée après elle sans revue (risque de réintroduire les mocks et le `create_all`).

## 2. Ordre des commits

L'ordre chronologique est aussi l'ordre logique : audit → dépendances → correctifs → CI → modèle
→ gardes → validateurs → pédagogie → outils (#3) ; revue → migrations → auth → API Mika → import (#4) ;
revue → R7 → R6 → migrations → audit API → harnais → sécurité → front → décisions (#5) ; R19 → contrat
front → observabilité → publication → import → curriculum → sciences → RC (#6). Aucun commit ne
dépend d'un commit postérieur (chaque tête de PR passait sa CI).

## 3. Migrations

| base | chaîne | tête | introduite par |
|---|---|---|---|
| mika | `m0001_baseline` → `m0002_index_tentatives` → `m0003_tutorat` | `m0003_tutorat` | #4 (toutes) |
| billing | `b0001_baseline` → `b0002_liens_compte_eleve` → `b0003_invitations_lien` → `b0004_verif_email_revocation` | `b0004_verif_email_revocation` | #4 (b0001–2), #5 (b0003), #6 (b0004) |

- une seule tête par base (aucune branche Alembic, aucune fusion de révisions) ;
- `down_revision` chaîné sans trou ; `python -m tools.db upgrade` puis `status` sur base neuve :
  `mika courante=m0003_tutorat head=m0003_tutorat OK`, `billing courante=b0004… OK` ;
- la session 5 **n'ajoute aucune migration** : le branchement du moteur relit les tables existantes.

## 4. Compatibilité API (cumul de la pile, vue du client)

| changement | PR | effet client |
|---|---|---|
| routes élève/parent/RGPD sous garde (`MIKA_AUTH_MODE`) | #4 | `enforce` ⇒ `Authorization: Bearer` requis |
| `POST /session/nouvelle`, identifiant de séance serveur (D15) | #5 | en `enforce`, un `session_id` inventé est refusé |
| invitations parent ↔ élève (D8) | #5 | `/liens/invitations`, `/liens/accepter` |
| vérification d'adresse (R19), révocation (`ver`, `cid`, `cv`) | #6 | invitation refusée si adresse non vérifiée ; jetons révoqués ⇒ 401 `jeton_revoque` |
| 422 sans `input`/`ctx`, champs inconnus ⇒ 422 | #6 | un client qui envoyait des champs en trop doit les retirer |
| **`progression` ajouté aux réponses `/exercices/soumettre` et `/escalier/etape`** | **RC1** | champ **additionnel**, optionnel ; `etat_maitrise` inchangé (7 valeurs historiques) |
| **`etat_maitrise` décidé par le moteur sur historique** | **RC1** | plus de MAITRISE le même jour, plus de FRAGILE après une seule réponse ; `MIKA_PROGRESSION_MOTEUR=legacy` pour revenir à l'ancien calcul |

Le contrat exécutable `contrat_front/contrat.json` (46 appels) a été régénéré : seul ajout,
l'objet `progression` de `/exercices/soumettre` (voir le diff du commit du lot 3).

## 5. Compatibilité du schéma de base

- aucune table ni colonne supprimée dans la pile ; b0004 ajoute `comptes.jeton_version` (défaut 0)
  et la table `verifications_email` ; m0002 ajoute un index ; m0003 ajoute les tables du tutorat ;
- les bases historiques (antérieures à Alembic) sont adoptées par `tools.db stamp-existant` (testé) ;
- `mika_etats.etat` garde ses 7 valeurs : l'ancien et le nouveau moteur écrivent le même vocabulaire,
  donc le retour arrière `legacy` ne demande aucune conversion (testé :
  `test_legacy_retour_arriere_sans_migration`).

## 6. Tests de la pile intégrée

| point | résultat |
|---|---|
| suite complète sur `470e89e` (avant tout changement de la session 5) | **4593 passed, 0 échec** |
| ruff | 0 |

Le chiffre « 4531 » annoncé dans la PR #6 correspond à un décompte antérieur au dernier commit
(470e89e ajoute les tests des lots 22, 26 et 31) ; la valeur mesurée ici sur la tête est 4593.

## 7. Changements introduits par la session 5 sur la branche RC

Voir `RELEASE_CANDIDATE.md` §1 et l'historique `git log 470e89e..HEAD` : un commit par lot.
