# @mikamike/frontend-contract

Contrat front **exécutable** de MikaMike (élèves mineurs + parents) : types TypeScript exacts,
client `fetch` de référence, machines d'état **pures**, validateur runtime et tests contractuels.
Sans framework, sans dépendance d'exécution (seule devDependency : `typescript` 5.9.3, épinglée).

Source de vérité : `contrat_front/contrat.json` (46 appels réels enregistrés par
`tools/contrat_front.py`) et le code des routes. Documents liés : `FRONT_IMPLEMENTATION_PACK.md`,
`FRONT_AUTH_INTEGRATION.md`, `AUTH_CONTRACT.md`, `MIKA_API_CONTRACT.md`.

| Fichier | Rôle |
|---|---|
| `types.ts` | requêtes, réponses, énumérations (`EtatMaitrise`, `NiveauProgression`, `ActionTuteur`…), codes d'erreur |
| `validators.ts` | validateur runtime léger, typé contre `types.ts` (`objet<T>` exige toutes les clés de `T`) |
| `client.ts` | `MikaClient`, `ApiError`, `TokenStore` + `MemoryTokenStore`, `ROUTES`, `COUVERTURE_CONTRAT` |
| `auth-state.ts` | machines compte, vérification d'adresse, séance élève |
| `parent-link-state.ts` | machine du rattachement parent ↔ enfant par invitation (D8) |
| `examples/` | un fichier par parcours (inscription, invitation, séance Mika, dashboard, RGPD) |
| `contract-tests/` | tests `node:test` (unitaires, contractuels, intégration) |

## Installation

Node ≥ 22.18 (exécution native des `.ts` par effacement des types : aucune étape de build).

```sh
cd frontend-contract
npm ci                 # installe uniquement typescript 5.9.3
npm run typecheck      # tsc --noEmit (strict, noUncheckedIndexedAccess, exactOptionalPropertyTypes…)
npm test               # node --test "contract-tests/*.test.ts"
```

> `node --test contract-tests/` (un répertoire) n'est pas accepté par Node 22 : le script utilise
> le motif `contract-tests/*.test.ts`, résolu par Node lui-même.

Les fichiers n'utilisent que de la syntaxe **effaçable** (`erasableSyntaxOnly` : ni `enum`, ni
`namespace`, ni propriété de paramètre) : un front (Vite, Next, esbuild, Node) les importe tels quels.
Les tests lisent `../../contrat_front/contrat.json` ; hors du dépôt backend, définir
`MIKA_CONTRAT_JSON=/chemin/vers/contrat.json`.

## Usage

```ts
import { ApiError, MikaClient, MemoryTokenStore } from "@mikamike/frontend-contract/client";

const client = new MikaClient({
  baseUrl: "https://staging.example",        // /api/v1 est ajouté
  fetchImpl: fetch,                          // injectable (tests, SSR, intercepteurs)
  tokenStore: new MemoryTokenStore(),        // aucun stockage imposé
  validation: "souple",                      // "stricte" en recette : toute clé inconnue échoue
  surErreurAuth: (err, porteur) => dispatch({ type: "ERREUR_AUTH", code: err.code ?? "" }),
});

await client.connexion({ email, mot_de_passe });          // mémorise le jeton de compte
await client.obtenirJetonEleve(pseudo);                   // jeton élève (mémoire uniquement)
const r = await client.soumettreExercice({ exercice_id, student_pseudo_id: pseudo, reponse: "5*x" });
if (r.progression?.niveau === "FRAGILE") { /* guidage pas à pas */ }
```

Une méthode par opération : `inscription`, `connexion`, `moi`, `etatVerificationEmail`,
`demanderVerification`, `verifierEmail`, `changerMotDePasse`, `changerEmail`, `deconnexion`,
`exportCompte`, `supprimerCompte`, `jetonEleve` / `obtenirJetonEleve`, `emettreInvitation`,
`accepterInvitation`, `nouvelleSession`, `heartbeat`, `sauverEtat`, `reconnecter`,
`soumettreExercice`, `prochaineEtape`, `tutoratStart|Answer|Help|Comprehension`, `tutoratEtat`,
`dashboardParent`, `exportRgpdEleve`, `effacerRgpdEleve`. `COUVERTURE_CONTRAT` relie chacun des
46 appels de `contrat.json` à sa méthode (vérifié par les tests et par pytest).

Option par appel `{ porteur: "compte" | "eleve" }` : ex. export RGPD avec le jeton élève.

### Stockage des jetons

Le client ne décide pas où vivent les jetons : il passe par `TokenStore`.
- **Jeton de compte** : mémoire ; `sessionStorage` toléré (survit au rechargement d'onglet).
- **Jeton élève** : **mémoire uniquement** ; au rechargement, il est ré-émis.
- Jamais de cookie, d'URL, de `localStorage` partagé ni de journal.

```ts
class SessionStorageTokenStore extends MemoryTokenStore {
  override lireJetonCompte() { return sessionStorage.getItem("mika.compte"); }
  override ecrireJetonCompte(j: string | null) {
    j === null ? sessionStorage.removeItem("mika.compte") : sessionStorage.setItem("mika.compte", j);
  }
  // jetons élève : hérités de MemoryTokenStore (mémoire)
}
```

Le client **n'écrit jamais** dans la console (testé) ; `ApiError.message` ne contient que
`HTTP <statut> <code>`.

## Machines d'état

Fonctions pures `transition(etat, evenement) → etat` : aucun effet, aucune horloge implicite
(l'appelant fournit `maintenant`). Un événement invalide lève `TransitionRefusee`
(`peutTransitionner…` pour tester sans lever). Les jetons ne sont jamais dans les états.

### Compte (`auth-state.ts` : `transition`)
```
ANONYME ──INSCRIPTION_REUSSIE──▶ INSCRIT_NON_VERIFIE ──EMAIL_CONFIRME──▶ VERIFIE ──PROFIL_CHARGE──▶ CONNECTE
ANONYME ──CONNEXION_REUSSIE──▶ CONNECTE (email_verifie) | INSCRIT_NON_VERIFIE (sinon)
ANONYME ──EMAIL_CONFIRME (lien ouvert hors session)──▶ VERIFIE(sans jeton) ──CONNEXION_REUSSIE──▶ CONNECTE
CONNECTE ──EMAIL_CHANGE──▶ INSCRIT_NON_VERIFIE          CONNECTE ──MOT_DE_PASSE_CHANGE──▶ CONNECTE (jeton remplacé)
état avec jeton ──ERREUR_AUTH 401 jeton_expire──▶ ANONYME(raison: expiration)
état avec jeton ──ERREUR_AUTH 401 jeton_revoque──▶ ANONYME(raison: revocation)
état avec jeton ──ERREUR_AUTH 401 token_invalide|jeton_invalide|token_absent|jeton_requis|compte_inconnu──▶ ANONYME(raison)
état avec jeton ──DECONNEXION──▶ ANONYME(raison: deconnexion)
état avec jeton ──COMPTE_SUPPRIME──▶ SUPPRIME (terminal : tout événement est refusé)
```
`401 session_inactivite_5min` n'est **pas** une perte de session de compte (refusé ici).

### Vérification d'adresse (`transitionVerification`)
```
NON_DEMANDEE ──DEMANDE_ACCEPTEE (202)──▶ ENVOYEE ──CONFIRMATION_REUSSIE (200)──▶ VERIFIEE
      │                                  └──CONFIRMATION_REFUSEE (400 jeton_invalide_ou_expire)──▶ JETON_INVALIDE
      └──DEMANDE_ECHOUEE (503 courriel_indisponible)──▶ ECHEC_ENVOI
ECHEC_ENVOI | JETON_INVALIDE ──DEMANDE_ACCEPTEE──▶ ENVOYEE        VERIFIEE ──ADRESSE_CHANGEE──▶ ENVOYEE
tout état ──STATUT_LU (GET /comptes/verification-email)──▶ état du serveur
```

### Séance élève Mika (`transitionSeance`)
```
AUCUNE ──JETON_OBTENU──▶ JETON_PRET ──SEANCE_CREEE (POST /session/nouvelle 201)──▶ OUVERTE
OUVERTE ──ERREUR 401 session_inactivite_5min──▶ EXPIREE(inactivite) ──SEANCE_CREEE──▶ OUVERTE
OUVERTE ──ERREUR 401 jeton_expire | TEMPS ≥ expireA──▶ EXPIREE(jeton_expire) ──JETON_OBTENU (une fois)──▶ JETON_PRET
   (jeton ré-émis qui expire à son tour sans succès intermédiaire ⇒ reemissionTentee ⇒ reconnexion)
* ──ERREUR 401 jeton_revoque──▶ REVOQUEE (retour au choix d'enfant)
OUVERTE ──ERREUR 404 session_inconnue──▶ JETON_PRET        * ──FERMER──▶ AUCUNE
```

### Rattachement parent (`parent-link-state.ts` : `transitionLien`)
```
AUCUNE ──CODE_EMIS──▶ CODE_EMIS ──ACCEPTATION_REUSSIE (201)──▶ ACCEPTEE  ⇒ dashboardAccessible()
CODE_EMIS ──403 email_non_verifie──▶ REFUSEE_EMAIL_NON_VERIFIE ──(après vérification) ACCEPTATION_REUSSIE──▶ ACCEPTEE
CODE_EMIS ──400 invitation_invalide──▶ INVALIDE        CODE_EMIS ──TEMPS ≥ expire_le──▶ EXPIREE
CODE_EMIS ──409 deja_lie──▶ ACCEPTEE(dejaLie)
ACCEPTEE ──DASHBOARD_REFUSE 403 | LIEN_REVOQUE──▶ LIEN_REVOQUE (dashboard 403 : retirer l'enfant)
EXPIREE | INVALIDE | LIEN_REVOQUE ──CODE_EMIS──▶ CODE_EMIS
```

## Expiration et révocation

| Réponse | Porteur | Ce que fait le client | Ce que fait le front |
|---|---|---|---|
| 401 `jeton_expire` | élève | purge, **une** ré-émission avec le jeton de compte, un seul nouvel essai | si l'échec persiste : reconnexion |
| 401 `jeton_revoque` | élève | purge le jeton élève | retour au choix d'enfant (lien supprimé, effacement RGPD, mot de passe du parent changé) |
| 401 `jeton_revoque` / `jeton_expire` / `token_invalide` / `compte_inconnu` | compte | purge tous les jetons, appelle `surErreurAuth` | `transition(…, ERREUR_AUTH)` ⇒ ANONYME(raison) |
| 401 `session_inactivite_5min` | élève | rien | `POST /session/nouvelle` |
| 429 `trop_de_tentatives` | — | `ApiError.retryAfter` (secondes) | compte à rebours, bouton désactivé, jamais de boucle |

Le jeton élève est renouvelé automatiquement 5 min avant `expires_in` (`margeRenouvellementMs`).
Changement de mot de passe ou d'adresse : le client **remplace** le jeton de compte et purge les
jetons élève (révoqués côté serveur). Déconnexion : globale (tous les appareils), purge locale
même si le serveur répond 401.

## Séance Mika et tuteur

1. `obtenirJetonEleve(pseudo)` puis `nouvelleSession({ user_id })` : le `session_id` vient
   **toujours** du serveur (D15) ; un identifiant inventé ⇒ 404 `session_inconnue`.
2. `heartbeat` toutes les 60 s, `sauverEtat` à chaque modification de l'ardoise, `reconnecter` au
   retour réseau.
3. `soumettreExercice` renvoie `etat_maitrise` (7 valeurs historiques : `INCONNU`, `FRAGILE`,
   `EN_COURS`, `ACQUIS_ASSISTE`, `ACQUIS_AUTONOME`, `A_REVOIR`, `MAITRISE`) et, depuis la session 5,
   `progression` **optionnel** (`{moteur, niveau: NON_EVALUEE|NON_ACQUISE|FRAGILE|EN_COURS|MAITRISEE,
   prochaine_action, observations, raisons[]}`).
4. Tuteur : `requete_id` = `nouveauRequeteId()` (UUID v4) par action, conservé pour les réessais ;
   `version` = dernière reçue ; 409 `version_perimee` ⇒ `tutoratEtat` puis nouvelle action avec un
   **nouveau** `requete_id` (`examples/seance-mika.ts`). 404 `exercice_indisponible` tant
   qu'aucun contenu prouvé n'est importé.

## Tableau de bord parent

`dashboardParent(pseudo)` (compte parent lié). Le schéma est **fermé** côté serveur et côté
validateur (toute clé supplémentaire est refusée même en mode souple) : `pseudo_id` +
`statistiques_pedagogiques` (`exercices_tentes`, `exercices_reussis`, `taux_reussite` ∈ [0, 1],
`competences{tentatives, reussites, etat}`, `niveau_actuel`). 403 `acces_refuse` ⇒ lien révoqué.

## RGPD

| Action | Méthode | Porteur | Erreurs |
|---|---|---|---|
| Export des données de l'enfant | `exportRgpdEleve(pseudo)` | compte lié ou élève | 403, 404 `aucune_donnee_trouvee_pour_cet_identifiant` |
| Effacement des données de l'enfant | `effacerRgpdEleve(pseudo)` | compte **parent** lié (D9) | 403, 404 `aucune_donnee_a_effacer` |
| Export du compte | `exportCompte()` | compte | 401 |
| Suppression du compte | `supprimerCompte({mot_de_passe, confirmation: true})` | compte | 403 `mot_de_passe_incorrect`, 409 `abonnement_en_cours`, 422 |

Après effacement : les liens sont supprimés (dashboard 403) et **tous** les jetons élève émis sont
révoqués (401 `jeton_revoque`). Après suppression du compte : état `SUPPRIME` (terminal), l'ancien
jeton répond 401 `compte_inconnu`. Les données d'apprentissage de l'enfant ne sont pas touchées
par la suppression d'un compte parent (elles s'effacent par `/rgpd/effacer`).

## Codes d'erreur

`ApiError { status, code, detail, retryAfter, versionCourante, erreursValidation }` ; `code` =
`detail` (chaîne) ou `detail.code` (409 `version_perimee`) ; null pour une 422 (voir
`erreursValidation`). Liste complète : `CODES_ERREUR` dans `types.ts`.

| Statut | Codes |
|---|---|
| 400 | `email_deja_utilise`, `email_invalide`, `mot_de_passe_trop_court`, `email_indisponible`, `email_identique`, `jeton_invalide_ou_expire`, `invitation_invalide` |
| 401 | routes `/comptes/*` : `token_absent`, `token_invalide`, `compte_inconnu`, `jeton_revoque`, `identifiants_invalides` ; autres routes : `jeton_requis`, `jeton_invalide`, `jeton_expire`, `jeton_revoque`, `jeton_compte_requis`, `compte_inconnu` ; séance : `session_inactivite_5min` |
| 403 | `acces_refuse`, `email_non_verifie`, `mot_de_passe_incorrect`, `session_non_autorisee` |
| 404 | `session_inconnue`, `exercice_inconnu`, `exercice_indisponible`, `tutorat_inconnu`, `aucune_donnee_trouvee_pour_cet_identifiant`, `aucune_donnee_a_effacer` |
| 409 | `abonnement_en_cours`, `trop_d_invitations_actives`, `deja_lie`, `version_perimee` (+ `version_courante`), `tutorat_termine`, `comprehension_attendue`, `comprehension_non_demandee`, `comprehension_non_verifiable`, `contenu_retire`, `requete_id_reutilise_avec_un_autre_contenu`, `conflit_de_creation` |
| 413 | `etat_session_trop_volumineux` |
| 422 | validation Pydantic (`detail` = tableau `{loc, msg, type}`) |
| 429 | `trop_de_tentatives` + en-tête `Retry-After` |
| 503 | `courriel_indisponible` (renvoi du courriel de vérification : fournisseur en panne) |
| 500 | `auth_mal_configuree`, `limitation_mal_configuree`, `etat_tutorat_illisible`, … (message générique) |

Ne jamais afficher un code brut : le traduire (un message unique pour « code invalide ou expiré »).

## Tests

| Fichier | Contenu |
|---|---|
| `contract-tests/auth-state.test.ts`, `parent-link-state.test.ts` | matrices **complètes** état × événement, états terminaux, refus, pureté |
| `contract-tests/contract.test.ts` | pour chacun des 46 appels : méthode client, route, porteur, corps envoyé = corps enregistré, réponse validée en mode strict ou `ApiError` typée ; ré-émission du jeton élève, purges, absence de log |
| `contract-tests/examples.test.ts` | les exemples s'exécutent |
| `contract-tests/integration.test.ts` | parcours complet contre un **vrai** serveur si `MIKA_CONTRACT_BASE_URL` est défini (sinon ignoré explicitement) |

Le jeton de vérification n'est **jamais** renvoyé par HTTP (courriel uniquement) et le premier code
d'invitation est émis par l'opérateur : les étapes correspondantes du test d'intégration exigent
un harnais côté serveur, `MIKA_CONTRACT_HELPER` (tableau JSON argv) imprimant la valeur demandée.
`tests_cloud/test_frontend_contract_pkg.py` lance le serveur uvicorn (mode `enforce`, courriel
`faux`), fournit ce harnais et exige 0 étape ignorée. Sans harnais, seules les étapes publiques
sont jouées. **Jamais contre la production.**
