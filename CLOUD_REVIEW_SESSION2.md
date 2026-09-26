# CLOUD_REVIEW_SESSION2 — Revue contradictoire de la PR #4 (session 2)

- Cible : `cloud/mikamike-session2-20260926` @ `db03ff41b707e7e5455bca3220128fa662816016` (PR #4)
- Date : 2026-09-26 · Relecteur : session cloud 3 · Branche des correctifs : `cloud/mikamike-session3-20260926`
- Méthode : lecture du code ajouté par la PR #4 (auth, tuteur, migrations, RGPD, import), **preuve de
  concept exécutée** pour chaque finding (aucun n'est retenu sans scénario reproduit), correctif,
  test de non-régression, mutant dédié.
- Anti-faux-positif : `tests_cloud/test_review_session2.py` a été rejoué sur db03ff4 (worktree
  jetable) : **21 tests échouent**, les **2 qui passent sont les témoins positifs**
  (`test_s3_01_temoin_…`, `test_s3_06_temoin_…`) qui décrivent un comportement sain à préserver.
- Mutants : 10 nouveaux (session 3) + 2 mutants de la session 2 devenus **inapplicables** après
  correctif, réécrits ; les 12 rejoués : **12/12 tués**.

## Synthèse

| Gravité | Nombre | Corrigés | Documentés (décision / front) |
|---|---|---|---|
| P0 | 0 | — | — |
| P1 | 3 | 3 | 0 |
| P2 | 11 | 9 | 2 |
| **Total** | **14** | **12** | **2** |

Barème identique à CLOUD_REVIEW_SESSION1.md : **P0** contournement d'un verrou de sûreté / DoS
trivial ; **P1** faille de sécurité ou RGPD, perte d'intégrité, déploiement impossible ; **P2**
robustesse, contrat, test trompeur.

---

## P1

### S3-01 — Le jeton élève survit à l'effacement RGPD, au retrait du lien et à la désactivation du compte
- SEVERITY : P1 (RGPD / autorisation)
- FILE : `app/core/auth.py` · FUNCTION : `emettre_jeton_eleve`, `decoder`, `autoriser` ; `app/api/v1/session/router.py` · `stream_notifications_sse`
- SCENARIO : parent lié ⇒ jeton élève (TTL 2 h) ; le parent **efface** les données (`DELETE /rgpd/effacer`,
  qui supprime aussi les liens) ; le jeton élève réécrit aussitôt (`POST /memory/schedule` ⇒ 200).
  Idem si le compte parent est désactivé : `GET /rgpd/export` ⇒ 200 avec le jeton élève.
- EXPECTED : 401 dès que le compte émetteur n'est plus actif ou plus lié à l'élève.
- ACTUAL : 200 pendant toute la durée du jeton ; des données sont **recréées** pour un élève effacé.
- FIX : claim `cid` (id du compte émetteur, entier, obligatoire) ; à **chaque** requête élève :
  compte actif ET lien `relation == compte.role` toujours présent, sinon 401 `jeton_revoque`.
  Le flux SSE passe aussi par la garde (il lisait `g.qui` sans la revérification).
- TEST : `test_s3_01_*` (4 refus + 1 témoin). Mutants `jeton_eleve_lien_non_reverifie`,
  `jeton_eleve_compte_desactive`.
- Contrat : le jeton élève porte un claim de plus (`cid`) — le front ne lit pas les claims
  (FRONT_AUTH_INTEGRATION.md). `test_jeton_emis_ne_contient_aucune_pii` mis à jour en conséquence
  (`cid` n'est pas une PII : identifiant numérique interne).
- STATUT : **corrigé**. Coût : 2 requêtes indexées (billing) par requête élève.

### S3-02 — Toute commande de migration plante si l'URL de base contient `%`
- SEVERITY : P1 (déploiement impossible)
- FILE : `app/db/migrations.py` · FUNCTION : `config`
- SCENARIO : URL PostgreSQL dont le mot de passe contient un caractère encodé (`%40` pour `@`) ou chemin SQLite
  contenant `%20`. `python -m tools.db upgrade` (et le démarrage en `MIKA_DB_INIT=check`, qui appelle `head()`).
- EXPECTED : migration appliquée.
- ACTUAL : `ValueError: invalid interpolation syntax` (ConfigParser interpole `%`) ⇒ refus de démarrer.
- FIX : `%` doublé avant `set_main_option`.
- TEST : `test_s3_02_url_avec_pourcent`. Mutant `url_alembic_non_echappee`. **Corrigé.**

### S3-03 — Migration interrompue sur SQLite : tables orphelines, reprise impossible
- SEVERITY : P1 (intégrité du schéma)
- FILE : `migrations/{mika,billing}/env.py` · FUNCTION : `run_migrations_online` ; `app/db/migrations.py`
- SCENARIO : `upgrade` m0002 → m0003 coupé après la 1re `CREATE TABLE` (coupure simulée).
- EXPECTED : révision atomique (rien de m0003 ne subsiste), `upgrade` relançable.
- ACTUAL : `mika_tutorat_sessions` créée, `alembic_version` resté à m0002 ; relance ⇒
  `OperationalError: table mika_tutorat_sessions already exists` (réparation manuelle).
  Cause : pysqlite valide implicitement avant chaque DDL, la transaction d'Alembic est illusoire.
- FIX : `ddl_transactionnel_sqlite(engine)` (pilote en autocommit + `BEGIN` émis explicitement,
  recette SQLAlchemy) dans les deux `env.py`.
- TEST : `test_s3_03_migration_interrompue_atomique_et_reprenable` (+ MIGRATION_VALIDATION_REPORT.md).
  Mutant `ddl_sqlite_non_transactionnel`. **Corrigé.**

## P2

### S3-04 — Double soumission concurrente : 409 au lieu du rejeu idempotent
- FILE : `app/api/v1/tutorat/service.py` · `transition`
- SCENARIO : double clic : la même requête (`requete_id`, même corps) arrive deux fois ; la 2e lit
  le journal AVANT que la 1re ne valide, puis perd la course sur `UPDATE … WHERE version = v`.
- EXPECTED : `200` + `rejeu: true` (MIKA_API_CONTRACT §4). ACTUAL : `409 version_perimee`.
- FIX : après échec de l'UPDATE conditionnel, relire le journal d'idempotence avant de conclure au conflit.
- TEST : `test_s3_04_double_soumission_concurrente_rejouee` (course reproduite de façon déterministe).
  Mutant `double_soumission_409`. **Corrigé.**

### S3-05 — État de tutorat corrompu servi tel quel / 500 non maîtrisée
- FILE : `service.py` · `etat_depuis_json`
- SCENARIO : `etat_json` avec `tentatives="x"`, `messages="abc"`, `avec_aide=1`, `tentatives=-1`.
- EXPECTED : 500 `etat_tutorat_illisible` (erreur contrôlée, sans trace).
- ACTUAL : `GET` renvoie 200 avec l'état corrompu (`"messages": ["a","b","c"]`) ; `answer` ⇒ 500 brute (`TypeError`).
- FIX : validation stricte des types et bornes de chaque champ persistant. TEST : `test_s3_05_*` (5 cas).
  Mutant `etat_corrompu_accepte`. **Corrigé.**

### S3-06 — Compréhension vérifiée FAUSSE comptée comme réussite
- FILE : `app/curriculum/pedagogie/tuteur.py` · `repondre_comprehension`, `_succes`, `_consolider` ;
  `service.py` · `_verser_au_learning_engine`
- SCENARIO : aide → bonne réponse → question de compréhension ratée → … → fin.
- EXPECTED : niveau `FRAGILE`, pas de « Bravo », tentative versée `est_correct=False`.
- ACTUAL : `niveau_estime=ACQUIS_ASSISTE`, message « Bravo ! », tentative `est_correct=True`.
- FIX : compréhension infirmée ⇒ `FRAGILE` (non effacé par un 2e succès) ; réussite = résolu ET
  compréhension non infirmée. Choix pédagogique **fail-closed** (à confirmer par Mike, cf. D14).
- TEST : `test_s3_06_*` (+ témoin : compréhension réussie ⇒ « Bravo »). Mutant
  `comprehension_ratee_comptee_reussie`. **Corrigé.**

### S3-07 — Oracle de timing à la connexion (énumération des comptes)
- FILE : `paiement_comptes/crud_billing.py` · `authentifier`
- SCENARIO (mesuré) : `POST /comptes/connexion` mauvais mot de passe : e-mail existant **295 ms**,
  e-mail inconnu **5 ms** ; compte désactivé : aucun bcrypt non plus.
- EXPECTED : même coût dans tous les cas. FIX : vérification systématique contre un hash leurre
  (secret aléatoire jetable, calculé une fois). TEST : `test_s3_07_connexion_temps_constant`.
  Mutant `connexion_sans_leurre`. **Corrigé.** (L'inscription reste un oracle d'existence :
  `email_deja_utilise` — inhérent au parcours, à traiter avec la vérification d'e-mail, D3.)

### S3-08 — Inscription concurrente du même e-mail : 500
- FILE : `crud_billing.py` · `creer_compte`
- SCENARIO : deux inscriptions simultanées passent le contrôle « e-mail libre ». ACTUAL : `IntegrityError` non rattrapée (500).
- FIX : la contrainte UNIQUE tranche ⇒ `ValueError("email_deja_utilise")` (400). TEST : `test_s3_08_*`. **Corrigé.**

### S3-09 — Export RGPD incomplet
- FILE : `app/api/v1/rgpd/router.py` · `exporter_donnees_eleve`
- SCENARIO : élève ayant utilisé le tuteur. ACTUAL : `mika_tutorat_requetes` (dans `TABLES_ELEVE`, donc
  effacée) **absente** de l'export ; liens compte ↔ élève absents.
- FIX : `requetes_tutorat_mika` et `liens_comptes` (relation + date, jamais l'e-mail) ; table
  `CLES_EXPORT` + test qui exige qu'**aucune** table de `TABLES_ELEVE` ne manque à l'export.
- TEST : `test_s3_09_*`. Mutant `export_rgpd_sans_journal`. **Corrigé.**

### S3-10 — Identifiants API de 128 caractères persistés dans des colonnes `String(64)`
- FILES : `session/router.py` (`session_id`), `memory/router.py` (`notion_id`), `escalier/router.py`
  (`competence_objectif`, `exercice_id`) ; `tutorat/service.py` (troncature `[:64]` silencieuse)
- SCENARIO : `session_id` de 65 à 128 caractères. ACTUAL : SQLite stocke sans contrôle ; PostgreSQL
  lève `StringDataRightTruncation` ⇒ 500. Côté tuteur, deux notions de même préfixe de 64 caractères
  partageaient le même état de maîtrise.
- FIX : type `Identifiant64` (422) ; catalogue du tuteur : identifiant > 64 ⇒ contenu refusé
  (`identifiant_trop_long`), jamais tronqué. TEST : `test_s3_10_*` (dont un test **statique**
  bornes API ≤ longueur de colonne). Mutant `identifiant_64_elargi`. **Corrigé.**

### S3-11 — `mutation_check` mutait l'arbre de travail
- FILE : `tools/mutation_check.py`
- SCENARIO : arrêt brutal pendant un mutant (SIGKILL, timeout CI, Ctrl-C hors `finally`) ⇒ **bug
  injecté laissé dans le code source** (commitable) ; un pytest lancé en parallèle testait du code muté.
- FIX : mutation sur une **copie jetable** du dépôt ; option `--seulement a,b` pour rejouer un sous-ensemble.
- TEST : `test_s3_11_mutation_sur_copie_jetable`, `test_s3_11_mutants_session3_applicables`
  (échoue dès qu'un mutant devient inapplicable — c'est ce qui aurait signalé les 2 mutants
  de la session 2 cassés par les correctifs de cette session). **Corrigé.**

### S3-12 — Tests négatifs sans témoin positif (faux positifs possibles)
- FILE : `tests_cloud/test_auth.py` (`_eleve_claims` + 5 tests paramétrés)
- SCENARIO : les tests forgent des claims altérés et attendent 401 ; aucun test ne montre que les
  claims **non altérés** passent. Après S3-01 (`cid` obligatoire), ils auraient tous continué de
  passer… pour une autre raison (claim manquant). Le défaut est désormais complété (`cid`) et un
  témoin prouve l'acceptation des claims intacts.
- TEST : `test_s3_12_temoin_claims_forges_valides_acceptes`. **Corrigé.**

### S3-13 — Squat de `session_id` (DoS ciblé) — DOCUMENTÉ
- FILE : `app/api/v1/session/session_manager.py` · `heartbeat`, `sauvegarder_etat_partiel`, `reconnecter_et_restaurer`
- SCENARIO : `session_id` choisi par le client, clé primaire **globale** : un élève B qui crée d'abord
  la séance `default_session` (défaut du flux SSE) ou l'identifiant prévisible d'un élève A ⇒ tous les
  appels de A reçoivent 403 `session_non_autorisee`.
- EXPECTED : isolation par élève. Pourquoi non corrigé ici : la correction propre (clé primaire
  composite `(eleve_hmac, session_id)`, migration m0004) change le comportement verrouillé par les
  tests historiques B1 (403 attendu) et dépend de la façon dont le front génère l'identifiant.
- MITIGATION immédiate (front) : `session_id` = UUID v4 aléatoire (FRONT_AUTH_INTEGRATION.md §6).
  Décision **D15** (Mike) : clé composite ou identifiant généré par le serveur.

### S3-14 — Troncature bcrypt à 72 octets — DOCUMENTÉ
- FILE : `crud_billing.py` · `hacher_mot_de_passe`
- SCENARIO : deux mots de passe identiques sur leurs 72 premiers octets sont équivalents.
- Pourquoi non corrigé : changer le schéma de hachage invalide les hash existants (migration de
  hash à la connexion à décider). Impact faible (≥ 72 octets déjà). Borne d'entrée conservée (200).

## Points vérifiés SANS finding
- `decoder` : jeton élève signé avec la clé dérivée mais `typ`/`role` faux ⇒ 401 (l'`HTTPException`
  n'est pas avalée par `except PyJWTError`) ; jeton de compte portant `aud` ⇒ 401 (PyJWT refuse
  un `aud` non attendu).
- Effacement RGPD : ordre (données puis liens) **reprenable** — si la 2e base échoue, le parent
  garde l'accès et peut relancer ; relance ⇒ 404 idempotent.
- Tuteur : transitions bornées (question → indices → méthodes → correction ; ≤ 2 reformulations ;
  anti-répétition ⇒ REVUE_HUMAINE) : pas de croissance non bornée de `messages`.
- Idempotence de `start` (id déterministe) et collision inter-élèves : correctes.
- Verrou optimiste : `UPDATE … WHERE version = v` atomique (SQLite et PostgreSQL).
- `LimiteTailleCorps` : `Content-Length` non numérique ⇒ 413 ; chunked compté en flux.
