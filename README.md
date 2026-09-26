# MikaMike Backend (autonome)

Backend FastAPI du tuteur scientifique adaptatif **MikaMike**. Totalement
autonome : aucune dépendance à une autre plateforme. Bases **SQLite dédiées**, dont le
schéma est appliqué par **migrations versionnées** (`python -m tools.db upgrade`) — jamais
créé implicitement à l'import (cf. `CLOUD_DB_MIGRATION_PLAN.md`).

## Lancer

```bash
pip install -r requirements.txt
python -m tools.db upgrade        # schéma des deux bases (MIKA_DB_URL, BILLING_DB_URL)
uvicorn main:app --reload         # refuse de démarrer si le schéma n'est pas à jour
```

- Docs interactives : http://127.0.0.1:8000/api/v1/docs
- Santé : http://127.0.0.1:8000/health

## Endpoints (préfixe `/api/v1`)

| Méthode | Chemin | Rôle |
|---|---|---|
| POST | `/api/v1/exercices/soumettre` | évalue la réponse (learning engine) et renvoie une remédiation en cas d'erreur |
| GET  | `/api/v1/parcours/prochaine-etape` | prochaine marche réelle de l'escalier |
| GET  | `/api/v1/parents/dashboard/{student_pseudo_id}` | stats agrégées **sans PII** (indexation HMAC) |
| POST | `/api/v1/comptes/inscription` · `/connexion` | comptes self-service (JWT) |
| GET  | `/api/v1/comptes/moi` | profil du compte courant (Bearer) |
| POST | `/api/v1/paiement/checkout` · `/webhook` | abonnement Stripe |
| GET  | `/api/v1/paiement/statut` | statut d'abonnement |
| POST | `/api/v1/auth/eleve/jeton` | jeton de séance élève pour un compte lié (AUTH_CONTRACT.md) |
| POST | `/api/v1/mika/session/start` · `/answer` · `/help` · `/comprehension` | tuteur Mika (MIKA_API_CONTRACT.md) |
| GET  | `/api/v1/mika/session/{tutorat_id}` | état public du tutorat |

Les routes élève / parent / RGPD exigent un jeton (`MIKA_AUTH_MODE=enforce`, défaut) :
voir `AUTH_CONTRACT.md` (matrice d'autorisation, mode `off` de transition interdit en production).

## Structure

```
backend/
├── main.py                     # app FastAPI (uvicorn main:app)
├── requirements.txt
├── app/api/v1/mikamike/        # moteur pédagogique + endpoints exercices/parents/parcours
│   ├── learning_engine.py      # escalier pédagogique
│   ├── store.py                # SQLite dédiée (MIKA_DB_URL)
│   ├── catalogue.py, crud.py, schemas.py, router.py
├── paiement_comptes/           # comptes self-service + abonnement Stripe
│   ├── database.py             # SQLite dédiée (BILLING_DB_URL)
│   ├── models_billing.py, crud_billing.py, router_comptes.py, router_paiement.py
├── tests_mika/                 # 6 tests (succès + erreur->remédiation)
└── tests_paiement/             # 7 tests (comptes + abonnement)
```

## Variables d'environnement (défauts sûrs)

```
MIKA_DB_URL=sqlite:///./mikamike_backend.db
BILLING_DB_URL=sqlite:///./billing.db
MIKA_JWT_SECRET=<secret JWT (PyJWT) — obligatoire, distinct du suivant>
MIKA_PSEUDO_SECRET=<secret HMAC pseudonymisation — à définir en prod>
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
MIKA_APP_URL=https://app.mikamike.fr
CORS_ORIGINS=https://app.mikamike.fr   # liste séparée par des virgules
```

## Développement (environnement reproductible, hors ligne)

```bash
./setup.sh              # venv isolé + dépendances + ruff + tests (secrets de TEST factices)
source .venv/bin/activate
python -m pytest -q     # suite hors ligne (tests_mika/, tests_paiement/, tests_cloud/) — cf. CLOUD_TEST_REPORT.md
```

Aucune clé réelle, aucune API payante, aucune base réelle : Stripe reste non configuré
(les routes renvoient une erreur explicite). Voir `.env.example` pour les NOMS de variables.

### Outils (`tools/`)
| Commande | Rôle |
|---|---|
| `python -m tools.content_check` | garde-fou contenu (fixtures, existant, catalogue) — exécuté en CI |
| `python -m tools.rapports [--artefacts DIR --sha-manifest SHA] [--depot DIR]` | backlog canonique (par matière / niveau / programme / chapitre) + audit de déduplication (reproductibles) |
| `python -m tools.db status\|upgrade\|downgrade\|stamp-existant\|sql` | migrations des bases (CLOUD_DB_MIGRATION_PLAN.md) |
| `python tools/secret_scan.py --history` | scan de secrets arbre + historique, valeurs jamais affichées |
| `python -m tools.verifier_manifest SHA256_DEPOT_PREPARE.txt` | dérive d'un manifeste SHA-256 |
| `python -m tools.mutation_check` | bugs injectés (sessions 1 et 2) : la suite doit tous les détecter |

### Chaîne de contenu pédagogique (`app/curriculum/`)
Modèle canonique des programmes, provenance vérifiable, validateurs (structure, texte,
formules), vérificateurs par matière (SymPy, unités…), exercices/quiz, tuteur Mika.
Documentation : `CLOUD_ARCHITECTURE.md`, `CLOUD_DATA_MODEL.md`, `CLOUD_PEDAGOGY_MIKA.md`.
Import des artefacts réels : `IMPORT_CONTRACT.md`. Revue de la session 1 : `CLOUD_REVIEW_SESSION1.md`.
État et reprise : `CLOUD_NEXT_SESSION.md`.

RGPD : aucune donnée nominative n'entre ni ne sort ; les identifiants sont re-hachés en HMAC
pour l'indexation ; l'effacement couvre toutes les tables élève.
