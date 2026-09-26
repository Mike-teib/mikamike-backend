# FRONT_AUTH_INTEGRATION — Passer le front de `MIKA_AUTH_MODE=off` à `enforce`

> Contrat **préparé côté backend** (session cloud 3). Le frontend réel n'a **pas** été modifié.
> Références : AUTH_CONTRACT.md (matrice d'autorisation), MIKA_API_CONTRACT.md (tuteur),
> CLOUD_SECURITY_REPORT.md (limitation R7). Tous les chemins sont préfixés par `/api/v1`.

## 0. À savoir avant de commencer
| Point | Conséquence pour le front |
|---|---|
| `MIKA_ENV=production` **interdit** `MIKA_AUTH_MODE=off` (refus de démarrer) | le front doit être prêt **avant** tout déploiement de production |
| En mode `off`, l'en-tête `Authorization` est **ignoré** | le front peut l'envoyer dès maintenant, sans risque (migration progressive) |
| Aucune route publique ne crée de lien compte ↔ élève (décision **D8**) | **bloquant** pour `enforce` : sans lien, un parent ne peut obtenir aucun jeton élève |
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
  **généré par le front en UUID v4** (36 caractères, ≤ 64 exigés, 422 au-delà). Jamais un
  identifiant prévisible ni `default_session` : une séance créée par un autre élève sous le même
  identifiant répond 403 (S3-13, décision D15).
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
| 3 | **D8 livré** (création des liens) | écran de rattachement parent ↔ élève | un parent réel obtient un jeton élève |
| 4 | production `enforce` (`MIKA_ENV=production`, `MIKA_RATE_LIMIT=on`, `MIKA_PROXY_HOPS` réglé) | idem | supervision des 401/403/429 |
| 5 | +7 jours : retrait des jetons de compte sans `typ` (R14) | — | — |

## 8. Checklist de recette front
- [ ] aucune requête d'apprentissage sans `Authorization` (vérifier dans l'onglet réseau)
- [ ] jeton élève jamais persisté hors mémoire ; jeton de compte jamais en cookie/URL/logs
- [ ] 401 `jeton_expire` élève ⇒ ré-émission unique puis écran de connexion
- [ ] 401 `jeton_revoque` ⇒ retour au choix d'élève
- [ ] 429 ⇒ attente `Retry-After`, bouton désactivé
- [ ] `session_id` et `requete_id` en UUID v4 ; réessai = même `requete_id`
- [ ] effacement RGPD ⇒ l'élève disparaît, ses jetons sont purgés
- [ ] élève (compte `eleve`) : pas de bouton « effacer » (403)
