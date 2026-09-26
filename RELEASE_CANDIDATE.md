# RELEASE_CANDIDATE — MikaMike backend, RC1 (session cloud 5, 2026-09-26)

| verdict | valeur | condition |
|---|---|---|
| **READY_FOR_STAGING** | **YES** | code, migrations, runbook, smoke et rollback prêts et testés ; CI `rc-gate` verte sur le SHA déployé ; secrets et hôte staging fournis par Mike (hors dépôt) |
| **READY_FOR_PRODUCTION** | **NO** | artefacts officiels absents, front + E2E front absents (D12), fournisseur de courriel réel non choisi, durées DPO non validées, pile non fusionnée |

Rien n'a été fusionné ni déployé. Aucune production touchée, aucun secret réel, aucune API payante,
aucun courriel réel, aucune donnée réelle de mineur.

## 1. Identification

| élément | valeur |
|---|---|
| branche | `cloud/mikamike-release-candidate-1` (miroir `claude/loving-hamilton-e1ksf3`) |
| PR | https://github.com/Mike-teib/mikamike-backend/pull/7 (draft, base = PR #6) |
| SHA final | voir `CLOUD_NEXT_SESSION.md` (dernier SHA vert en CI) ; déployer uniquement un SHA dont `rc-gate` est vert |
| pile | main ← [#3](https://github.com/Mike-teib/mikamike-backend/pull/3) ← [#4](https://github.com/Mike-teib/mikamike-backend/pull/4) ← [#5](https://github.com/Mike-teib/mikamike-backend/pull/5) ← [#6](https://github.com/Mike-teib/mikamike-backend/pull/6) ← [#7](https://github.com/Mike-teib/mikamike-backend/pull/7) : linéaire, 0 conflit (STACK_INTEGRATION_REPORT.md) |
| ordre de fusion | #3 → #4 → #5 → #6 → #7, **uniquement par Mike** (avances rapides) |

## 2. Contenu de la RC1 (au-dessus de la PR #6)

| lot | livrable |
|---|---|
| 1 | STACK_INTEGRATION_REPORT.md (historique, dépendances, migrations, compatibilité API/schéma) |
| 3 | API branchée sur le moteur de progression sur historique (`app/api/v1/mikamike/moteur.py`) ; R8 corrigé ; `MIKA_PROGRESSION_MOTEUR=legacy` en retour arrière |
| 4 | `frontend-contract/` : types, client, validateurs, machines d'état, exemples, tests contractuels |
| 5 | E2E backend complet en enforce (`tests_cloud/test_e2e_release.py`) |
| 6 | fournisseur SMTP générique (EMAIL_PROVIDER_SETUP.md), aucune clé |
| 7 | rétention : rapport scellé, lots, reprise, idempotence, audit chaîné ; DPO_RETENTION_DECISION.md |
| 8 | ARTIFACTS_REQUIRED_MANIFEST.json + `tools.artefacts verifier` |
| 9 | dataset synthétique de staging (STAGING_DATASET.md) |
| 10 | migrations : matrice de toutes les têtes, rollback runbook, reprise |
| 11 | performance : requêtes constantes par appel (aucun N+1 trouvé), migration 100 000 lignes |
| 12 | audit sécurité : matrice BOLA + inventaire des routes, S5-01 corrigé |
| 13 | garde de publication : quiz revalidé, auto-tests rejoués (TESTS_ROUGES) |
| 15 | CI : Node 22 avant pytest, job `frontend-contract`, étapes RC1, verrou `rc-gate` |
| 16 | runbooks staging / production / rollback ; `tools.smoke`, `tools.sauvegarde` |

## 3. Migrations

| base | head | chaîne |
|---|---|---|
| mika | `m0003_tutorat` | m0001_baseline → m0002_index_tentatives → m0003_tutorat |
| billing | `b0004_verif_email_revocation` | b0001 → b0002_liens_compte_eleve → b0003_invitations_lien → b0004 |

La RC1 n'ajoute **aucune** migration. Validé : base neuve, base historique adoptée, pas à pas,
double et concurrent, interrompu (atomicité par révision) puis reprise, downgrade/upgrade avec
données, **matrice des 20 couples de départ** montés ensemble puis application démarrée en `check`,
rollback du runbook vers b0003 avec données créées par l'API.

## 4. Variables d'environnement

Obligatoires en production (démarrage refusé sinon) : `MIKA_ENV=production`, `MIKA_JWT_SECRET`,
`MIKA_PSEUDO_SECRET`, `MIKA_DB_URL`, `BILLING_DB_URL`, `MIKA_EMAIL_TRANSPORT=smtp` + `MIKA_SMTP_HOST`,
`MIKA_SMTP_FROM`, `MIKA_SMTP_USER`, `MIKA_SMTP_PASSWORD` (chiffré : `MIKA_SMTP_SECURITE=starttls|ssl`).
Nouveaux en RC1 : `MIKA_SMTP_*`, `MIKA_PROGRESSION_MOTEUR` (historique|legacy),
`MIKA_RETENTION_INVITATIONS_EXPIREES_JOURS`, `MIKA_RETENTION_AUDIT`, `MIKA_OPERATEUR` (outil de purge),
`MIKA_ARTEFACTS_DIR`. Référence : `.env.example`.

## 5. Dépendances

Python : `requirements.txt` inchangé (fastapi 0.141.1, pydantic 2.13.5, SQLAlchemy 2.0.35, alembic
1.20.0, PyJWT 2.15.0, bcrypt 4.2.0, sympy 1.14.0, stripe 10.10.0…) ; le SMTP utilise la bibliothèque
standard. Node ≥ 22.18 pour le package front et le vérificateur de contrat ; `typescript` 5.9.3
(devDependency unique, lockfile). pip-audit : 0 vulnérabilité connue. **SQLite uniquement**
(aucun pilote PostgreSQL) : une seule instance applicative (`--workers 1`).

## 6. Tests

Voir le rapport final de session (`CLOUD_NEXT_SESSION.md`) pour les chiffres exacts de la tête ;
base de la pile (#6, 470e89e) : 4593 passed. Suites ajoutées en RC1 : moteur/API (30), SMTP (22),
rétention (+14), artefacts (16), E2E RC (3), migrations RC (22), perf RC (10), sécurité RC (24),
publication RC (35), dataset (27), package front (5 pytest + 293 Node), smoke (3), sauvegarde (3).

## 7. Mutations

`python -m tools.mutation_check` (CI, job `mutation`) : tous les mutants doivent être tués.
Mutants ajoutés en RC1 : progression/moteur (9 + 2 réalignés), SMTP (5), rétention (7 + 2
réalignés), S5-01 (1), publication (2).

## 8. Sécurité

bandit 0, pip-audit 0, secrets arbre 0 (historique : 12 connues, D1). Corrigés en RC1 : S5-01 (P2,
course à la première soumission ⇒ 500), S5-02 (P2 pédagogique, R8), S5-03 (P3, durcissement SMTP),
deux écarts de la garde de publication. P0 ouverts : 0. P1 ouverts : 0. Détail :
CLOUD_SECURITY_REPORT.md.

## 9. Artefacts manquants — WAITING_FOR_ARTIFACT

C02, C02-6, C02-6.1, M01, Extraction V3, PDF officiels (+ structure des PDF, SHA256_SOURCE, plans de
guidage) : ARTIFACTS_REQUIRED_MANIFEST.json. Conséquence : catalogue du tuteur vide en réel
(`start` ⇒ 404), 42 notions historiques NOT_EVIDENCED, aucune publication possible hors mode test.

## 10. Front manquant

Le front n'est pas dans ce dépôt. Livré : `frontend-contract/` (à intégrer par l'équipe front) et
FRONT_IMPLEMENTATION_PACK.md, dont **8 écarts d'API** à trancher (codes 401 hétérogènes, `jeton_expire`
absent sur `/comptes/*`, échec d'envoi masqué à l'inscription…). Aucune route HTTP de **quiz**
n'existe (module prêt, non exposé). E2E front : à écrire (condition D12).

## 11. Fournisseur de courriel

Code prêt (SMTP générique, EMAIL_PROVIDER_SETUP.md) ; prestataire, DPA, domaine (SPF/DKIM/DMARC)
et identifiants : décision et action de Mike.

## 12. DPO

DPO_RETENTION_DECISION.md : 5 durées configurables + 6 questions ouvertes ; rien n'est présenté
comme conforme sans signature.

## 13. Staging, smoke, rollback

- Procédure : STAGING_DEPLOYMENT_RUNBOOK.md (sauvegarde → migration → activation → healthcheck →
  smoke → observation 48 h → enforce après D12).
- Smoke : `python -m tools.smoke --url <hôte> [--ecriture --email <boîte de test>]`, vérificateur
  Node du contrat, purge en simulation, état des artefacts.
- Rollback : ROLLBACK_RUNBOOK.md (bascule `legacy`, retrait de publication, rollback de lot, retour
  de code, downgrade b0003 documenté, restauration `tools.sauvegarde`).

## 14. Verdicts

**READY_FOR_STAGING = YES** — sous réserve de : CI `rc-gate` verte sur le SHA déployé, secrets
staging dédiés, hôte staging (une instance), `MIKA_AUTH_MODE=observe` jusqu'à D12.

**READY_FOR_PRODUCTION = NO** — bloquants : P1 artefacts officiels, P2 front + E2E front (D12),
P3 fournisseur de courriel réel, P4 validation DPO, P5 rotation des secrets (D1), P6 staging
observé en enforce, P8 fusion de la pile par Mike (PRODUCTION_DEPLOYMENT_RUNBOOK.md §0).

## 15. Incompatibilités de contrat introduites par la RC1

- `etat_maitrise` décidé par le moteur sur historique : plus de `MAITRISE` sans réussites
  autonomes sur ≥ 2 jours, plus de `FRAGILE`/`A_REVOIR` après une seule réponse (NON_EVALUEE ⇒
  libellé provisoire) ; `NON_ACQUISE` ⇒ `A_REVOIR`. Retour : `MIKA_PROGRESSION_MOTEUR=legacy`.
- Ajout (non cassant) : `progression` dans `/exercices/soumettre` et `/escalier/etape`.
- `POST /comptes/verification-email` peut répondre 503 `courriel_indisponible`.
