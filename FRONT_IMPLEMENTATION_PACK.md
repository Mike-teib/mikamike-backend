# FRONT_IMPLEMENTATION_PACK — Ce que le front doit implémenter (backend session 4)

> Le frontend n'est **pas** dans ce dépôt : rien n'a été inventé côté front. Ce pack décrit le
> contrat que le backend **teste** et fournit de quoi le vérifier côté front.
> Source de vérité des formes : `contrat_front/contrat.json` (46 appels, régénéré depuis le vrai
> flux ; la CI échoue si l'API dérive). Complète FRONT_AUTH_INTEGRATION.md et MIKA_API_CONTRACT.md.

## 0. Outils livrés
| Fichier | Usage |
|---|---|
| `contrat_front/contrat.json` | statut + forme de chaque réponse (types ; codes d'erreur et énumérations à l'identique) — pour mocks (MSW…), tests de client, revue |
| `contrat_front/verifier_contrat.mjs` | `node contrat_front/verifier_contrat.mjs https://staging…` : rejoue la partie publique du contrat contre un serveur (Node ≥ 18, sans dépendance). **Jamais contre la production.** |
| `python -m tools.contrat_front --verifier` | côté backend : échoue si l'API ne respecte plus le contrat |

## 1. Endpoints (préfixe `/api/v1`)
Auth : **C** = jeton de compte, **E** = jeton élève, **—** = aucun.
| Écran / action | Méthode · chemin | Auth | Corps | Succès | Erreurs à gérer |
|---|---|---|---|---|---|
| Inscription | POST `/comptes/inscription` | — | `{email, mot_de_passe(8–200), prenom?, role?}` | 201 `{token, compte}` | 400 `email_deja_utilise`, 422, 429 |
| Connexion | POST `/comptes/connexion` | — | `{email, mot_de_passe}` | 200 `{token, compte}` | 401 `identifiants_invalides`, 429 + `Retry-After` |
| Profil | GET `/comptes/moi` | C | — | 200 `compte` (`email_verifie`) | 401 `token_absent`/`token_invalide`/`jeton_revoque`/`compte_inconnu` |
| État vérif. e-mail | GET `/comptes/verification-email` | C | — | `{statut: EMAIL_UNVERIFIED\|VERIFICATION_TOKEN_CREATED\|EMAIL_VERIFIED, email_verifie}` | 401 |
| Renvoyer le courriel | POST `/comptes/verification-email` | C | — | 202 `{statut}` | 429 (5/h) |
| Lien du courriel | POST `/comptes/verification-email/confirmer` | — | `{jeton}` | 200 `{statut: EMAIL_VERIFIED}` | 400 `jeton_invalide_ou_expire`, 429 |
| Mot de passe | POST `/comptes/mot-de-passe` | C | `{ancien, nouveau}` | 200 `{token, compte}` (**remplacer** le jeton) | 403 `mot_de_passe_incorrect`, 429 |
| Changer d'adresse | POST `/comptes/email` | C | `{nouvel_email, mot_de_passe}` | 200 `{token, compte}` (adresse à revérifier) | 400 `email_indisponible`/`email_identique`, 403, 429 |
| Déconnexion | POST `/comptes/deconnexion` | C | — | 204 (tous les appareils) | 401 |
| Mes données | GET `/comptes/moi/export` | C | — | 200 | 401 |
| Supprimer mon compte | DELETE `/comptes/moi` | C | `{mot_de_passe, confirmation: true}` | 200 | 403, 409 `abonnement_en_cours`, 422 |
| Jeton élève | POST `/auth/eleve/jeton` | C | `{student_pseudo_id}` | 200 `{token, expires_in}` | 403 `acces_refuse`, 429 |
| Inviter un parent | POST `/liens/invitations` | E ou C lié | `{student_pseudo_id, relation?}` | 201 `{code, expires_in, expire_le, usage_unique}` | 403, 409 `trop_d_invitations_actives`, 429 |
| Saisir un code | POST `/liens/accepter` | C | `{code, confirmation: true}` | 201 `{statut: lien_cree, relation, student_pseudo_id}` | 400 `invitation_invalide`, 403 `email_non_verifie`, 409 `deja_lie`, 422, 429 |
| Nouvelle séance | POST `/session/nouvelle` | E | `{user_id}` | 201 `{session_id}` | 403 |
| Présence / état / reprise | POST `/session/heartbeat\|save-state\|reconnect` | E | `{session_id, user_id, state_data?}` | 200 | 401 `session_inactivite_5min`, 403, 404 `session_inconnue`, 413 |
| Exercice (catalogue) | POST `/exercices/soumettre` | E | `{exercice_id, student_pseudo_id, reponse}` | 200 `{est_correct, …}` | 401/403/422 |
| Parcours | GET `/parcours/prochaine-etape?student_id=` | E | — | 200 | 401/403 |
| Tuteur Mika | POST `/mika/session/start\|answer\|help\|comprehension`, GET `/mika/session/{id}?student_id=` | E | voir MIKA_API_CONTRACT.md | 201/200 | 404 `exercice_indisponible`/`tutorat_inconnu`, 409 `version_perimee`/`tutorat_termine`/… |
| Tableau de bord parent | GET `/parents/dashboard/{pseudo}` | C lié | — | 200 | 403 |
| Export RGPD enfant | GET `/rgpd/export/{pseudo}` | C lié / E | — | 200 | 403, 404 `aucune_donnee_trouvee_pour_cet_identifiant` |
| Effacement RGPD enfant | DELETE `/rgpd/effacer/{pseudo}` | C **parent** lié | — | 200 | 403, 404 `aucune_donnee_a_effacer` |

## 2. États d'interface (machine à états côté front)
```
DÉCONNECTÉ ──connexion/inscription──▶ CONNECTÉ(compte, email_verifie?)
CONNECTÉ ──email_verifie=false──▶ À_VÉRIFIER (bandeau « vérifiez votre adresse » + bouton renvoyer)
À_VÉRIFIER ──lien du courriel (page /verifier?jeton=…) ──▶ CONNECTÉ(email_verifie=true)
CONNECTÉ ──aucun enfant rattaché──▶ SANS_ENFANT (écran « saisir le code d'invitation »)
SANS_ENFANT ──code accepté──▶ ENFANT_CHOISI(pseudo) ──jeton élève──▶ SÉANCE(session_id)
SÉANCE ──401 jeton_expire──▶ ré-émission du jeton élève (1 fois) ──échec──▶ DÉCONNECTÉ
tout état ──401 jeton_revoque──▶ purge des jetons ──▶ DÉCONNECTÉ (ou choix d'enfant si seul le jeton élève est révoqué)
tout état ──429──▶ ATTENTE(Retry-After) puis retour à l'état précédent
```

## 3. Gestion des jetons (pseudo-code)
```js
const etat = { compte: null /* sessionStorage */, eleve: null /* mémoire */, expireEleve: 0 };

async function api(chemin, { methode = "GET", corps, jeton } = {}) {
  const r = await fetch(`/api/v1${chemin}`, { method: methode,
    headers: { "Content-Type": "application/json", ...(jeton && { Authorization: `Bearer ${jeton}` }) },
    body: corps && JSON.stringify(corps) });
  const data = r.status === 204 ? null : await r.json().catch(() => null);
  if (r.status === 429) throw { type: "attente", secondes: +r.headers.get("Retry-After") || 60 };
  if (r.status === 401) throw { type: "auth", code: data?.detail };
  if (r.status === 403) throw { type: "interdit", code: data?.detail };
  if (!r.ok) throw { type: "erreur", statut: r.status, code: data?.detail };
  return data;
}

async function jetonEleve(pseudo) {
  if (etat.eleve && Date.now() < etat.expireEleve - 5 * 60_000) return etat.eleve;
  const r = await api("/auth/eleve/jeton", { methode: "POST", jeton: etat.compte, corps: { student_pseudo_id: pseudo } });
  etat.eleve = r.token; etat.expireEleve = Date.now() + r.expires_in * 1000;
  return etat.eleve;
}

async function appelEleve(pseudo, chemin, options) {
  try { return await api(chemin, { ...options, jeton: await jetonEleve(pseudo) }); }
  catch (e) {
    if (e.type === "auth" && e.code === "jeton_expire") { etat.eleve = null; return api(chemin, { ...options, jeton: await jetonEleve(pseudo) }); }
    if (e.type === "auth") { etat.eleve = null; throw e; }  // jeton_revoque, etc.
    throw e;
  }
}
```
- Jeton de compte : mémoire + `sessionStorage`. Jeton élève : **mémoire uniquement**. Jamais de cookie, d'URL ni de log.
- Changement de mot de passe / d'adresse : **remplacer** immédiatement le jeton de compte par celui de la réponse.
- Déconnexion : appeler `/comptes/deconnexion` puis purger ; elle vaut pour **tous les appareils**.

## 4. Parcours clés
**Vérification d'adresse** : après inscription, bandeau permanent tant que `email_verifie=false`.
La page du lien (`/verifier?jeton=…`) poste le jeton une seule fois, affiche succès ou « lien
expiré ou déjà utilisé » (400 unique) avec un bouton « renvoyer » (si connecté).

**Invitation (enfant → parent)** : bouton « inviter un parent » → affiche le code
`XXXX-XXXX-…` UNE fois (copier / lire à voix haute), avec l'heure d'expiration ; jamais stocké.
**Saisie du code (parent)** : champ tolérant casse/espaces/tirets ; case obligatoire « je suis
le parent de cet enfant » (envoyer `confirmation: true` seulement si cochée) ; 403
`email_non_verifie` ⇒ rediriger vers la vérification ; 400 ⇒ « code invalide ou expiré » (message
unique) ; 409 `deja_lie` ⇒ « déjà rattaché ».

**Séance Mika** : `POST /session/nouvelle` à l'ouverture ; heartbeat toutes les 60 s ; `save-state`
à chaque modification de l'ardoise (debounce) ; au retour réseau `reconnect`. Tuteur : `requete_id`
= UUID v4 par action, conservé pour les réessais ; `version` = dernière reçue ; 409
`version_perimee` ⇒ GET du tutorat puis nouvelle action.

**Tableau de bord / RGPD** : afficher uniquement progression, matières, notions, activité ;
export = téléchargement du JSON ; effacement = double confirmation, puis retirer l'enfant de
l'interface (ses jetons sont révoqués côté serveur).

## 5. Tests E2E attendus (condition D12) et sélecteurs fonctionnels
Sélecteurs stables recommandés (`data-testid`) : `inscription-email`, `inscription-mdp`,
`inscription-valider`, `connexion-email`, `connexion-mdp`, `connexion-valider`, `bandeau-verif-email`,
`verif-renvoyer`, `invitation-generer`, `invitation-code-affiche`, `invitation-saisie`,
`invitation-confirmation-parent`, `invitation-valider`, `enfant-choix`, `exercice-enonce`,
`exercice-reponse`, `exercice-valider`, `mika-message`, `mika-aide`, `mika-reponse`,
`dashboard-progression`, `rgpd-export`, `rgpd-effacer`, `rgpd-effacer-confirmer`, `erreur-message`,
`attente-retry-after`, `deconnexion`.

Scénarios minimum (miroir de `tests_cloud/test_e2e_parent_enfant.py`) :
1. inscription → bandeau de vérification → lien → bandeau disparu ;
2. saisie de code sans vérification ⇒ redirection vérification ; après vérification ⇒ enfant rattaché ;
3. jeton élève → nouvelle séance → exercice (« 5*x » accepté) → tuteur (aide, réponse, compréhension) ;
4. l'enfant invite un second parent ; le second parent vérifie puis saisit le code ;
5. tableau de bord, export ; effacement ⇒ l'enfant disparaît, ses écrans renvoient au choix d'enfant ;
6. mauvais mot de passe ×6 ⇒ message d'attente avec compte à rebours (Retry-After) ;
7. changement de mot de passe ⇒ l'autre onglet/appareil est déconnecté au prochain appel.

Largeurs à couvrir : **390, 768, 1024, 1440 px** — navigation, zone de réponse et clavier mobile
(le champ reste visible au-dessus du clavier), formules (pas de débordement horizontal ; défilement
interne si nécessaire), boutons ≥ 44 × 44 px, quiz, messages de Mika, tableau de bord.

## 6. Accessibilité (exigences à tester)
- tout est utilisable au **clavier** (ordre de tabulation logique, focus visible, pas de piège) ;
- chaque champ a un `<label>` ; erreurs reliées par `aria-describedby` et annoncées (`role="alert"`) ;
- messages de Mika dans une région `aria-live="polite"` ;
- contrastes ≥ 4,5:1 (texte) ; zoom 200 % sans perte ; pas d'information par la couleur seule ;
- formules : MathML ou texte alternatif lisible (« 7 sur 10 »), jamais une image sans alternative ;
- compte à rebours d'attente (429) annoncé une fois, pas à chaque seconde.

## 7. Ce que le front ne doit JAMAIS faire
Stocker un code d'invitation ou un jeton de vérification ; afficher un JWT ; journaliser un
corps de requête contenant un mot de passe ; générer un `session_id` ; réessayer en boucle sur
401/403 ; envoyer `confirmation: true` sans action explicite de l'utilisateur.
