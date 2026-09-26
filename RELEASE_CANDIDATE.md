# RELEASE_CANDIDATE — MikaMike backend (session cloud 4, 2026-09-26)

**Verdict : RELEASE_CANDIDATE = NON pour la production ; candidat pour un STAGING (préproduction).**
Le backend est complet, testé et durci, mais la production exige des éléments hors de ce dépôt :
artefacts officiels (programmes), front conforme + E2E front (D12), fournisseur de courriel réel,
décisions DPO (rétention). Rien n'a été fusionné ni déployé depuis la session cloud.

## 1. Identification

| élément | valeur |
|---|---|
| branche | `cloud/mikamike-session4-autonomous` (miroir `claude/elegant-cray-y17l2b`) |
| PR | https://github.com/Mike-teib/mikamike-backend/pull/6 (draft, empilée sur #5 ← #4 ← #3) |
| SHA candidat | tête de la branche au moment du déploiement staging (`git rev-parse HEAD`) ; dernier SHA vert en CI noté dans CLOUD_NEXT_SESSION.md |
| ordre de fusion | #3 → #4 → #5 → #6, **uniquement par Mike** |

## 2. Migrations

| base | head | révisions |
|---|---|---|
| mika | `m0003_tutorat` | m0001_baseline, m0002_index_tentatives, m0003_tutorat |
| billing | `b0004_verif_email_revocation` | b0001_baseline, b0002_liens_compte_eleve, b0003_invitations_lien, b0004 (colonne `comptes.jeton_version`, table `verifications_email`) |

Validé par tests : base neuve, base historique adoptée, upgrade pas à pas, downgrade/re-upgrade
(données préservées), version inconnue refusée, migration interrompue ⇒ rollback, **double upgrade
sans effet sur schéma/données/révision, deux upgrades concurrents ⇒ base cohérente** (session 4).
Procédure : `python -m tools.db status` → sauvegarde → `python -m tools.db upgrade` → `status`.

## 3. Variables d'environnement

Obligatoires en production (démarrage refusé sinon) : `MIKA_JWT_SECRET`, `MIKA_PSEUDO_SECRET`
(≥ 32 caractères, non-test), `MIKA_DB_URL`, `BILLING_DB_URL`, `MIKA_ENV=production`,
`MIKA_EMAIL_TRANSPORT` = fournisseur réel **enregistré** (`faux`/`journal` refusés en production).

Réglages : `MIKA_AUTH_MODE` (off|observe|enforce — enforce seulement après D12), `MIKA_TOKEN_TTL_H`,
`MIKA_ELEVE_TOKEN_TTL_MIN`, `MIKA_DB_INIT` (none|check|migrate), `MIKA_MAX_BODY_BYTES`,
`MIKA_RATE_LIMIT`, `MIKA_PROXY_HOPS`, `MIKA_RL_EMAIL_GLOBAL`, `MIKA_CORRECTION_SYMBOLIQUE`,
`MIKA_INVITATION_TTL_MIN`, `MIKA_EMAIL_VERIFICATION` (requise ; `off` refusé en production),
`MIKA_EMAIL_VERIF_TTL_MIN`, `MIKA_RETENTION_*_JOURS`, `CORS_ORIGINS`, `MIKA_APP_URL`,
`STRIPE_*`. Référence : `.env.example`.

## 4. Dépendances

`requirements.txt` épinglé (fastapi 0.141.1, pydantic 2.13.5, SQLAlchemy 2.0.35, alembic 1.20.0,
PyJWT 2.15.0, bcrypt 4.2.0, sympy 1.14.0, stripe 10.10.0…). pip-audit : 0 vulnérabilité connue
(CI « sécurité »). Node 22 uniquement pour le vérificateur de contrat front (CI).

## 5. Tests et qualité

- Suite `tests_cloud` : 4065 au début de la session 4 → **4531 passed, 0 échec**.
- Mutation : tous les mutants ciblés de la session tués (dont 40 des lots 10, 14–21, 26).
- ruff 0, bandit 0, scanner de secrets 0, contrat front sans dérive (46 appels).

## 6. Sécurité (résumé, détail CLOUD_SECURITY_REPORT.md)

Corrigés en session 4 : S4-01 (notion anomale générable), S4-02 (bilan énergétique toute
dimension), S4-03 (422 renvoyant le mot de passe saisi), affectation de masse (11 schémas
d'entrée ouverts), en-têtes HTTP de sécurité, schéma parent fermé. P0 ouverts : 0. P1 ouverts : 0.

## 7. Procédure staging

1. Base staging vide ou copie anonymisée (jamais de données réelles d'élèves en staging).
2. Secrets staging dédiés (coffre), `MIKA_ENV=staging`, `MIKA_AUTH_MODE=observe`.
3. `python -m tools.db upgrade` puis `status` (2× OK).
4. Démarrage `uvicorn main:app` avec `MIKA_DB_INIT=check`.
5. Smoke tests (§8), puis vérificateur de contrat : `node contrat_front/verifier_contrat.mjs <url>`.
6. Observer 48 h les journaux JSON (`event=http_request`, codes 5xx, `jeton_revoque`, 429).

## 8. Smoke tests

`GET /healthz` = 200 ; `POST /api/v1/comptes/inscription` (adresse de test) = 201 et courriel de
vérification émis par le transport configuré ; `POST /comptes/connexion` = 200 ; accepter une
invitation sans adresse vérifiée = 403 `email_non_verifie` ; `POST /session/nouvelle` = 201 ;
`GET /parents/dashboard/<id non lié>` en enforce = 403 ; corps JSON avec champ inconnu = 422 ;
en-têtes `x-content-type-options: nosniff` présents ; `python -m tools.purge_retention` (simulation).

## 9. Retour arrière

Code : redéployer le SHA précédent. Schéma : `python -m tools.db downgrade billing b0003_invitations_lien`
(perte documentée : `verifications_email`, `jeton_version`) ; mika inchangé en session 4.
Toujours sauvegarder avant upgrade ; le downgrade est testé et atomique.

## 10. Incompatibilités (contrat API)

- 422 : le corps ne contient plus `input` ni `ctx` (seulement `type`, `loc`, `msg`).
- Champs inconnus dans un corps JSON ⇒ 422 `extra_forbidden` (auparavant ignorés).
- Jetons de compte : claim `ver` (révocation) ; jetons élève : claims `cid`, `cv` obligatoires.
- Invitation acceptée seulement si l'adresse du compte est vérifiée (R19).
- Dashboard parent : schéma fermé (champ imprévu ⇒ 500, jamais transmis).

## 11. Tâches front

Voir FRONT_IMPLEMENTATION_PACK.md et FRONT_AUTH_INTEGRATION.md : écrans vérification d'adresse,
invitation (émettre / saisir le code), `POST /session/nouvelle`, gestion `jeton_revoque`,
suppression/export du compte, tuteur Mika, puis E2E front (condition D12 du passage en enforce).

## 12. Artefacts manquants (WAITING_FOR_ARTIFACT)

C02, C02-6, C02-6.1, M01, Extraction V3, PDF officiels ; relevé `disciplines_indiquees` pour
l'Enseignement scientifique ; programmes cycle 2 et technologie cycle 4 (non modélisés, rien
d'inventé) ; fournisseur de courriel ; validation DPO des durées de rétention.
