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
- Les 4 correctifs sont vérifiés individuellement (mutant rejoué ⇒ TUÉ) ; résultat de l'exécution
  complète : cf. job CI « mutation » sur le dernier commit.

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
