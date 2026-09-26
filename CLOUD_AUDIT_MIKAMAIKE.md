# CLOUD_AUDIT_MIKAMAIKE — Audit de la réalité du dépôt

- Dépôt : `Mike-teib/mikamike-backend` · Date : 2026-09-26
- Branche de travail : `cloud/mikamike-autonomous-20260926` (miroir : `claude/funny-thompson-igpvnl`)
- Historique au démarrage : 2 commits (`c01d9ba` préparation, `232e464` retrait des replis de secret)
- Méthode : lecture intégrale des 60 fichiers suivis + exécution des tests. **Rien n'est inventé** :
  ce qui n'existe pas est marqué ABSENT.

## 1. Structure (état initial)

| Zone | Fichiers | Lignes | Rôle réel |
|---|---|---|---|
| `main.py` | 1 | 69 | App FastAPI, monte 8 routeurs sous `/api/v1`, `/health` |
| `app/core/security_config.py` | 1 | 66 | Lecture fail-closed de `MIKA_PSEUDO_SECRET` / `MIKA_JWT_SECRET` |
| `app/api/v1/mikamike/` | 7 | ~560 | Catalogue (4 exercices maths en dur), learning engine (7 états, graphe de prérequis démo), CRUD SQLite, routes exercices/parents/parcours |
| `app/api/v1/escalier/` | 3 | ~230 | Orchestrateur « 8 étapes » (déterministe, sans LLM) |
| `app/api/v1/parcours/` | 2 | ~365 | `curriculum_dataset.py` : 47 notions codées en dur (maths primaire→Tle, 2 physique 5e, 2 chimie 4e, 2 SVT 3e), DAG |
| `app/api/v1/memory/` | 3 | ~270 | Répétition espacée J+1/3/7/14, Ebbinghaus |
| `app/api/v1/session/` | 3 | ~300 | Heartbeat 5 min, sauvegarde/restauration d'état, SSE |
| `app/api/v1/rgpd/` | 2 | ~145 | Export / effacement par pseudo-id |
| `app/api/v1/security/` | 2 | ~170 | Garde JWT fail-closed, validation payload OCR (≤ 2 Mo, base64) — **non câblée** sur des routes |
| `paiement_comptes/` | 6 | ~740 | Comptes (bcrypt, JWT), Stripe Checkout + webhook |
| `tests_mika/`, `tests_paiement/` | 12 | ~1300 | 62 tests pytest |
| Docs racine | 11 | — | Rapports pré-Jules, SHA256, consignes de câblage |

## 2. Inventaire demandé

| Élément | Statut | Détail |
|---|---|---|
| Backend | PRÉSENT | FastAPI 0.115 / SQLAlchemy 2 / Pydantic 2 / SQLite |
| Frontend | **ABSENT** | Aucun fichier front dans ce dépôt |
| API | PRÉSENT | 20 routes (cf. §3) |
| Modèles | PRÉSENT | `mika_tentatives`, `mika_etats`, `mika_memory_schedules`, `mika_session_states`, `comptes`, `abonnements` |
| Stockage | PRÉSENT | 2 bases SQLite (`MIKA_DB_URL`, `BILLING_DB_URL`), tables créées à l'import |
| Scripts | ABSENT (initial) | Aucun script ; ajouté : `setup.sh` |
| Tests | PRÉSENT | 62 tests, 100 % verts (baseline) |
| Fixtures | PARTIEL | Fixtures pytest (client, DB jetables) ; aucune fixture de données pédagogiques |
| CI | **ABSENT** (initial) | Aucun `.github/workflows` |
| Dépendances | PRÉSENT | `requirements.txt` épinglé ; **CVE** sur python-jose, starlette, ecdsa, pytest (cf. rapport sécurité) |
| Logique pédagogique | PARTIEL | Escalier (états de maîtrise, remontée prérequis), règle LE-06 (aide ⇒ jamais MAITRISE) |
| Moteur professeur Mika | **PARTIEL / RUDIMENTAIRE** | Pas de dialogue : message fixe + 1 explication par exercice. Aucun indice gradué, aucune question intermédiaire, aucune 2e méthode |
| Ingestion programmes/notions | **ABSENT** | Aucune ingestion PDF/BO. Notions codées en dur **sans source officielle** |
| Exercices/quiz | PARTIEL / ABSENT | 4 exercices maths en dur ; **aucun quiz** |
| Validateurs | ABSENT | Aucune validation de contenu (notion, chapitre, texte, formule) |
| Import/export | PARTIEL | Export RGPD seulement ; aucun import d'artefacts |
| Sécurité | PARTIEL | Fail-closed secrets OK ; routes élève non authentifiées ; failles IDOR session (cf. rapport) |
| Registre notions / mappings / C02 / Extraction V3 / M01 | **ABSENT** | Artefacts du chantier local non présents dans ce dépôt |
| SymPy / filet mathématique | **ABSENT** | Correction par comparaison de chaînes normalisées |

## 3. Routes API (état initial)

| Méthode | Chemin | Auth | Remarque |
|---|---|---|---|
| GET | `/health`, `/healthz` | non | |
| POST | `/api/v1/exercices/soumettre` | non | |
| GET | `/api/v1/parents/dashboard/{id}` | non | aucune PII renvoyée |
| GET | `/api/v1/parcours/prochaine-etape` | non | 500 possible si état DB invalide |
| POST/GET | `/api/v1/parcours`, `/parcours/{u}/{l}/{s}` | non | **repli silencieux** vers Maths si matière absente |
| POST | `/api/v1/escalier/etape` | non | |
| POST | `/api/v1/memory/schedule`, `/memory/detect-fragile` | non | scores non bornés |
| POST | `/api/v1/session/heartbeat`, `/save-state`, `/reconnect` | non | **IDOR** : pas de contrôle de propriétaire |
| GET | `/api/v1/session/stream` | non | |
| GET/DELETE | `/api/v1/rgpd/export/{id}`, `/rgpd/effacer/{id}` | non | effacement **incomplet** (oublie mémoire + sessions) |
| POST | `/api/v1/comptes/inscription`, `/connexion` ; GET `/moi` | Bearer (moi) | `sub` non entier ⇒ 500 |
| POST | `/api/v1/paiement/checkout`, `/webhook` ; GET `/statut` | Bearer / signature | message d'exception Stripe renvoyé au client |

## 4. Bugs et dette constatés (à l'état initial)

| # | Gravité | Constat | Fichier |
|---|---|---|---|
| B1 | HAUTE (RGPD) | `/session/reconnect` renvoie l'état de séance d'une session appartenant à **un autre élève** ; `save-state` écrit dedans | `session/session_manager.py` |
| B2 | HAUTE (RGPD) | Droit à l'oubli incomplet : `mika_memory_schedules` et `mika_session_states` non effacés ni exportés | `rgpd/router.py` |
| B3 | MOYENNE | Parcours : matière/niveau inconnu ⇒ **repli silencieux** vers Maths 5e, étiqueté avec la matière demandée (mauvaise matière acceptée) | `parcours/curriculum_dataset.py` |
| B4 | MOYENNE | `valider_prerequis_resolus` renvoie toujours `True` (stub mort) | idem |
| B5 | MOYENNE | Jeton dont `sub` n'est pas un entier ⇒ `ValueError` ⇒ 500 au lieu de 401 | `paiement_comptes/router_comptes.py` |
| B6 | FAIBLE | Message d'exception Stripe renvoyé tel quel au client (fuite d'info) | `router_paiement.py` |
| B7 | MOYENNE | `detect-fragile` : scores/seuil non bornés ; `memory/schedule` : événement inconnu traité silencieusement comme FAILURE | `memory/router.py` |
| B8 | MOYENNE (pédago) | Série de succès pour MAITRISE compte les succès **avec aide** (contourne l'esprit de LE-06) | `mikamike/crud.py` |
| B9 | MOYENNE (pédago) | Escalier : sur erreur, l'échec est imputé à la **lacune prérequis** non testée au lieu de la compétence réellement tentée | `escalier/orchestrator.py` |
| B10 | FAIBLE | `prochaine_etape` : état DB invalide ⇒ `ValueError` ⇒ 500 | `mikamike/router.py` |
| B11 | FAIBLE | `datetime.utcnow` déprécié (mémoire, session) | |
| B12 | INFO | Deux systèmes d'identifiants de compétences non reliés (`GRAPHE_MATHS_COLLEGE` vs `maths_5e_04`…) | |
| B13 | INFO | Aucune notion n'a de source officielle ⇒ toutes `NOT_EVIDENCED` | |
| D1 | DETTE | 29 imports inutilisés (corrigés au lot 1) | |
| D2 | DETTE | `try/except: pass` ×4 autour de `create_all` à chaque requête | |

TODO/FIXME dans le code : **0**. Code mort : `valider_prerequis_resolus` (stub), `OcrPayload`/`exiger_session_active` non câblés sur des routes (utilisés seulement en test).

### Statut des corrections (mission cloud)
B1, B2, B3, B4, B5, B6, B7, B8, B9, B10, B11, D1, D2 : **corrigés** (tests de non-régression dans
`tests_cloud/test_api_regressions.py`). B12, B13 : documentés (backlog R1/R5).

## 5. Points non testés (initial)
Webhook Stripe (signature), CORS, `prochaine_etape` avec état corrompu, propriété de session,
effacement RGPD des tables mémoire/session, validation des entrées bornées, chemins d'erreur du JWT `sub`.

## 6. Conclusion
Le dépôt est un **backend applicatif** propre côté secrets mais **sans chaîne de contenu pédagogique**
(pas d'ingestion de programmes officiels, pas de provenance, pas de validateurs, pas de quiz, pas de
vérification symbolique). Le travail cloud ajoute cette chaîne sous forme de modules purs, testés,
hors ligne, alimentés uniquement par des **fixtures fictives explicitement marquées**. Aucun programme
officiel n'est inventé : les notions existantes restent `NOT_EVIDENCED` tant qu'aucune source n'est importée.
