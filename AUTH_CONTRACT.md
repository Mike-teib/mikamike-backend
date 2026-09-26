# AUTH_CONTRACT — Authentification et autorisation (élève, parent, RGPD)

Code : `app/core/auth.py`, `app/api/v1/auth/router.py`, `paiement_comptes/liens.py`.
Tests : `tests_cloud/test_auth.py` (40 tests), `tests_cloud/test_review_session1.py` (R2-10/11).

## 1. Principe
Un **pseudo-id seul n'authentifie personne**. Toute route qui lit, écrit ou efface des données
d'un élève exige un jeton, et le droit est vérifié contre le pseudo-id **visé par la requête**.
Le **contrat public est inchangé** (chemins, corps, réponses) : seul l'en-tête
`Authorization: Bearer <jeton>` s'ajoute en mode `enforce`.

## 2. Mode (`MIKA_AUTH_MODE`, lu à chaque requête et validé au démarrage)
| Valeur | Effet |
|---|---|
| absente / `enforce` | **défaut fail-closed** : jeton obligatoire |
| `off` | contrat historique sans jeton (transition du front, anciens tests) — **refusé si `MIKA_ENV=production`** |
| autre | configuration invalide : refus de démarrer, 500 `auth_mal_configuree` à l'exécution |

Les suites historiques (`tests_mika`, `tests_paiement`, tests_cloud antérieurs) posent `MIKA_AUTH_MODE=off`
dans leur conftest ; `test_auth.py` repasse explicitement en `enforce`.

## 3. Jetons
| | Jeton de COMPTE | Jeton de SÉANCE ÉLÈVE |
|---|---|---|
| Émis par | `POST /api/v1/comptes/connexion` / `inscription` | `POST /api/v1/auth/eleve/jeton` |
| Claims | `sub`=id compte, `typ=compte`, `role`, `email`*, `iat`, `exp` | `iss=mikamike-backend`, `aud=mikamike-api`, `typ=mika-eleve`, `role=eleve`, `sub`=pseudo-id, `cid`=id du compte émetteur (session 3), `iat`, `exp`, `jti` |
| Clé | `MIKA_JWT_SECRET` | clé **dérivée** `HMAC-SHA256(MIKA_JWT_SECRET, "mikamike/jeton-eleve/v1")` |
| Durée | `MIKA_TOKEN_TTL_H` (168 h) | `MIKA_ELEVE_TOKEN_TTL_MIN` (120 min, borné [1, 720]) |
| Algorithme | HS256 uniquement (`alg` vérifié, `none` refusé) | idem |
| Claims obligatoires | `exp`, `sub` | `exp`, `iat`, `sub` (alphabet des identifiants), `aud`, `iss`, `typ`, `cid` |

\* e-mail dans le jeton de compte : décision D3 inchangée (à retirer).

Séparation des types : un jeton élève est refusé par `/comptes/moi` (typ ≠ compte, et signé avec une
autre clé) ; un jeton de compte n'est jamais accepté comme jeton élève (clé différente, typ, aud).

## 4. Émission d'un jeton élève
`POST /api/v1/auth/eleve/jeton` · corps `{"student_pseudo_id": "<id>"}` · en-tête : jeton de **compte**.
Autorisé si le compte est actif et **lié** à l'élève (`liens_compte_eleve`, relation `parent` ou
`eleve`, avec `compte.role` égal à la relation). Exigé **dans tous les modes**.
Réponse : `{"token", "token_type": "Bearer", "typ": "mika-eleve", "expires_in"}`.

## 5. Matrice d'autorisation
| Action | Routes | Jeton élève (même pseudo-id) | Compte parent lié | Compte élève titulaire |
|---|---|---|---|---|
| apprentissage | `POST /exercices/soumettre`, `GET /parcours/prochaine-etape`, `POST /parcours`, `GET /parcours/{u}/{l}/{s}`, `POST /escalier/etape`, `POST /memory/schedule`, `POST /memory/detect-fragile`, `POST /session/heartbeat\|save-state\|reconnect`, `GET /session/stream`, `/mika/session/*` | ✅ | ❌ 403 | ❌ 403 |
| lecture | `GET /parents/dashboard/{id}`, `GET /rgpd/export/{id}` | ✅ | ✅ | ✅ |
| effacement | `DELETE /rgpd/effacer/{id}` | ❌ 403 (D9) | ✅ | ❌ 403 |

Réponses : **401** jeton absent / invalide / expiré / mal signé / mauvais type / compte inconnu ou
désactivé ; **403** `acces_refuse` (identique pour « autre élève », « non lié », « mauvais rôle » : pas
d'oracle). `GET /session/stream` : séance existante d'un autre élève ⇒ 403.

L'effacement RGPD supprime aussi les liens compte ↔ élève (donnée relative à l'élève) : après
effacement, le parent n'a plus accès.

## 6. Compatibilité
- Jetons de compte émis avant cette branche (sans `typ`) : **acceptés** comme jetons de compte
  (jamais comme jetons élève). À retirer après expiration du TTL (168 h) suivant le déploiement.
- `exiger_session_active` (garde historique non câblée) : durcie (exp obligatoire, pas de rôle par
  défaut, refus des jetons de compte), conservée pour ses tests ; les routes utilisent `app/core/auth.py`.

## 7. Décisions produit ouvertes
| # | Décision | Défaut appliqué |
|---|---|---|
| D8 | Parcours de **création des liens** compte ↔ élève (invitation, vérification parentale, rattachement du pseudo-id) | aucune route publique ; fonction `paiement_comptes.liens.lier` seulement |
| D9 | Un élève (mineur) peut-il demander lui-même l'effacement ? (âge du consentement numérique : 15 ans en France) | non : parent lié uniquement |
| D11 | Révocation des jetons élève avant expiration (liste de `jti` révoqués) | non implémentée ; TTL court (2 h) |
| D12 | Date de passage du front en `enforce` (fin du mode `off`) | `off` interdit en production dès maintenant |

## 8. Hors périmètre / limites connues
- ~~Pas de rate-limiting~~ : **R7 livré en session 3** (§9).
- Le mode `off` reste un contrat **non authentifié** : il ne doit jamais être exposé sur Internet.

## 9. Session cloud 3 — évolutions
- **Révocation effective (S3-01)** : à chaque requête portant un jeton élève, le compte `cid` doit
  être actif ET encore lié à l'élève (relation = rôle du compte). Sinon 401 `jeton_revoque`.
  Conséquence : un effacement RGPD, la suppression d'un lien ou la désactivation du compte
  coupent immédiatement les jetons élève émis (D11 reste ouverte pour la révocation par `jti`).
- **Limitation R7** (`app/core/limitation.py`) : connexion par (IP, e-mail) et par IP ; inscriptions
  par IP ; émission de jetons élève par compte et par IP ; jetons invalides répétés par IP.
  Réponse 429 `trop_de_tentatives` + `Retry-After`. Jamais de blocage par l'e-mail seul (anti-DoS).
- **Connexion à temps constant** (S3-07) ; **inscription concurrente** ⇒ 400 (S3-08).
- Intégration front : FRONT_AUTH_INTEGRATION.md.
