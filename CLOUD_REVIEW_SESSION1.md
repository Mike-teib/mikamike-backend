# CLOUD_REVIEW_SESSION1 — Revue contradictoire de la PR #3 (session 1)

- Cible : `cloud/mikamike-autonomous-20260926` @ `fb77fb874960bfaff9d7cfd67044d3419f05fe6b`
- Date : 2026-09-26 · Relecteur : session cloud 2 · Méthode : lecture de tout le code applicatif et
  de la chaîne `app/curriculum`, **preuves de concept exécutées** (aucun finding n'est retenu sans
  scénario reproduit), puis correctif + test de non-régression.
- Contrôle anti-faux-positif : `tests_cloud/test_review_session1.py` a été rejoué sur l'ancien head
  (worktree jetable) : **26 tests échouent** sur fb77fb8 ; les 4 qui passent sont des témoins positifs
  (comportement sain qui doit être préservé). Les tests SymPy (R2-03) n'y ont pas été rejoués car ils
  **bloquent** l'ancien code (> 20 s par entrée, mesuré).

## Synthèse

| Gravité | Nombre | Corrigés dans cette branche |
|---|---|---|
| P0 | 2 | 2 |
| P1 | 13 | 13 (dont 2 via lots dédiés : migrations, authentification) |
| P2 | 13 | 10 corrigés, 3 documentés (décision / design) |
| **Total** | **28** | |

Barème : **P0** = contournement d'un verrou de sûreté ou déni de service trivial ; **P1** = faille
de sécurité/RGPD, perte d'intégrité ou crash sur entrée hostile ; **P2** = dette, robustesse,
performance, test trompeur.

---

## P0

### R2-01 — Le « verrou unique de génération » croit le statut de texte DÉCLARÉ
- SEVERITY : P0
- FILE : `app/curriculum/provenance.py`
- LINE/FUNCTION : `autorisation_generation`
- SCENARIO : notion au texte tronqué `"[FICTIF] Comparer, ranger et encadrer des"` déclarée
  `statut_texte=TEXT_EXACT`, extrait de source contenant ce fragment.
- EXPECTED : génération refusée (texte tronqué).
- ACTUAL : `Autorisation(autorise=True, raisons=[])` — la génération d'exercices/quiz est autorisée
  et le backlog la compte en `NEED_EXERCISE`. `structure.valider_referentiel` recalcule le texte, mais
  `creer_exercice`, `valider_question` et `calculer_backlog` ne passent que par ce verrou.
- MINIMAL_FIX : recalculer `analyser_texte(notion.texte)` dans le verrou ; refuser si non utilisable.
- TEST_REQUIRED : `test_r2_01_texte_tronque_declare_exact_refuse` (+ témoin `..._texte_sain_reste_autorise`).
- STATUT : **corrigé**.

### R2-03 — Déni de service et crash du vérificateur SymPy
- SEVERITY : P0 (dès que le tuteur est exposé ; P1 tant qu'il ne l'est pas)
- FILE : `app/curriculum/verifiers/maths.py`
- LINE/FUNCTION : `normaliser` (gardes regex), `_difference_nulle`
- SCENARIO (mesuré) : `9^(59*59*59*59)` 8,4 s ; `(x+y+z+1)^60`, `10^(59)^(59)` (contourne la regex
  « puissances imbriquées » grâce aux parenthèses), `tan(x)^60+sin(x)^60+cos(x)^60` : > 20 s (tués) ;
  `exp(exp(exp(59)))` : `OverflowError` **non rattrapée**.
- EXPECTED : réponse en temps borné, verdict `NEEDS_HUMAN_REVIEW`, jamais d'exception.
- ACTUAL : blocage du worker / exception propagée (500 côté API).
- MINIMAL_FIX : contrôle de complexité sur l'arbre **non évalué** avant toute évaluation (exposant
  littéral borné, pas de puissance dans un exposant, produit cumulé des exposants ≤ 60, taille du
  développement ≤ 2000 termes, profondeur de fonctions ≤ 2, puissance de transcendante ≤ 8, ≤ 120
  nœuds) ; test numérique **avant** `simplify` ; `simplify` seulement si ≤ 60 opérations ;
  `OverflowError/RecursionError/MemoryError` ⇒ indécidable.
- TEST_REQUIRED : `test_r2_03_*` (10 entrées hostiles × 2 côtés, borne 3 s ; 5 expressions légitimes
  toujours VALID : `2^(n+1)`, `x^(1/2)`, `(x-1)(x+1)`, `sin²+cos²`, `x^-2`).
- STATUT : **corrigé**.

## P1

### R2-02 — Preuve issue de la source d'un AUTRE programme acceptée
- FILE : `app/curriculum/provenance.py` · `autorisation_generation` / `evaluer_preuve`
- SCENARIO : notion du programme A dont la preuve cite la source enregistrée d'un programme B.
- EXPECTED : refus (la docstring promettait QUARANTINED pour « source d'une autre notion »).
- ACTUAL : `autorise=True`. La variable `source` du programme était calculée puis ignorée.
- MINIMAL_FIX : exiger `preuve.source_id == programme.source_id`.
- TEST_REQUIRED : `test_r2_02_preuve_d_un_autre_programme_refusee`. **Corrigé.**

### R2-04 — Importeur « fail-closed » qui plante sur contenu hostile
- FILE : `app/curriculum/importers.py` · `importer`, `lire_manifest`, `_lignes_jsonl`, `_charger_checkpoint`
- SCENARIOS : (a) JSON imbriqué 100 000 niveaux ⇒ `RecursionError` non rattrapée ; (b) entrée de
  manifest non-objet (`[42]`) ⇒ `TypeError` ; (c) manifest racine liste ⇒ `AttributeError` ;
  (d) checkpoint corrompu ⇒ `JSONDecodeError` ; (e) deux mappings contradictoires pour une notion ⇒
  le dernier gagne **silencieusement** ; (f) téléphone fixe (01…05, 09) non dépisté ; (g) une ligne
  JSONL géante était lue **entièrement** en mémoire avant le contrôle de longueur ; (h) la doc
  affirmait « un fichier DONE n'est jamais retraité » alors qu'il est relu (comportement correct,
  doc fausse).
- EXPECTED : statut `FAILED`/`REJECTED` avec raison, jamais d'exception ; lecture bornée.
- MINIMAL_FIX : capture `RecursionError/ValueError/TypeError/UnicodeDecodeError` ⇒ FAILED
  (`json_trop_imbrique`), validation de type du manifest, checkpoint illisible ignoré,
  `readline(MAX_LIGNE+1)`, taille max du référentiel (50 Mo), anomalie `MAPPING_CONTRADICTOIRE`,
  motif téléphone 0[1-9], parcours des clés itératif, doc corrigée.
- TEST_REQUIRED : `test_r2_04_*` (8 tests). **Corrigé.**

### R2-05 — Heartbeat : effet de bord AVANT le contrôle de propriétaire (+ test historique faux positif)
- FILE : `app/api/v1/session/session_manager.py` · `GestionnaireSession.heartbeat`
- SCENARIO : un tiers envoie un heartbeat sur le `session_id` expiré d'un élève.
- EXPECTED : 403, aucune modification.
- ACTUAL : 401 `session_inactivite_5min` **et** `is_active=False` écrit en base (le tiers désactive la
  séance d'autrui ; oracle 401/403 sur l'existence et l'expiration).
- **Faux positif associé** : `tests_mika/test_session_robustness.py::test_timeout_5min_inactivite_expiration`
  insérait une séance avec `eleve_hmac="hmac_timeout"` puis interrogeait avec `user_id="eleve_timeout"`
  (HMAC différent) : il validait exactement le comportement fautif. Sa **préparation** est corrigée
  (vrai HMAC du propriétaire) ; ses assertions (401 + détail) sont inchangées.
- MINIMAL_FIX : `_verifier_proprietaire` en premier.
- TEST_REQUIRED : `test_r2_05_tiers_ne_peut_pas_desactiver_seance_expiree`. **Corrigé.**

### R2-06 — État de séance fusionné non borné
- FILE : `session_manager.py` · `sauvegarder_etat_partiel`
- SCENARIO : 3 sauvegardes successives de 1,9 Mo sur des clés différentes.
- EXPECTED : 413 dès que l'état dépasse 2 Mo.
- ACTUAL : 200 ×3, **5,7 Mo stockés** (seule la charge utile était mesurée).
- MINIMAL_FIX : mesurer l'état fusionné. TEST : `test_r2_06_etat_fusionne_borne`. **Corrigé.**

### R2-07 — Tables créées au chargement des modules (`create_all` ×5)
- FILES : `mikamike/store.py` (`init_db()` en fin de module), `memory/router.py`, `session/router.py`,
  `rgpd/router.py` (crée les tables d'AUTRES modules), `paiement_comptes/models_billing.py`.
- SCENARIO : `import main` sur une base de production ⇒ DDL exécuté sans migration, sans version ;
  une colonne ajoutée au modèle n'est jamais appliquée à une table existante (`create_all` ne modifie pas).
- EXPECTED : schéma versionné, appliqué explicitement.
- MINIMAL_FIX : migrations Alembic + suppression des `create_all` à l'import (cf. CLOUD_DB_MIGRATION_PLAN.md).
- TEST_REQUIRED : schéma migré ≡ modèles ; import sans DDL. **Corrigé (lot B).**

### R2-08 — Tuteur : « j'ai compris » clôt un exercice jamais résolu
- FILE : `app/curriculum/pedagogie/tuteur.py` · `repondre_comprehension`, `demander_aide`
- SCENARIO : `demarrer` puis `repondre_comprehension(etat, True)` sans aucune réponse.
- EXPECTED : refus (compréhension non demandée).
- ACTUAL : CONSOLIDATION, séance terminée. De plus la compréhension était un booléen **déclaré par
  l'appelant** (non vérifiable côté serveur) et `demander_aide` restait actif après la fin.
- MINIMAL_FIX : état `attend_comprehension`, `TransitionInvalide` sinon ; clé
  `PlanGuidage.reponse_comprehension` vérifiée côté serveur (`repondre_comprehension_texte`) ;
  `demander_aide` inerte après la fin.
- TEST_REQUIRED : `test_r2_08_*` (3 tests). **Corrigé.**

### R2-09 — Fuite de la réponse par les diagnostics d'erreurs fréquentes
- FILE : `tuteur.py` · `valider_plan`
- SCENARIO : `erreurs_frequentes={"7,10": "la bonne réponse était 0,7"}` : le diagnostic est affiché
  à la 1re erreur (IDENTIFIER_BLOCAGE), avant toute aide.
- EXPECTED : plan refusé (`aide_divulgue_la_reponse`).
- ACTUAL : plan accepté — seuls indices/questions/méthodes étaient contrôlés.
- MINIMAL_FIX : contrôler aussi les diagnostics et la question de compréhension vs sa clé.
- TEST_REQUIRED : `test_r2_09_*`. **Corrigé.**

### R2-10 — Garde `exiger_session_active` : jeton sans expiration, rôle par défaut, confusion de jetons
- FILE : `app/api/v1/security/fail_closed.py`
- SCENARIOS : jeton sans `exp` accepté **à vie** ; rôle absent ⇒ `"eleve"` par défaut (fail-open) ;
  jeton de **compte** parent (`sub` = id numérique) accepté comme séance élève.
- EXPECTED : 401 dans les trois cas.
- MINIMAL_FIX : `require=["exp","sub"]`, rôle obligatoire ∈ {eleve, parent}, refus des jetons
  `typ=compte`/porteurs d'e-mail. (Remplacé pour les routes par la couche `app/core/auth.py`, lot C.)
- TEST_REQUIRED : `test_r2_10_*` (4 refus + 1 témoin). **Corrigé.**

### R2-11 — `compte_courant` accepte tout jeton signé à `sub` numérique, sans `exp` exigé
- FILE : `paiement_comptes/router_comptes.py`
- SCENARIO : jeton `typ=mika-eleve` à `sub` numérique ; jeton de compte sans `exp`.
- EXPECTED : 401. ACTUAL : 200 (profil du compte renvoyé).
- MINIMAL_FIX : claim `typ=compte` émis ; tout autre `typ` refusé ; `exp` exigé. Jetons historiques
  sans `typ` encore acceptés (compatibilité, cf. AUTH_CONTRACT.md).
- TEST_REQUIRED : `test_r2_11_*`. **Corrigé.**

### R2-12 — `mutation_check` : résultats non significatifs possibles
- FILE : `tools/mutation_check.py`
- SCENARIOS : (a) aucune exécution de référence : si la suite est déjà rouge, **tous** les mutants
  sont « tués » ; (b) un mutant qui casse l'import (erreur de collecte, code 2) est compté « tué »
  sans qu'aucune assertion ne l'ait détecté.
- MINIMAL_FIX : baseline verte obligatoire (sinon code 2) ; seul le code pytest 1 vaut « tué ».
- TEST_REQUIRED : `test_r2_12_*`. **Corrigé.**

### R2-18 — Routes élève / RGPD non authentifiées (S1, connu session 1)
- FILES : routeurs `exercices`, `parents`, `parcours`, `escalier`, `memory`, `session`, `rgpd`.
- SCENARIO : quiconque connaît un pseudo-id exporte ou **efface** les données d'un élève.
- MINIMAL_FIX : couche d'autorisation fail-closed configurable (cf. AUTH_CONTRACT.md).
- **Corrigé (lot C).**

### R2-19 — Contenus importés (exercices/quiz) jamais recoupés avec le référentiel
- FILE : `app/curriculum/importers.py`
- SCENARIO : `index_contenus` avec un exercice sur une notion inexistante ou de matière différente ⇒
  statut VALIDATED (seul le schéma était vérifié), puis compté `WITH_EXERCISE` au backlog.
- MINIMAL_FIX : contrôles d'intégrité croisés (cf. `app/curriculum/integrite.py`). **Corrigé (lot E).**

### R2-20 — Pas de borne sur la taille du corps des requêtes
- FILE : `main.py`
- SCENARIO : corps JSON de centaines de Mo : entièrement lu et parsé avant la validation Pydantic.
- MINIMAL_FIX : middleware ASGI de taille maximale (413). **Corrigé (lot F).**

## P2

| # | Fichier / fonction | Scénario → constat | Correctif | Test | Statut |
|---|---|---|---|---|---|
| R2-13 | `tools/verifier_manifest.py` | chemin `../../etc/passwd` lu et haché ; code retour 0 même si CHANGED | statut `OUTSIDE`, code 1 si écart | `test_r2_13_*` | corrigé |
| R2-14 | `tests_mika/conftest.py` | tables mémoire/session non réinitialisées entre tests (fuite d'état) | reset des 4 bases | suite complète | corrigé |
| R2-15 | 6 routeurs + `spaced_repetition.py`, `session_manager.py` | 6 copies de `_hmac`, 2 lectures de secret mortes (effet de bord à l'import) | `app/core/pseudonymisation.py` unique | suite complète | corrigé |
| R2-16 | `crud.agreger_dashboard` | tout l'historique chargé en RAM à chaque affichage | `GROUP BY` SQL | `test_r2_16_dashboard_agrege` | corrigé |
| R2-17 | `crud.get_tentatives` | ordre non déterministe à horodatage égal | tri secondaire `id` | — | corrigé |
| R2-21 | `tools/rapports.py` | pose un secret **littéral** de repli (`setdefault`) — contraire à la politique fail-closed, et inutile | supprimé | exécution sans secret | corrigé |
| R2-22 | `audit.auditer` | Jaccard par paire recalcule les 3-grammes à chaque comparaison | cache par item | `test_perf_*` | corrigé (lot F) |
| R2-23 | `exercices.valider_exercice` | recherche de doublon linéaire sur toute la banque (O(N²) en import) | index par empreinte | `test_perf_*` | corrigé (lot F) |
| R2-24 | `backlog` / `exercices` | l'« oracle » compare la réponse attendue **à elle-même** : il prouve seulement que le vérificateur sait la lire, pas qu'elle est juste | sémantique renommée et documentée (WAITING_ORACLE = « non vérifiable automatiquement ») ; la justesse reste une revue humaine | — | documenté |
| R2-25 | `test_pedagogie_mika.py` propriété 2 | « jamais la réponse avant la correction » ne cherche que la chaîne `"0,7"` (pas `7/10`, `0.7`) | propriété renforcée côté API (réponse jamais présente dans le JSON avant correction, toutes graphies équivalentes) | `test_mika_api.py` | corrigé |
| R2-26 | `tuteur.repondre` | réponse à l'exercice acceptée pendant l'attente de compréhension | l'API refuse (409) ; moteur documenté | `test_mika_api.py` | corrigé (API) |
| R2-27 | `session_manager.reconnecter_et_restaurer` | une séance **expirée** est réactivée par `reconnect` (le heartbeat la refuse) | cohérence à trancher (produit : « reconnexion gracieuse ») | — | documenté (D10) |
| R2-28 | `router_comptes.creer_token` | e-mail dans le JWT (S2, connu) | décision D3 inchangée | — | documenté |

## Points vérifiés SANS finding (revus, aucun défaut démontré)
- `security_config` : fail-closed correct, aucune fuite de valeur dans les messages.
- `algorithms=["HS256"]` fixé partout (pas d'`alg=none`, pas de confusion RS/HS).
- RGPD : registre `TABLES_ELEVE` + test qui échoue si une table `eleve_hmac` est oubliée : efficace
  (la nouvelle table de tutorat a été détectée par ce test lors du lot D).
- `text_quality._repetition` : pire cas mesuré 0,08 s pour 2000 caractères (pas de quadratique pathologique).
- `math_guard.proteger` : 10 000 opérandes en 3 ms (pas de regex catastrophique).
- Corps JSON imbriqué 50 000 niveaux : FastAPI répond 400 (pas de 500).
- `structure._cycles_prerequis` : DFS itératif, pas de récursion.
