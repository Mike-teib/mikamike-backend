// Test d'intégration contre un VRAI serveur (MIKA_CONTRACT_BASE_URL), validation STRICTE des
// réponses. Sans cette variable : ignoré explicitement. JAMAIS contre la production.
//
// Le jeton de vérification d'adresse n'est JAMAIS renvoyé par HTTP (courriel uniquement) et le
// premier code d'invitation d'un élève est émis par l'opérateur (`python -m tools.liens`). Ces
// deux étapes exigent donc un HARNAIS côté serveur : `MIKA_CONTRACT_HELPER` = tableau JSON
// (argv) d'une commande qui imprime la valeur demandée :
//   <argv…> jeton-verification <email>   →  un jeton de vérification valide pour ce compte
//   <argv…> invitation <pseudo>          →  un code d'invitation opérateur
// Fourni par tests_cloud/test_frontend_contract_pkg.py (qui lance aussi le serveur uvicorn).
// Sans harnais, seules les étapes publiques sont jouées ; les autres sont ignorées explicitement.

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { describe, it } from "node:test";

import { transition, transitionSeance, transitionVerification } from "../auth-state.ts";
import type { EtatAuth, EtatSeance, EtatVerification } from "../auth-state.ts";
import { ApiError, MemoryTokenStore, MikaClient, nouveauRequeteId } from "../client.ts";
import { expireLeEnMs, transitionLien } from "../parent-link-state.ts";
import type { EtatLien } from "../parent-link-state.ts";
import type { Compte } from "../types.ts";

const BASE = process.env["MIKA_CONTRACT_BASE_URL"];
const HELPER = process.env["MIKA_CONTRACT_HELPER"];
const argvHarnais: readonly string[] | null = HELPER ? (JSON.parse(HELPER) as string[]) : null;
const SANS_SERVEUR = BASE ? false : "MIKA_CONTRACT_BASE_URL non définie : intégration ignorée";
const SANS_HARNAIS = !BASE ? SANS_SERVEUR
  : argvHarnais ? false : "MIKA_CONTRACT_HELPER non défini : étape pilotée par le harnais serveur ignorée";

function harnais(...args: string[]): string {
  if (!argvHarnais || argvHarnais.length === 0) throw new Error("harnais absent");
  const [cmd, ...pre] = argvHarnais;
  return execFileSync(cmd!, [...pre, ...args], { encoding: "utf8", timeout: 60_000 }).trim();
}

const suffixe = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
const PSEUDO = `eleve-fc-${suffixe}`;
const MDP = "motdepasse-fc-0001";
const email = (qui: string) => `fc-${qui}-${suffixe}@example.com`;

const client = (store = new MemoryTokenStore()) =>
  new MikaClient({ baseUrl: BASE ?? "http://invalide", tokenStore: store, validation: "stricte" });

const estApi = (status: number, code: string | null) => (e: unknown): boolean => {
  if (!(e instanceof ApiError)) throw e;
  assert.equal(e.status, status, `statut ${e.status} ${String(e.code)}`);
  assert.equal(e.code, code);
  return true;
};

it("serveur réel configuré (MIKA_CONTRACT_BASE_URL)", { skip: SANS_SERVEUR }, () => {
  assert.match(BASE ?? "", /^https?:\/\//);
  assert.doesNotMatch(BASE ?? "", /prod/i, "jamais contre la production");
});

describe("intégration contre un serveur réel", { skip: SANS_SERVEUR }, () => {
  // Acteurs : parent A (rattaché par code opérateur), l'enfant (jeton élève émis par A),
  // parent B (rattaché par invitation de l'enfant), parent C (jamais lié).
  const storeA = new MemoryTokenStore();
  const A = client(storeA);
  const storeB = new MemoryTokenStore();
  const B = client(storeB);
  const C = client();
  let auth: EtatAuth = { etat: "ANONYME", raison: null };
  let verif: EtatVerification = { etat: "NON_DEMANDEE" };
  let lienA: EtatLien = { etat: "AUCUNE" };
  let lienB: EtatLien = { etat: "AUCUNE" };
  let seance: EtatSeance = { etat: "AUCUNE" };
  let sessionId = "";
  let codeB = "";
  let compteB: Compte | null = null;

  it("inscription (201), doublon (400), invalide (422), connexion refusée (401)", async () => {
    const r = await A.inscription({ email: email("a"), mot_de_passe: MDP, prenom: "Prénom", role: "parent" });
    assert.equal(r.compte.email_verifie, false);
    auth = transition(auth, { type: "INSCRIPTION_REUSSIE", compte: r.compte });
    await assert.rejects(client().inscription({ email: email("a"), mot_de_passe: MDP }), estApi(400, "email_deja_utilise"));
    await assert.rejects(client().inscription({ email: "pas-un-email", mot_de_passe: "court" }), estApi(422, null));
    await assert.rejects(client().connexion({ email: email("a"), mot_de_passe: "mauvais-mdp-00" }),
      estApi(401, "identifiants_invalides"));
    await assert.rejects(client().moi(), estApi(401, "token_absent"));
  });

  it("vérification : état, renvoi (202), jeton invalide (400)", async () => {
    const e = await A.etatVerificationEmail();
    verif = transitionVerification(verif, { type: "STATUT_LU", statut: e.statut });
    assert.equal(verif.etat, "ENVOYEE");
    const d = await A.demanderVerification();
    verif = transitionVerification(verif, { type: "DEMANDE_ACCEPTEE", statut: d.statut });
    await assert.rejects(A.verifierEmail({ jeton: "jeton-inconnu" }), estApi(400, "jeton_invalide_ou_expire"));
    verif = transitionVerification(verif, { type: "CONFIRMATION_REFUSEE" });
    assert.equal(verif.etat, "JETON_INVALIDE");
  });

  it("vérification : jeton reçu « par courriel » (harnais) ⇒ EMAIL_VERIFIED ⇒ CONNECTE", { skip: SANS_HARNAIS }, async () => {
    const jeton = harnais("jeton-verification", email("a"));
    assert.equal((await A.verifierEmail({ jeton })).statut, "EMAIL_VERIFIED");
    verif = transitionVerification(verif, { type: "CONFIRMATION_REUSSIE" });
    auth = transition(auth, { type: "EMAIL_CONFIRME" });
    const moi = await A.moi();
    assert.equal(moi.email_verifie, true);
    auth = transition(auth, { type: "PROFIL_CHARGE", compte: moi });
    assert.equal(auth.etat, "CONNECTE");
    await assert.rejects(A.verifierEmail({ jeton }), estApi(400, "jeton_invalide_ou_expire")); // usage unique
  });

  it("rattachement par code opérateur (harnais) : 403 sans lien, 201, 400 déjà utilisé, jeton élève", { skip: SANS_HARNAIS }, async () => {
    await assert.rejects(A.jetonEleve({ student_pseudo_id: PSEUDO }), estApi(403, "acces_refuse"));
    const code = harnais("invitation", PSEUDO);
    lienA = transitionLien(lienA, { type: "CODE_EMIS", expireA: null });
    await assert.rejects(A.accepterInvitation({ code: "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", confirmation: true }),
      estApi(400, "invitation_invalide"));
    const r = await A.accepterInvitation({ code: code.toLowerCase(), confirmation: true }); // tolérant à la casse
    assert.deepEqual(r, { statut: "lien_cree", relation: "parent", student_pseudo_id: PSEUDO });
    lienA = transitionLien(lienA, { type: "ACCEPTATION_REUSSIE", pseudo: r.student_pseudo_id, relation: r.relation });
    await assert.rejects(A.accepterInvitation({ code, confirmation: true }), estApi(400, "invitation_invalide"));
    const j = await A.jetonEleve({ student_pseudo_id: PSEUDO });
    assert.equal(j.typ, "mika-eleve");
    seance = transitionSeance(seance, { type: "JETON_OBTENU", pseudo: PSEUDO, expireA: Date.now() + j.expires_in * 1000 });
  });

  it("séance Mika : nouvelle (201), inconnue (404), heartbeat, save-state, reconnect", { skip: SANS_HARNAIS }, async () => {
    const n = await A.nouvelleSession({ user_id: PSEUDO });
    sessionId = n.session_id;
    assert.match(sessionId, /^s[0-9a-f]{48}$/);
    seance = transitionSeance(seance, { type: "SEANCE_CREEE", sessionId });
    await assert.rejects(A.heartbeat({ session_id: "identifiant-client", user_id: PSEUDO }), estApi(404, "session_inconnue"));
    assert.equal((await A.heartbeat({ session_id: sessionId, user_id: PSEUDO })).statut, "heartbeat_ok");
    await A.sauverEtat({ session_id: sessionId, user_id: PSEUDO, state_data: { ardoise: "x" } });
    const r = await A.reconnecter({ session_id: sessionId, user_id: PSEUDO });
    assert.deepEqual(r.session_state, { ardoise: "x" });
    seance = transitionSeance(seance, { type: "ACTIVITE" });
    assert.equal(seance.etat, "OUVERTE");
  });

  it("exercice (progression), prochaine étape, tuteur (404 typés : aucun contenu prouvé servi)", { skip: SANS_HARNAIS }, async () => {
    const s = await A.soumettreExercice({ exercice_id: "exo-maths-calcul-litteral-1", student_pseudo_id: PSEUDO, reponse: "5*x" });
    assert.equal(s.est_correct, true);
    assert.equal(s.progression?.moteur, "historique");
    await assert.rejects(client().soumettreExercice({ exercice_id: "exo-maths-calcul-litteral-1", student_pseudo_id: PSEUDO, reponse: "5x" }),
      estApi(401, "jeton_requis"));
    const p = await A.prochaineEtape(PSEUDO);
    assert.ok(p.exercice_id.length > 0);
    await assert.rejects(A.tutoratStart({ student_pseudo_id: PSEUDO, requete_id: nouveauRequeteId(), exercice_id: "exo:inexistant" }),
      estApi(404, "exercice_indisponible"));
    const tid = "0".repeat(32);
    await assert.rejects(A.tutoratHelp({ student_pseudo_id: PSEUDO, requete_id: nouveauRequeteId(), tutorat_id: tid, version: 1 }),
      estApi(404, "tutorat_inconnu"));
    await assert.rejects(A.tutoratEtat(tid, PSEUDO), estApi(404, "tutorat_inconnu"));
  });

  it("l'enfant invite un 2e parent : 403 email_non_verifie puis 201 après vérification", { skip: SANS_HARNAIS }, async () => {
    const inv = await A.emettreInvitation({ student_pseudo_id: PSEUDO }); // jeton ÉLÈVE (porteur par défaut)
    assert.equal(inv.usage_unique, true);
    codeB = inv.code;
    lienB = transitionLien(lienB, { type: "CODE_EMIS", expireA: expireLeEnMs(inv.expire_le) });
    compteB = (await B.inscription({ email: email("b"), mot_de_passe: MDP })).compte;
    await assert.rejects(B.accepterInvitation({ code: codeB, confirmation: true }), (e: unknown) => {
      estApi(403, "email_non_verifie")(e);
      lienB = transitionLien(lienB, { type: "ACCEPTATION_REFUSEE", status: 403, code: "email_non_verifie" });
      return true;
    });
    assert.equal(lienB.etat, "REFUSEE_EMAIL_NON_VERIFIE");
    await B.verifierEmail({ jeton: harnais("jeton-verification", email("b")) });
    const r = await B.accepterInvitation({ code: codeB, confirmation: true });
    lienB = transitionLien(lienB, { type: "ACCEPTATION_REUSSIE", pseudo: r.student_pseudo_id, relation: r.relation });
    assert.equal(lienB.etat, "ACCEPTEE");
  });

  it("tableau de bord (schéma fermé) ; non lié ⇒ 403 ; exports RGPD", { skip: SANS_HARNAIS }, async () => {
    const d = await A.dashboardParent(PSEUDO);
    assert.equal(d.pseudo_id, PSEUDO);
    assert.equal(d.statistiques_pedagogiques.exercices_tentes, 1);
    lienA = transitionLien(lienA, { type: "DASHBOARD_OK" });
    await C.inscription({ email: email("c"), mot_de_passe: MDP });
    await assert.rejects(C.dashboardParent(PSEUDO), estApi(403, "acces_refuse"));
    const ex = await A.exportRgpdEleve(PSEUDO);
    assert.equal(ex.total_tentatives, 1);
    assert.equal(ex.liens_comptes.length, 2);
    const exEleve = await A.exportRgpdEleve(PSEUDO, { porteur: "eleve" });
    assert.equal(exEleve.student_pseudo_id, PSEUDO);
    const exc = await A.exportCompte();
    assert.equal(exc.verification_email.statut, "EMAIL_VERIFIED");
  });

  it("suppression du compte B ⇒ SUPPRIME ; ancien jeton ⇒ 401 compte_inconnu", { skip: SANS_HARNAIS }, async () => {
    const ancien = storeB.lireJetonCompte();
    await assert.rejects(B.supprimerCompte({ mot_de_passe: "mauvais-mdp-00", confirmation: true }),
      estApi(403, "mot_de_passe_incorrect"));
    const r = await B.supprimerCompte({ mot_de_passe: MDP, confirmation: true });
    assert.deepEqual(r, { statut: "compte_supprime", liens_supprimes: 1 });
    assert.ok(compteB !== null);
    let authB: EtatAuth = { etat: "CONNECTE", compte: { ...compteB, email_verifie: true } };
    authB = transition(authB, { type: "COMPTE_SUPPRIME" });
    assert.equal(authB.etat, "SUPPRIME");
    assert.equal(storeB.lireJetonCompte(), null);
    storeB.ecrireJetonCompte(ancien);
    await assert.rejects(B.moi(), estApi(401, "compte_inconnu"));
  });

  it("effacement RGPD : élève refusé (403), parent (200) ⇒ jeton élève révoqué, dashboard 403", { skip: SANS_HARNAIS }, async () => {
    await assert.rejects(A.effacerRgpdEleve(PSEUDO, { porteur: "eleve" }), estApi(403, "acces_refuse"));
    const jetonEleve = storeA.lireJetonEleve(PSEUDO);
    const r = await A.effacerRgpdEleve(PSEUDO);
    assert.equal(r.statut, "effacement_effectue");
    assert.equal(storeA.lireJetonEleve(PSEUDO), null);
    // Autre appareil de l'enfant, qui détient encore l'ancien jeton élève :
    const autre = new MemoryTokenStore();
    if (jetonEleve) autre.ecrireJetonEleve(PSEUDO, jetonEleve);
    await assert.rejects(client(autre).heartbeat({ session_id: sessionId, user_id: PSEUDO }), (e: unknown) => {
      estApi(401, "jeton_revoque")(e);
      seance = transitionSeance(seance, { type: "ERREUR", status: 401, code: "jeton_revoque" });
      return true;
    });
    assert.equal(seance.etat, "REVOQUEE");
    await assert.rejects(A.dashboardParent(PSEUDO), (e: unknown) => {
      estApi(403, "acces_refuse")(e);
      lienA = transitionLien(lienA, { type: "DASHBOARD_REFUSE", status: 403 });
      return true;
    });
    assert.equal(lienA.etat, "LIEN_REVOQUE");
  });

  it("mot de passe changé ⇒ ancien jeton 401 jeton_revoque ; changement d'adresse ; déconnexion 204", async () => {
    // Sans harnais, A est encore « INSCRIT_NON_VERIFIE » : le parcours reste valable.
    const autreAppareil = new MemoryTokenStore();
    autreAppareil.ecrireJetonCompte(storeA.lireJetonCompte());
    const r = await A.changerMotDePasse({ ancien: MDP, nouveau: "nouveau-mdp-fc-0001" });
    auth = transition(auth, { type: "MOT_DE_PASSE_CHANGE", compte: r.compte });
    let authAutre: EtatAuth = auth;
    await assert.rejects(client(autreAppareil).moi(), (e: unknown) => {
      estApi(401, "jeton_revoque")(e);
      authAutre = transition(authAutre, { type: "ERREUR_AUTH", code: "jeton_revoque" });
      return true;
    });
    assert.deepEqual(authAutre, { etat: "ANONYME", raison: "revocation" });
    assert.equal(autreAppareil.lireJetonCompte(), null, "le client a purgé le jeton révoqué");
    const e = await A.changerEmail({ nouvel_email: email("a2"), mot_de_passe: "nouveau-mdp-fc-0001" });
    assert.equal(e.compte.email_verifie, false);
    auth = transition(auth, { type: "EMAIL_CHANGE", compte: e.compte });
    assert.equal(auth.etat, "INSCRIT_NON_VERIFIE");
    verif = transitionVerification(verif, { type: "ADRESSE_CHANGEE" });
    const avant = storeA.lireJetonCompte();
    await A.deconnexion();
    auth = transition(auth, { type: "DECONNEXION" });
    assert.deepEqual(auth, { etat: "ANONYME", raison: "deconnexion" });
    const apres = new MemoryTokenStore();
    apres.ecrireJetonCompte(avant);
    await assert.rejects(client(apres).moi(), estApi(401, "jeton_revoque"));
  });

  it("limitation : 6e connexion ratée ⇒ 429 trop_de_tentatives + Retry-After", async () => {
    const x = client();
    for (let i = 0; i < 5; i += 1) {
      await assert.rejects(x.connexion({ email: email("c"), mot_de_passe: "mauvais-mdp-00" }), estApi(401, "identifiants_invalides"));
    }
    await assert.rejects(x.connexion({ email: email("c"), mot_de_passe: "mauvais-mdp-00" }), (e: unknown) => {
      estApi(429, "trop_de_tentatives")(e);
      assert.ok(e instanceof ApiError && e.retryAfter !== null && e.retryAfter > 0);
      return true;
    });
  });
});
