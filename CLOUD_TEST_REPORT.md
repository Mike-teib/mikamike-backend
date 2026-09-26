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
