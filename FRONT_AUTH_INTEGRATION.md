# FRONT_AUTH_INTEGRATION — Passer le front de `MIKA_AUTH_MODE=off` à `enforce`

> Contrat **préparé côté backend** (session cloud 3). Le frontend réel n'a **pas** été modifié.
> Références : AUTH_CONTRACT.md (matrice d'autorisation), MIKA_API_CONTRACT.md (tuteur),
> CLOUD_SECURITY_REPORT.md (limitation R7). Tous les chemins sont préfixés par `/api/v1`.

## 0. À savoir avant de commencer
| Point | Conséquence pour le front |
|---|---|
| `MIKA_ENV=production` **interdit** `MIKA_AUTH_MODE=off` (refus de démarrer) | le front doit être prêt **avant** tout déploiement de production |
| En mode `off`, l'en-tête `Authorization` est **ignoré** | le front peut l'envoyer dès maintenant, sans risque (migration progressive) |
| Les liens compte ↔ élève se créent **uniquement par invitation** (décision **D8**, §2 bis) | écran « saisir le code d'invitation » côté parent ; écran « inviter un parent » côté enfant |
| Aucun cookie : authentification par **en-tête** uniquement | pas de CSRF classique ; ne pas mettre les jetons en cookie |
| Pas de route `refresh` | renouvellement = nouvelle émission (§3) |

## 1. Deux jetons
| | Jeton de COMPTE | Jeton de SÉANCE ÉLÈVE |
|---|---|---|
| Obtenu par | `POST /comptes/connexion` ou `/comptes/inscription` | `POST /auth/eleve/jeton` (avec le jeton de compte) |
| Durée | `MIKA_TOKEN_TTL_H` (168 h par défaut) | `expires_in` secondes (7 200 par défaut, 12 h max) |
| Sert à | profil (`/comptes/moi`), tableau de bord parent, export RGPD, **effacement RGPD**, émettre des jetons élève | toutes les routes d'**apprentissage** de CET élève (exercices, parcours, escalier, mémoire, séance, tuteur Mika) + lecture |
| Révoqué si | compte désactivé / supprimé | compte émetteur désactivé, **lien supprimé** ou **effacement RGPD** (S3-01) ⇒ 401 `jeton_revoque` |

Le front ne lit **jamais** le contenu des jetons (claims susceptibles d'évoluer) : il utilise
`expires_in` et les codes d'erreur.

## 2. Flux de connexion
```
1. POST /comptes/connexion {email, mot_de_passe}
   200 → {token: <compte>, compte: {id, email, prenom, role, statut_abonnement}}
   401 identifiants_invalides   429 trop_de_tentatives (+ Retry-After)
2. Choix de l'élève (pseudo-id déjà connu du front)
3. POST /auth/eleve/jeton {student_pseudo_id}   Authorization: Bearer <compte>
   200 → {token: <élève>, token_type: "Bearer", typ: "mika-eleve", expires_in: 7200}
   401 (jeton de compte absent/invalide/expiré)   403 acces_refuse (élève non lié)   429
4. Routes d'apprentissage : Authorization: Bearer <élève>
```

## 2 bis. Rattacher un parent à un enfant (D8)
```
Enfant (jeton élève) : POST /liens/invitations {student_pseudo_id}
   201 → {code: "ABCD-EFGH-…", expires_in: 172800, usage_unique: true}   ← afficher UNE fois
   (premier rattachement d'un enfant sans aucun parent : code remis par l'établissement / le support)
Parent (jeton de compte) : POST /liens/accepter {code, confirmation: true}
   201 → {statut: "lien_cree", relation: "parent", student_pseudo_id}   ← mémoriser le pseudo-id
   400 invitation_invalide (inconnu/utilisé/expiré)  409 deja_lie  429 (trop d'essais)
```
Le code est tolérant à la casse et aux tirets. `confirmation` doit être le booléen JSON `true`
(case à cocher « je suis le parent de cet enfant » explicitement cochée). Ne jamais stocker le code.

## 3. Stockage, expiration, renouvellement, reconnexion
- **Jeton de compte** : en mémoire ; `sessionStorage` toléré pour survivre au rechargement
  d'onglet. Jamais `localStorage` partagé, jamais cookie, jamais dans une URL ni dans les logs.
- **Jeton élève** : **en mémoire uniquement** ; au rechargement, le ré-émettre (étape 3).
- **Renouvellement élève** : ré-émettre à `expires_in − 5 min`, ou sur 401 `jeton_expire`
  (une seule tentative, puis retour à l'écran de connexion). Quota : 30 émissions / 10 min / compte.
- **Expiration du compte** : 401 `jeton_expire` sur une route « compte » ⇒ reconnexion.
- **Reconnexion réseau** : rejouer les requêtes du tuteur avec le **même** `requete_id`
  (idempotence, §6) ; ne pas rejouer une connexion en boucle (limitation R7).

## 4. En-tête et gestion des erreurs
Toujours `Authorization: Bearer <jeton>` (schéma `Bearer`, un espace, jeton ≤ 4 096 caractères).

| Statut / `detail` | Signification | Action front |
|---|---|---|
| 401 `jeton_requis` | en-tête absent | ajouter le jeton ; bug du front |
| 401 `jeton_invalide` | jeton mal formé / mauvais type / mauvaise signature | purger le jeton, reconnexion |
| 401 `jeton_expire` | expiré | élève : ré-émettre (1 fois) ; compte : reconnexion |
| 401 `jeton_revoque` | lien supprimé, compte désactivé, effacement RGPD | purger le jeton élève, retour au choix d'élève |
| 401 `compte_inconnu` | compte supprimé/désactivé | purger tout, reconnexion |
| 403 `acces_refuse` | jeton valide mais pas le droit (autre élève, non lié, mauvais rôle) | message « accès non autorisé » ; **ne pas** réessayer |
| 429 `trop_de_tentatives` | limitation R7 | attendre `Retry-After` secondes ; désactiver le bouton |
| 500 `auth_mal_configuree` / `limitation_mal_configuree` | configuration serveur | message générique, alerte exploitation |

Une source qui envoie ≥ 50 jetons invalides en 5 min est freinée (429) : ne pas boucler sur un
jeton refusé.

```js
// Enveloppe fetch minimale (illustrative, non livrée au front).
async function api(path, {jeton, ...init} = {}) {
  const r = await fetch(`/api/v1${path}`, {...init, headers: {"Content-Type": "application/json",
    ...(jeton ? {Authorization: `Bearer ${jeton}`} : {}), ...init.headers}});
  if (r.status === 429) throw {attente: Number(r.headers.get("Retry-After") || 60)};
  if (r.status === 401) { const {detail} = await r.json(); throw {auth: detail}; }
  if (r.status === 403) throw {interdit: true};
  return r;
}
```

## 5. Tableau de bord parent et RGPD
| Action | Route | Jeton accepté |
|---|---|---|
| Tableau de bord | `GET /parents/dashboard/{pseudo}` | compte **parent lié**, compte **élève titulaire**, ou jeton élève du même pseudo |
| Export RGPD | `GET /rgpd/export/{pseudo}` | idem (404 `aucune_donnee_trouvee_pour_cet_identifiant` si vide) |
| Effacement RGPD | `DELETE /rgpd/effacer/{pseudo}` | **compte parent lié uniquement** (D9) |

Après un effacement : les liens compte ↔ élève sont supprimés ⇒ le parent n'a plus accès
(403) et **tous les jetons élève émis sont révoqués** (401 `jeton_revoque`). Le front doit
purger le jeton élève et retirer l'élève de la liste. L'export contient désormais aussi
`requetes_tutorat_mika` et `liens_comptes` (relation + date, jamais d'e-mail).

## 6. Séances et tuteur Mika
- **Séance** (`/session/heartbeat|save-state|reconnect`, `GET /session/stream`) : `session_id`
  **obtenu du serveur** par `POST /session/nouvelle {user_id}` (201, 192 bits aléatoires,
  décision D15). En `enforce`, tout autre identifiant ⇒ 404 `session_inconnue` (plus de
  `default_session`, plus d'identifiant généré par le front).
- **Tuteur** (`/mika/session/start|answer|help|comprehension`, `GET /mika/session/{id}`) :
  jeton élève du même `student_pseudo_id`.
  - `requete_id` : **UUID v4 par action**, conservé pour les réessais (même corps ⇒ même
    réponse, `rejeu: true`) ; même `requete_id` avec un autre corps ⇒ 409.
  - `version` : celle de la dernière réponse ; 409 `{"code": "version_perimee", "version_courante": n}`
    ⇒ `GET` du tutorat puis nouvelle action avec un **nouveau** `requete_id`.
  - 409 `tutorat_termine` / `comprehension_attendue` / `comprehension_non_demandee` : suivre `etat`.
  - 404 `exercice_indisponible` : aucun contenu prouvé (normal tant que R1 n'est pas fait).
  - Double clic : sans risque (rejeu idempotent, S3-04).

## 7. Migration progressive (proposition, date = décision D12)
| Étape | Backend | Front | Critère de passage |
|---|---|---|---|
| 0 | `off` (dev/staging) | inchangé | — |
| 1 | `off` | envoie **déjà** `Authorization` (compte + élève) partout ; gère 401/403/429 | tests e2e verts en `off` |
| 2 | staging `enforce` | idem | parcours complets verts : connexion → jeton élève → exercices → tuteur → dashboard → export → effacement |
| 3 | D8 livré côté backend (invitations) | écrans « inviter » / « saisir le code » (§2 bis), `POST /session/nouvelle` | un parent réel obtient un jeton élève via un code |
| 4 | production `enforce` (`MIKA_ENV=production`, `MIKA_RATE_LIMIT=on`, `MIKA_PROXY_HOPS` réglé) | idem | supervision des 401/403/429 |
| 5 | +7 jours : retrait des jetons de compte sans `typ` (R14) | — | — |

**Règle de passage (décision D12)** : `MIKA_AUTH_MODE=enforce` en production **uniquement quand**
(1) le front est conforme à ce document, (2) le flux parent/enfant complet fonctionne, (3) les
tests E2E sont verts — côté backend `tests_cloud/test_e2e_parent_enfant.py` (vert en CI) ET les
tests E2E du front (à fournir). Tant que ces trois conditions ne sont pas réunies : **aucun
déploiement de production** (le mode `off` y est refusé au démarrage).

## 8. Checklist de recette front
- [ ] aucune requête d'apprentissage sans `Authorization` (vérifier dans l'onglet réseau)
- [ ] jeton élève jamais persisté hors mémoire ; jeton de compte jamais en cookie/URL/logs
- [ ] 401 `jeton_expire` élève ⇒ ré-émission unique puis écran de connexion
- [ ] 401 `jeton_revoque` ⇒ retour au choix d'élève
- [ ] 429 ⇒ attente `Retry-After`, bouton désactivé
- [ ] `session_id` obtenu par `POST /session/nouvelle` ; `requete_id` en UUID v4 ; réessai = même `requete_id`
- [ ] rattachement parent par code d'invitation (§2 bis), confirmation cochée explicitement
- [ ] effacement RGPD ⇒ l'élève disparaît, ses jetons sont purgés
- [ ] élève (compte `eleve`) : pas de bouton « effacer » (403)
