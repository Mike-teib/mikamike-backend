# CLOUD_TEST_REPORT — Rapport de tests

Environnement : Python 3.11, venv isolé (`./setup.sh`), hors ligne, secrets de test factices,
bases SQLite jetables. Commande : `python -m pytest -q`.

## Baseline (avant toute modification, commit `232e464`)
```
TESTS_TOTAL_BEFORE = 62
TESTS_PASS_BEFORE  = 62
TESTS_FAIL_BEFORE  = 0
TESTS_ERROR_BEFORE = 0
```
Note : dans l'image cloud, la suite **ne démarrait pas** avec les paquets système (`cryptography`
système cassé → panique pyo3 à l'import de python-jose). Contournement reproductible : venv isolé.

## Après mission
```
TESTS_TOTAL_AFTER = 3462   (62 historiques + 3400 nouveaux, tests_cloud/)
TESTS_PASS_AFTER  = 3462
TESTS_FAIL_AFTER  = 0
TESTS_ERROR_AFTER = 0
Durée ≈ 14 s
```
Les 62 tests historiques sont conservés. Modifications apportées aux tests historiques :
uniquement le retrait d'imports inutilisés (ruff F401) et le remplacement de `from jose import jwt`
par `import jwt` (PyJWT, même API). **Aucune assertion modifiée, affaiblie ou supprimée.**

## Nouveaux tests (tests_cloud/)
| Fichier | Tests | Objet |
|---|---|---|
| test_api_regressions.py | 30 | non-régression B1–B10 (IDOR, RGPD, repli matière, JWT, Stripe, LE-06, escalier…), validation d'entrées |
| test_curriculum_model.py | 41 | IDs stables, versions, provenance (4 statuts), verrou de génération, 20 contrôles structurels (1 mutation = 1 anomalie), migration |
| test_text_quality.py | 32 | 11 textes sains (dont formules) + 18 textes défectueux, source, réparations sans perte |
| test_math_guard.py | 51 | 1/10→0,1, exposants, parenthèses…, équivalence SymPy, 11 entrées hostiles, formes requises |
| test_verifiers_sciences.py | 35 | PC (unités/dimensions/CS/homogénéité), SVT, techno, ES, dispatch |
| test_exercices_quiz.py | 27 | verrous de création, incohérences, fuite, doublons, quiz (double bonne réponse, ambiguïté…) |
| test_pedagogie_mika.py | 3161 | démarche du tuteur + propriétés sur 3 125 séquences exhaustives + récurrence |
| test_backlog_audit_import.py | 18 | backlog reproductible, audit dédup, import (checkpoint, reprise, altération, PII), perf |
| test_secret_scan.py | 5 | scanner (détection sans divulgation, faux positifs, arbre propre) |

## Tests négatifs / mutation (Phase 24)
`python -m tools.mutation_check` injecte 18 bugs et vérifie que la suite échoue :
**18/18 mutants tués** (notion non prouvée acceptée, source fictive acceptée en prod, texte tronqué
accepté, texte suspect utilisable, mauvais chapitre, exercice dupliqué, formule cassée, quiz
ambigu, mauvaise unité, résultat sans unité, réponse vide, niveau incohérent, VALID par défaut,
aide comptée pour la maîtrise, solution immédiate, IDOR session, RGPD incomplet, repli de matière).

## Bugs corrigés (avec test de non-régression)
B1 IDOR session · B2 effacement RGPD incomplet · B3 repli silencieux vers Maths · B4 prérequis
jamais vérifiés · B5 JWT `sub` ⇒ 500 · B6 fuite d'exception Stripe · B7 entrées mémoire non bornées ·
B8 succès aidés comptés vers MAITRISE · B9 échec imputé à la mauvaise compétence · B10 500 sur état
corrompu · + tri non déterministe des tentatives à horodatage égal · + élisions françaises en SVT ·
+ répétition de messages du tuteur sur réponses vides répétées (trouvé par le test de propriétés).

## Contrôles qualité
| Contrôle | Résultat |
|---|---|
| ruff (config projet) | 0 erreur |
| bandit (≥ moyenne) | 0 |
| pip-audit | 0 vulnérabilité connue |
| scan de secrets (arbre) | 0 |
| content_check | OK |
| rapports ×2 + diff | identiques (reproductibles) |
| CI GitHub | verte sur les commits poussés |

---

# Session cloud 2 (2026-09-26) — branche `cloud/mikamike-session2-20260926`

```
TESTS_TOTAL = 3767   (session 1 : 3462 ; +305)
TESTS_PASS  = 3767
TESTS_FAIL  = 0
TESTS_ERROR = 0
Durée ≈ 47 s (tests_mika 55 · tests_paiement 7 · tests_cloud 3705)
```

## Nouveaux tests
| Fichier | Tests | Objet |
|---|---|---|
| test_review_session1.py | 55 | un test par finding de la revue (26 échouaient sur fb77fb8 ; SymPy : bloquait l'ancien code) |
| test_migrations.py | 11 | import sans DDL, migrations ≡ modèles, downgrade/upgrade, démarrage fail-closed, adoption de base historique |
| test_auth.py | 40 | toutes les routes élève fermées sans jeton (énumération OpenAPI), A≠B lecture/écriture/effacement, jeton absent/expiré/mal signé/`alg=none`/claims, confusion compte↔élève, rôles, propriétaire, modes |
| test_mika_api.py | 106 | API tuteur : présentation sans réponse, aide graduée, compréhension vérifiée serveur, idempotence, versions, propriété, RGPD ; 81 séquences de propriétés (`avec_aide` monotone, version +1, difficulté non croissante, aucune fuite) |
| test_import_v2_integrite.py | 46 | manifest v2 épinglé, altération, SHA/taille, rôles, symlink, manifests SHA256, intégrité croisée, backlog hiérarchique, dépôt/rollback |
| test_performance.py | 8 | nb de requêtes SQL constant, calculs par item, pic mémoire du hachage et des lignes géantes, flux de 5000 notions |
| test_attaques.py | 37 | corps énorme (413), Unicode hostile, traversée, charges SQL, JSON imbriqué, DoS SymPy via l'API, erreurs sans trace ni secret |
| + 2 tests | 2 | isolent des règles que les tests de la session 1 ne distinguaient pas (R2-29) |

Tests historiques : **aucune assertion modifiée ni affaiblie**. Une seule préparation corrigée
(`test_timeout_5min_inactivite_expiration`, faux positif R2-05) ; conftests : bases créées
explicitement, `MIKA_AUTH_MODE=off`/`MIKA_DB_INIT=none` pour conserver le contrat historique.

## Mutation (`python -m tools.mutation_check`)
39 mutants (18 session 1 + 21 session 2), chacun sur une suite ciblée, baseline verte exigée,
erreurs de collecte non comptées comme « tuées ».
- Le nouveau job CI a révélé que **2 mutants de la session 1 survivaient déjà** sur fb77fb8 (le
  « 18/18 » publié était faux) et qu'un 3e était devenu inapplicable : corrigés (R2-29).
- 1 mutant de la session 2 (`generation_malgre_anomalie`) survivait : test ajouté.
- Les 4 correctifs sont vérifiés individuellement (mutant rejoué ⇒ TUÉ).
- **Exécution complète en CI sur 53794c4 : 39/39 mutants tués** (run CI n° 21, tous jobs verts).

## Contrôles qualité (session 2)
| Contrôle | Résultat |
|---|---|
| ruff | 0 erreur |
| bandit (≥ moyenne) | 0 |
| pip-audit (dont alembic 1.20.0) | 0 vulnérabilité connue |
| scan de secrets arbre / historique | 0 / uniquement le repli faible historique connu (c01d9ba, documenté) |
| content_check | OK |
| rapports ×2 + diff | identiques |
| migrations (CI) | upgrade → status → downgrade base → upgrade |

---

# Session cloud 3 (2026-09-26) — branche `cloud/mikamike-session3-20260926` (PR #5)

```
TESTS_TOTAL = 4017   (session 2 : 3767 ; +250)
TESTS_PASS  = 4017
TESTS_FAIL  = 0
TESTS_ERROR = 0
```

## Nouveaux tests
| Fichier | Tests | Objet |
|---|---|---|
| test_review_session2.py | 26 | un test par finding de la revue de la PR #4 (21 échouent sur db03ff4, 2 témoins passent) |
| test_limitation.py | 31 | R7 : fenêtre, seuil, backoff, reset, mémoire bornée, anti-DoS (IP unique et botnet), X-Forwarded-For, jetons |
| test_equivalence.py | 44 | R6 : équations, fractions, puissances, expressions, unités, forme vs fond, ambigu ⇒ revue, catalogue en lecture seule |
| test_migrations_validation.py | 12 | base neuve/historique, stamp, pas à pas, downgrade, version incorrecte, interruption (×3), downgrade interrompu |
| test_mika_api_audit.py | 39 | contrat exact, non-divulgation des aides futures, concurrence par threads, rejeu, plans invalides, prérequis, état corrompu |
| test_import_harnais.py | 40 | pipeline synthétique complet, 12 défauts injectés (étape exacte, jamais publiés), partiel, reprise, idempotence, dépôt |
| test_import_perf.py | 6 | croissance linéaire temps/mémoire, flux, checkpoint O(fichiers), reprise sur 6 000 notions |
| test_securite_s3.py | 52 | JWT hostiles, IDOR croisé, CSRF/CORS, rôles, Unicode, rejeu, fixation de séance |

## Tests existants modifiés (préparation uniquement, justifiée)
- `test_mika_api.py::test_ownership_en_mode_enforce` : les jetons élève sont émis pour un compte lié
  (S3-01 exige `cid`). Assertions inchangées.
- `test_auth.py::_eleve_claims` : `cid` ajouté au jeu de claims de base (sinon les tests négatifs
  échouaient pour une autre raison — S3-12) ; `test_jeton_emis_ne_contient_aucune_pii` : ensemble de
  claims attendu complété par `cid` (évolution de contrat documentée, pas un affaiblissement).
- `test_backlog_audit_import.py` (3 appels) : `autoriser_fictif=True`, la fixture étant fictive (S3-15).
- conftests : remise à zéro des compteurs R7 entre tests.

## Mutation
**Exécution complète locale : 73/73 mutants tués** (15,5 min ; 0 survivant, 0 inapplicable).
34 mutants ajoutés en session 3 (+ 3 réécrits car devenus inapplicables), chacun vérifié tué
individuellement lors de son ajout ; `mutation_check` mute désormais une **copie jetable** (S3-11)
et accepte `--seulement`.

## Contrôles qualité (session 3)
| Contrôle | Résultat |
|---|---|
| ruff | 0 |
| bandit (≥ moyenne, `migrations/` inclus) | 0 |
| pip-audit | 0 vulnérabilité connue |
| scan de secrets arbre | 0 |
| audit R6 (catalogue historique) | 0 faux positif historique |

## Décisions de Mike appliquées (fin de session 3)
```
TESTS_TOTAL = 4065   (+48 : invitations D8 30, D5 15, E2E parent/enfant 2, séances D15 +1 net)
TESTS_PASS  = 4065 · FAIL 0 · ERROR 0
```
| Fichier | Tests | Objet |
|---|---|---|
| test_invitations.py | 30 | D8 : code 120 bits unique, jamais en clair, usage unique, expiration, confirmation stricte, rôle, déjà lié, force brute, quota, concurrence, RGPD, outil opérateur, aucune autre création de lien |
| test_equivalence.py (+15) | 59 | D5 : équivalences démontrées acceptées, ambigus refusés, désactivable, jamais d'exception |
| test_e2e_parent_enfant.py | 2 | D12 : flux complet en enforce (inscription → invitation → validation → jeton → séance → exercice → tuteur → second parent → dashboard → export → effacement → révocation → R7) ; configuration production |
| test_securite_s3.py | 53 | D15 : fixation impossible en enforce, identifiants serveur uniques 192 bits |

Préparations de tests adaptées (assertions de comportement inchangées) : `test_session_stream_proprietaire`
(séance créée par `POST /session/nouvelle`), nombre de tables billing (3 → 4, b0003) et nom de
la révision head billing dans les tests de migration.
Mutants des décisions : 9/9 tués (`d8_*` ×6, `d5_ambigu_accepte`, `d15_*` ×2).
