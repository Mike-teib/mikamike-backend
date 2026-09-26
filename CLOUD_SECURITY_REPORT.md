# CLOUD_SECURITY_REPORT — Sécurité / RGPD / Secrets

Date : 2026-09-26 · Périmètre : arbre de travail **et** historique Git complet (2 commits).
Aucune valeur sensible n'est reproduite dans ce rapport.

## 1. Scan des secrets

Motifs recherchés (arbre + `git log --all -p`) : clés Stripe `sk_live/sk_test/whsec_`, jetons GitHub
`ghp_/github_pat_`, AWS `AKIA…`, Google `AIza…`, Slack `xox*`, Anthropic/OpenAI `sk-…`, clés privées
PEM, URL de base de données avec identifiants intégrés (postgres, mysql, mongodb), e-mails, numéros de téléphone FR.

| Constat | Résultat |
|---|---|
| Clé API / jeton réel | **0** |
| Clé privée | **0** |
| Chaîne de connexion avec mot de passe | **0** |
| Fichier `.env`, `.db`, `.sqlite`, dump, CSV, image, PDF dans l'historique | **0** |
| Littéral de secret **faible de démonstration** utilisé comme repli (`os.getenv(..., "<littéral>")`) | **OUI — historique uniquement** |

```
SECRET_DETECTED = YES   (secret faible de démonstration, pas une clé de service)
PATH = app/api/v1/*/router.py, learning_engine.py, spaced_repetition.py, session_manager.py,
       fail_closed.py, paiement_comptes/router_comptes.py (≈10 emplacements)
COMMIT = c01d9ba (introduit) — retiré du code exécutable par 232e464
ROTATION_REQUIRED = YES — si un environnement (staging/prod) a tourné SANS MIKA_PSEUDO_SECRET ou
                    MIKA_JWT_SECRET définis, ses pseudonymes HMAC et ses JWT ont été calculés avec un
                    secret désormais PUBLIC dans l'historique : régénérer les deux secrets, invalider
                    les jetons émis, et re-pseudonymiser (décision Mike : cf. CLOUD_NEXT_SESSION.md).
```

Autres hits (non sensibles) : le texte du rapport `RAPPORT_SECRETS_EXCLUS.md` (noms de motifs),
l'adresse e-mail d'auteur des commits (métadonnée Git du propriétaire, pas une donnée élève),
le nom d'hôte de la machine de build dans `junit_pre_jules.xml` (information mineure).

Hit historique supplémentaire (non sensible) : `34031bd:CLOUD_SECURITY_REPORT.md` — la 1re version de
ce rapport citait le motif générique d'URL de base avec identifiants (texte d'exemple, aucune valeur
réelle) ; reformulé depuis. `python tools/secret_scan.py --history` liste ces hits, valeurs masquées.

Réécriture d'historique : **non effectuée** (irréversible, hors périmètre sans accord Mike).

## 2. Données personnelles / élèves

| Recherche | Résultat |
|---|---|
| Données d'élèves réelles, conversations, photos, OCR, exports | **0** |
| Identifiants dans les tests | pseudonymes fictifs (`anon-eleve-999`, `eleve_test_…`) |
| E-mails dans les tests | domaines fictifs de test |

`PERSONAL_DATA_DETECTED = NO`

## 3. Dépendances (pip-audit, 2026-09-26)

| Paquet | Version | Avis | Action |
|---|---|---|---|
| python-jose | 3.3.0 | PYSEC-2024-232/233 (confusion d'algorithme, bombe JWE), PYSEC-2025-185 (sans correctif) | **Remplacé par PyJWT** (lot 2) |
| ecdsa | 0.19.2 | PYSEC-2026-1325 (sans correctif) | retiré avec python-jose |
| starlette | 0.38.6 | 8 avis (corrigés ≥ 1.3.1) | montée FastAPI/Starlette (lot 2) |
| pytest | 8.3.3 | PYSEC-2026-1845 | montée ≥ 9.0.3 (lot 2) |

## 4. Failles applicatives (cf. audit §4)

| # | Gravité | Faille | Statut |
|---|---|---|---|
| B1 | HAUTE | IDOR session : lecture/écriture de l'état de séance d'un autre élève | corrigé lot 2 |
| B2 | HAUTE | Droit à l'oubli incomplet (mémoire espacée + sessions) | corrigé lot 2 |
| B5 | MOYENNE | JWT `sub` non entier ⇒ 500 | corrigé lot 2 |
| B6 | FAIBLE | Exception Stripe renvoyée au client | corrigé lot 2 |
| S1 | HAUTE (conception) | Routes élève/RGPD **sans authentification** : quiconque connaît un pseudo-id peut exporter ou **effacer** | **DÉCISION MIKE** (contrat front) — garde prête : `exiger_session_active` |
| S2 | MOYENNE | Le JWT contient l'e-mail (PII dans un jeton lisible côté client) | DÉCISION MIKE |
| S3 | FAIBLE | Pas de rate-limiting sur `/comptes/connexion` (force brute) | DÉCISION (infra : reverse proxy ou middleware) |
| S4 | INFO | `prenom` d'élève (mineur) stocké en clair dans `comptes` : minimisation à confirmer | DÉCISION MIKE |

## 5. `.gitignore`
Déjà complet (env, clés, bases, caches). Ajouts : `.venv` déjà couvert ; ajout de `reports/` (sorties
générées des outils d'audit) et `checkpoints/` (états de reprise des traitements longs).

## 6. Privacy by design — règles appliquées dans le code ajouté
- aucun identifiant élève en clair dans les nouveaux modules : uniquement des pseudonymes HMAC ;
- aucun log de réponse d'élève dans les outils d'audit ;
- les fixtures pédagogiques sont **fictives et marquées** `FIXTURE_FICTIVE` ;
- effacement RGPD couvrant toutes les tables élève (lot 2), avec test de non-régression qui échoue si une
  nouvelle table indexée par `eleve_hmac` n'est pas couverte.

---

# Session cloud 2 (2026-09-26) — mise à jour

Aucun secret réel utilisé ni créé ; aucune donnée d'élève réelle ; aucune base réelle touchée ;
aucune API payante. Scan de secrets (arbre) : **0 détection** à chaque commit.

## Failles traitées (détail : CLOUD_REVIEW_SESSION1.md)
| # | Gravité | Faille | Statut |
|---|---|---|---|
| S1 / R2-18 | HAUTE | Routes élève/RGPD sans authentification (pseudo-id = preuve d'identité) | **corrigé** : `app/core/auth.py`, 14 routes + API tuteur gardées, mode `enforce` par défaut (AUTH_CONTRACT.md) |
| R2-03 | HAUTE | DoS SymPy (> 20 s) et `OverflowError` non rattrapée | **corrigé** : garde de complexité sur arbre non évalué |
| R2-05 | MOYENNE | Heartbeat : tiers désactivant la séance expirée d'un élève + oracle 401/403 | **corrigé** |
| R2-06 | MOYENNE | État de séance fusionné non borné (5,7 Mo stockés pour une limite de 2 Mo) | **corrigé** |
| R2-10 | MOYENNE | Garde JWT : jeton sans `exp` valable à vie, rôle `eleve` par défaut, jeton de compte accepté | **corrigé** |
| R2-11 | MOYENNE | `/comptes/moi` acceptait tout jeton signé à `sub` numérique, sans `exp` | **corrigé** (`typ=compte`, `exp` exigé) |
| R2-20 | MOYENNE | Aucune borne de taille de corps HTTP | **corrigé** : 413 avant lecture (4 Mio, configurable) |
| R2-04 | MOYENNE | Importeur : crash sur JSON hostile, lecture non bornée | **corrigé** |
| R2-13 | FAIBLE | `verifier_manifest` : traversée de chemin, code retour 0 en cas d'écart | **corrigé** |
| R2-21 | FAIBLE | `tools/rapports.py` posait un secret littéral de repli | **supprimé** |

## Modèle d'authentification (résumé)
- Jetons de **compte** (`typ=compte`, clé `MIKA_JWT_SECRET`) et de **séance élève** (`typ=mika-eleve`,
  `aud`, `iss`, `jti`, TTL 2 h, clé **dérivée** HMAC) : jamais interchangeables, HS256 uniquement,
  `alg=none` refusé, claims obligatoires.
- Droits dérivés des **liens compte ↔ élève** (HMAC), jamais du rôle seul ; 403 uniforme (pas d'oracle).
- `MIKA_AUTH_MODE=off` (contrat historique) **refusé si `MIKA_ENV=production`** ; valeur invalide ⇒
  refus de démarrer.

## Privacy by design (ajouts)
- Jeton élève sans PII (claims fixés, testé) ; l'e-mail reste dans le jeton de COMPTE (D3 ouverte).
- RGPD : l'export et l'effacement couvrent les tables de tutorat et les liens compte ↔ élève ; le test
  du registre parcourt désormais **toutes** les metadata de la base élève.
- Réponses d'erreur sans trace ni secret (testé).

## Contrôles (session 2)
| Contrôle | Résultat |
|---|---|
| bandit (≥ moyenne) | 0 |
| pip-audit (runtime + dev, dont alembic 1.20.0 ajouté) | 0 vulnérabilité connue |
| scan de secrets arbre | 0 |
| tests d'attaque | `tests_cloud/test_attaques.py` + `test_auth.py` + `test_review_session1.py` |

## Décisions restant à Mike
D1 rotation des secrets si un environnement a tourné sans eux · D3 e-mail dans le jeton de compte ·
D3bis rate-limiting · D8 création des liens compte ↔ élève · D9 effacement par l'élève lui-même ·
D11 révocation des jetons élève · D12 date de passage du front en `enforce`.

---

# Session cloud 3 (2026-09-26) — mise à jour

Aucun secret réel, aucune donnée d'élève réelle, aucune base réelle, aucune API payante.
Revue contradictoire de la PR #4 : CLOUD_REVIEW_SESSION2.md (16 findings : 0 P0, 4 P1, 12 P2).

## Failles traitées
| # | Gravité | Faille | Statut |
|---|---|---|---|
| S3-01 | P1 | Jeton élève encore valide après effacement RGPD / retrait du lien / désactivation du compte (réécriture de données d'un élève effacé) | **corrigé** (claim `cid` revérifié à chaque requête) |
| S3-15 | P1 | Lot de contenu à source fictive VALIDATED et publiable hors mode test | **corrigé** (`SOURCE_FICTIVE_HORS_TEST`, anomalie globale) |
| S3-02 / S3-03 | P1 | Migrations : URL avec `%` ; migration interrompue non reprenable | **corrigé** |
| S3-07 | P2 | Oracle de timing à la connexion (5 ms vs 295 ms : énumération des comptes) | **corrigé** (hash leurre) |
| S3-09 | P2 | Export RGPD incomplet (journal du tuteur, liens) | **corrigé** |
| S3-10 | P2 | Identifiants 128 car. dans des colonnes 64 (500 sur PostgreSQL) | **corrigé** |
| S3-13 | P2 | Squat d'un `session_id` prévisible (DoS ciblé) | **documenté** (D15 ; front : UUID v4) |
| S3-14 | P2 | bcrypt tronque à 72 octets | **documenté** |
| S3 / R7 | — | Absence de limitation de débit (S3 historique, D3bis) | **livré** |
| — | P2 | `sub` d'un jeton élève hors alphabet des identifiants (ex. vide) accepté au décodage | **corrigé** (401) |

## R7 — Limitation des tentatives (paramètres par défaut)
| Limiteur | Clé | Seuil | Fenêtre d'inactivité | Backoff (base → plafond) |
|---|---|---|---|---|
| connexion | (IP, e-mail) | 5 échecs | 15 min | 30 s → 15 min |
| connexion | IP | 30 échecs | 15 min | 60 s → 1 h |
| connexion | e-mail seul | 100 échecs (**désactivé** par défaut, `MIKA_RL_EMAIL_GLOBAL=1`) | 1 h | 60 s → 1 h |
| inscription | IP | 20 demandes | 1 h | 60 s → 1 h |
| jeton élève | compte | 30 émissions | 10 min | 60 s → 30 min |
| jeton élève | IP | 60 émissions | 10 min | 60 s → 30 min |
| jetons invalides | IP | 50 | 5 min | 30 s → 15 min |

Propriétés testées (`tests_cloud/test_limitation.py`, 31 tests, 7 mutants) : refus **avant**
bcrypt ; succès ⇒ reset (sauf compteur IP) ; blocage identique e-mail existant/inexistant ;
**pas de DoS** contre la victime (attaquant sur une IP, ou botnet de 150 IP) ; `X-Forwarded-For`
ignoré sans `MIKA_PROXY_HOPS`, entrées forgées à gauche ignorées ; mémoire bornée (100 000
clés, historique borné), clés hachées (aucun e-mail en mémoire) ; `off` interdit en production.
Limites : état **par processus** (N workers ⇒ N × la limite ; redémarrage ⇒ remise à zéro) ;
pour plusieurs instances, compléter par une limitation au reverse proxy.

## Tests de sécurité ajoutés (session 3)
`test_securite_s3.py` (52) : en-têtes JWT hostiles (`kid`, `jku`, `x5u`, `crit`), HS384/HS512,
confusion RS256/HS256 (jeton signé à la main), `iat`/`nbf` futurs, types de claims hostiles, jeton
géant refusé **avant** décodage, schémas d'authentification hostiles, IDOR croisé (4 comptes × 2
élèves × 2 routes), rôle forgé dans un jeton de compte (la base fait foi), inscription `admin`
impossible, jeton élève lié à un compte non lié, rejeu après suppression/expiration, **aucun
cookie** (CSRF sans objet), jeton en cookie ignoré, CORS fermé par défaut et limité aux origines
listées, homoglyphes / RTL / zero-width / pleine chasse refusés, traversée encodée, fixation de
séance sans prise de contrôle. Plus `test_review_session2.py`, `test_mika_api_audit.py`
(concurrence par threads), `test_import_harnais.py` (manifest régénéré après falsification).

## Contrôles (session 3)
| Contrôle | Résultat |
|---|---|
| bandit (≥ moyenne, désormais `migrations/` inclus) | 0 |
| pip-audit (runtime + dev) | 0 vulnérabilité connue |
| scan de secrets arbre | 0 à chaque commit |
| Incident évité | le scanner a détecté un exemple d'URL avec identifiants **factices** dans un brouillon de CLOUD_REVIEW_SESSION2.md ; reformulé et commit amendé avant toute revue (le commit remplacé n'est plus référencé par aucune branche) |

## Décisions restant à Mike (ajouts session 3)
D14 (compréhension ratée ⇒ réussite non comptée : choix fail-closed appliqué, à confirmer) ·
D15 (`session_id` : clé composite ou identifiant généré par le serveur).
