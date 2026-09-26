# DPO_RETENTION_DECISION — paramètres de conservation à valider

**Statut : NON VALIDÉ. Ce document ne contient aucune décision juridique.** Il liste les paramètres
techniques que le DPO (ou le responsable de traitement) doit fixer, avec la valeur *proposée* par
défaut dans le code et ce que chaque valeur implique. Les valeurs proposées sont prudentes et
réversibles ; aucune n'est présentée comme conforme tant qu'elle n'est pas signée ci-dessous.

Contexte : plateforme éducative, utilisateurs **mineurs** (élèves) et parents ; données pseudonymisées
(HMAC) côté pédagogie ; adresse e-mail et mot de passe haché côté comptes.

## 1. Paramètres configurables (variables d'environnement, jours)

| clé | variable | donnée | critère de purge | proposée | bornes | à décider |
|---|---|---|---|---|---|---|
| SESSIONS | `MIKA_RETENTION_SESSIONS_JOURS` | état de séance (brouillon d'ardoise, progression de séance) | inactive depuis | 30 | 1–3650 | durée : ______ |
| TUTORAT_REQUETES | `MIKA_RETENTION_TUTORAT_REQUETES_JOURS` | journal d'idempotence du tuteur (réponses rejouables) | créée depuis | 30 | 1–3650 | durée : ______ |
| TUTORAT_SESSIONS | `MIKA_RETENTION_TUTORAT_SESSIONS_JOURS` | échanges élève ↔ tuteur Mika | dernière activité depuis | 180 | 1–3650 | durée : ______ |
| VERIFICATIONS_EMAIL | `MIKA_RETENTION_VERIFICATIONS_EMAIL_JOURS` | jetons de vérification d'adresse (hachés) + adresse cible | expirés ou utilisés depuis | 7 | 1–3650 | durée : ______ |
| INVITATIONS_EXPIREES | `MIKA_RETENTION_INVITATIONS_EXPIREES_JOURS` | codes d'invitation parent ↔ élève jamais utilisés | expirés depuis | 0 | 0–3650 | durée : ______ |

Une valeur hors bornes ou mal formée **empêche la purge** (jamais de purge plus large que prévu).

## 2. Données NON purgées automatiquement (questions ouvertes)

| donnée | comportement actuel | question au DPO |
|---|---|---|
| `mika_tentatives`, `mika_etats` (historique pédagogique pseudonymisé) | conservé tant que le compte existe ; effacé par le droit à l'oubli (`/rgpd`) | faut-il une durée maximale après la dernière activité (ex. fin de scolarité) ? ______ |
| invitations **utilisées** | conservées (trace du rattachement ; pseudo-identifiant effacé à l'acceptation) | durée de conservation de la preuve de rattachement : ______ |
| comptes parents inactifs | aucune purge automatique | durée d'inactivité avant suppression / notification : ______ |
| journal d'audit de purge (`MIKA_RETENTION_AUDIT`) | conservé indéfiniment (aucune donnée d'élève) | durée de conservation de la preuve d'effacement : ______ |
| journaux applicatifs (JSON, sans donnée sensible) | hors dépôt (plateforme d'hébergement) | durée chez l'hébergeur : ______ |
| sauvegardes de base | hors dépôt | rotation des sauvegardes (une donnée purgée survit jusqu'à expiration de la sauvegarde) : ______ |

## 3. Garanties techniques déjà en place (vérifiables par les tests)

- simulation par défaut ; application uniquement sur **rapport scellé** de moins de 24 h, établi
  sous la même politique, appliqué à la même date de référence, sans élargissement du périmètre ;
- suppression par lots ; reprise après interruption ; idempotence ;
- journal d'audit chaîné (opérateur, empreinte du rapport, politique, lignes supprimées, durée) ;
- aucune donnée d'élève dans le rapport ni dans l'audit (comptes par table uniquement) ;
- `tests_cloud/test_retention.py` (25 tests), mutants `retention_*`.

## 4. Mise en œuvre après décision

1. Reporter les durées signées dans le coffre de configuration (variables du §1).
2. Staging : `python -m tools.purge_retention --sortie rapport.json`, relire le rapport,
   `MIKA_OPERATEUR=<id> python -m tools.purge_retention --appliquer --rapport rapport.json`,
   puis `--verifier-audit`.
3. Production : même procédure, d'abord à la main ; une tâche planifiée seulement après décision
   explicite (fréquence : ______).

## 5. Validation

| rôle | nom | date | signature |
|---|---|---|---|
| DPO | | | |
| responsable de traitement | | | |
