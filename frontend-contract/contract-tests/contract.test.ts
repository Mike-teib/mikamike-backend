// Tests contractuels : CHAQUE appel de contrat_front/contrat.json a une méthode client, envoie
// exactement la requête enregistrée (méthode, chemin, jeton, corps) et sa réponse est validée
// par le validateur runtime (mode strict : aucune clé inconnue, aucune clé manquante).

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError, COUVERTURE_CONTRAT, MemoryTokenStore, MikaClient, ROUTES } from "../client.ts";
import type { OperationId } from "../client.ts";
import { CODES_ERREUR, NOMS_APPELS_CONTRAT } from "../types.ts";
import type { AcceptationCorps, NomAppelContrat } from "../types.ts";
import { ErreurContrat, valider, vDashboardParent, vReponseSoumission } from "../validators.ts";
import { chargerContrat, echantillon, fetchFactice } from "./contrat.ts";
import type { AppelContrat } from "./contrat.ts";

const contrat = chargerContrat();
const BASE = "https://api.test";
const PSEUDO = "eleve-contrat-01";
const CODE = "ABCD-EFGH-IJKL-MNOP-QRST-UVWX";
const SID = "s" + "0123456789abcdef".repeat(3);
const TID = "0123456789abcdef0123456789abcdef";
const JETON_MAIL = "jeton-recu-par-courriel";
const JETON_COMPTE = "jeton-compte-factice-NE-DOIT-JAMAIS-FUIR";
const JETON_ELEVE = "jeton-eleve-factice-NE-DOIT-JAMAIS-FUIR";
const MDP = "motdepasse-contrat-01";

const PLACEHOLDERS: Record<string, string> = {
  "<student_pseudo_id>": PSEUDO, "<code_invitation>": CODE, "<session_id>": SID, "<tutorat_id>": TID,
  "<jeton_recu_par_courriel>": JETON_MAIL,
};
const substituer = (v: unknown): unknown => {
  if (typeof v === "string") return PLACEHOLDERS[v] ?? v;
  if (Array.isArray(v)) return v.map(substituer);
  if (typeof v === "object" && v !== null) {
    return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, substituer(x)]));
  }
  return v;
};

// Appels écrits comme le ferait le front (le typage TS des corps est ainsi vérifié par tsc).
const INVOCATIONS: { readonly [N in NomAppelContrat]: (c: MikaClient) => Promise<unknown> } = {
  inscription: (c) => c.inscription({ email: "parent1@example.com", mot_de_passe: MDP, prenom: "Prénom", role: "parent" }),
  inscription_email_deja_utilise: (c) => c.inscription({ email: "parent1@example.com", mot_de_passe: MDP }),
  inscription_invalide: (c) => c.inscription({ email: "pas-un-email", mot_de_passe: "court" }),
  inscription_parent2: (c) => c.inscription({ email: "parent2@example.com", mot_de_passe: MDP }),
  connexion: (c) => c.connexion({ email: "parent1@example.com", mot_de_passe: MDP }),
  connexion_refusee: (c) => c.connexion({ email: "parent1@example.com", mot_de_passe: "mauvais-mdp-00" }),
  trop_de_tentatives: (c) => c.connexion({ email: "parent2@example.com", mot_de_passe: "mauvais-mdp-00" }),
  moi: (c) => c.moi(),
  moi_sans_jeton: (c) => c.moi(),
  ancien_jeton_revoque: (c) => c.moi(),
  etat_verification_email: (c) => c.etatVerificationEmail(),
  demander_verification_email: (c) => c.demanderVerification(),
  confirmer_email_invalide: (c) => c.verifierEmail({ jeton: "jeton-inconnu" }),
  confirmer_email: (c) => c.verifierEmail({ jeton: JETON_MAIL }),
  jeton_eleve_sans_lien: (c) => c.jetonEleve({ student_pseudo_id: PSEUDO }),
  jeton_eleve: (c) => c.jetonEleve({ student_pseudo_id: PSEUDO }),
  // Le type exige `confirmation: true` : le cas 422 n'est atteignable qu'en contournant le typage.
  accepter_invitation_sans_confirmation: (c) =>
    c.accepterInvitation({ code: CODE, confirmation: false } as unknown as AcceptationCorps),
  accepter_invitation_code_invalide: (c) =>
    c.accepterInvitation({ code: "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", confirmation: true }),
  accepter_invitation: (c) => c.accepterInvitation({ code: CODE, confirmation: true }),
  accepter_invitation_deja_utilisee: (c) => c.accepterInvitation({ code: CODE, confirmation: true }),
  accepter_invitation_email_non_verifie: (c) => c.accepterInvitation({ code: CODE, confirmation: true }),
  emettre_invitation: (c) => c.emettreInvitation({ student_pseudo_id: PSEUDO }),
  nouvelle_seance: (c) => c.nouvelleSession({ user_id: PSEUDO }),
  seance_inconnue: (c) => c.heartbeat({ session_id: "identifiant-client", user_id: PSEUDO }),
  heartbeat: (c) => c.heartbeat({ session_id: SID, user_id: PSEUDO }),
  jeton_eleve_revoque: (c) => c.heartbeat({ session_id: SID, user_id: PSEUDO }),
  sauver_etat: (c) => c.sauverEtat({ session_id: SID, user_id: PSEUDO, state_data: { ardoise: "x" } }),
  reconnexion: (c) => c.reconnecter({ session_id: SID, user_id: PSEUDO }),
  soumettre_exercice: (c) =>
    c.soumettreExercice({ exercice_id: "exo-maths-calcul-litteral-1", student_pseudo_id: PSEUDO, reponse: "5*x" }),
  soumettre_sans_jeton: (c) =>
    c.soumettreExercice({ exercice_id: "exo-maths-calcul-litteral-1", student_pseudo_id: PSEUDO, reponse: "5x" }),
  prochaine_etape: (c) => c.prochaineEtape(PSEUDO),
  tuteur_start: (c) => c.tutoratStart({ student_pseudo_id: PSEUDO, requete_id: "req-1", exercice_id: "exo:fictif:contrat" }),
  tuteur_start_rejeu: (c) =>
    c.tutoratStart({ student_pseudo_id: PSEUDO, requete_id: "req-1", exercice_id: "exo:fictif:contrat" }),
  tuteur_help: (c) => c.tutoratHelp({ student_pseudo_id: PSEUDO, tutorat_id: TID, requete_id: "req-2", version: 1 }),
  tuteur_version_perimee: (c) =>
    c.tutoratAnswer({ student_pseudo_id: PSEUDO, tutorat_id: TID, requete_id: "req-3", version: 1, reponse: "0,7" }),
  tuteur_answer: (c) =>
    c.tutoratAnswer({ student_pseudo_id: PSEUDO, tutorat_id: TID, requete_id: "req-4", version: 2, reponse: "0,7" }),
  tuteur_comprehension: (c) =>
    c.tutoratComprehension({ student_pseudo_id: PSEUDO, tutorat_id: TID, requete_id: "req-5", version: 3, reponse: "0,9" }),
  tuteur_etat: (c) => c.tutoratEtat(TID, PSEUDO),
  dashboard_parent: (c) => c.dashboardParent(PSEUDO),
  dashboard_non_lie: (c) => c.dashboardParent(PSEUDO),
  export_rgpd_eleve: (c) => c.exportRgpdEleve(PSEUDO),
  export_compte: (c) => c.exportCompte(),
  effacement_par_eleve_refuse: (c) => c.effacerRgpdEleve(PSEUDO, { porteur: "eleve" }),
  effacement_rgpd: (c) => c.effacerRgpdEleve(PSEUDO),
  changer_mot_de_passe: (c) => c.changerMotDePasse({ ancien: MDP, nouveau: "nouveau-mdp-contrat" }),
  deconnexion: (c) => c.deconnexion(),
};

/** Chemins dont le client ajoute la requête `?student_id=` (supprimée du gabarit enregistré). */
const QUERY_STUDENT_ID = new Set<OperationId>(["prochaineEtape", "tutoratEtat"]);

function clientPour(appel: AppelContrat, reponses: Parameters<typeof fetchFactice>[0]) {
  const f = fetchFactice(reponses);
  const store = new MemoryTokenStore();
  if (appel.auth === "compte") store.ecrireJetonCompte(JETON_COMPTE);
  if (appel.auth === "eleve") store.ecrireJetonEleve(PSEUDO, { token: JETON_ELEVE, expireA: Number.MAX_SAFE_INTEGER });
  const client = new MikaClient({
    baseUrl: BASE, fetchImpl: f.impl, tokenStore: store, validation: "stricte", emissionAutoJetonEleve: false,
  });
  return { client, store, requetes: f.requetes };
}

describe("couverture du contrat", () => {
  it("contrat.json ↔ NOMS_APPELS_CONTRAT ↔ COUVERTURE_CONTRAT : mêmes 46 noms", () => {
    const noms = contrat.appels.map((a) => a.nom).sort();
    assert.equal(new Set(noms).size, noms.length, "noms dupliqués dans contrat.json");
    assert.deepEqual([...NOMS_APPELS_CONTRAT].sort(), noms);
    assert.deepEqual(Object.keys(COUVERTURE_CONTRAT).sort(), noms);
    assert.equal(contrat.base, "/api/v1");
  });

  it("chaque code d'erreur du contrat appartient à CODES_ERREUR", () => {
    const codes = contrat.appels.filter((a) => a.statut_http >= 400).map((a) => {
      const d = (a.reponse as { detail: unknown }).detail;
      return typeof d === "string" ? d : Array.isArray(d) ? null : (d as { code: string }).code;
    }).filter((c): c is string => c !== null);
    assert.ok(codes.length >= 10);
    for (const c of codes) assert.ok((CODES_ERREUR as readonly string[]).includes(c), c);
  });

  it("chaque opération couverte est une méthode du client", () => {
    for (const op of new Set(Object.values(COUVERTURE_CONTRAT))) {
      assert.equal(typeof (MikaClient.prototype as unknown as Record<string, unknown>)[op], "function", op);
    }
    for (const op of Object.keys(ROUTES)) {
      assert.equal(typeof (MikaClient.prototype as unknown as Record<string, unknown>)[op], "function", op);
    }
  });
});

describe("chaque appel du contrat (client + validateur runtime)", () => {
  for (const appel of contrat.appels) {
    it(`${appel.nom} : ${appel.methode} ${appel.chemin} → ${appel.statut_http}`, async () => {
      const op = COUVERTURE_CONTRAT[appel.nom];
      const route = ROUTES[op];
      // 1. La route du client est celle du contrat.
      assert.equal(route.methode, appel.methode);
      assert.equal(contrat.base + route.chemin, appel.chemin);
      if (appel.statut_http < 400) assert.ok((route.succes as readonly number[]).includes(appel.statut_http));
      if (appel.auth === null && route.auth !== "aucune") assert.equal(appel.statut_http, 401, "appel sans jeton ⇒ 401");
      if (appel.auth !== null && route.auth !== "compte_ou_eleve" && route.auth !== appel.auth) {
        assert.ok([401, 403].includes(appel.statut_http), "mauvais porteur ⇒ 401/403");
      }

      // 2. Réponse échantillon construite depuis la forme enregistrée.
      const corpsReponse = echantillon(appel.reponse);
      const { client, requetes } = clientPour(appel, [{
        status: appel.statut_http, corps: appel.statut_http === 204 ? undefined : corpsReponse,
        ...(appel.retry_after ? { headers: { "Retry-After": "60" } } : {}),
      }]);
      const invocation = INVOCATIONS[appel.nom];
      let resultat: unknown;
      let erreur: unknown = null;
      try {
        resultat = await invocation(client);
      } catch (e) {
        erreur = e;
      }

      // 3. Requête émise = requête enregistrée.
      assert.equal(requetes.length, 1);
      const req = requetes[0]!;
      const url = new URL(req.url);
      const attendu = appel.chemin.replace("{student_pseudo_id}", PSEUDO).replace("{tutorat_id}", TID);
      assert.equal(url.pathname, attendu);
      if (QUERY_STUDENT_ID.has(op)) assert.equal(url.searchParams.get("student_id"), PSEUDO);
      else assert.equal(url.search, "");
      assert.equal(req.methode, appel.methode);
      const auth = req.headers["Authorization"];
      if (appel.auth === "compte") assert.equal(auth, `Bearer ${JETON_COMPTE}`);
      else if (appel.auth === "eleve") assert.equal(auth, `Bearer ${JETON_ELEVE}`);
      else assert.equal(auth, undefined);
      assert.deepEqual(req.corps, appel.corps === null ? undefined : substituer(appel.corps));

      // 4. Résultat : réponse validée (succès) ou ApiError typée (erreur).
      if (appel.statut_http < 400) {
        assert.equal(erreur, null, `erreur inattendue : ${String(erreur)}`);
        if (appel.statut_http === 204) assert.equal(resultat, undefined);
        else assert.deepEqual(resultat, corpsReponse);
      } else {
        assert.ok(erreur instanceof ApiError, `ApiError attendue, reçu ${String(erreur)}`);
        assert.equal(erreur.status, appel.statut_http);
        const detail = (corpsReponse as { detail: unknown }).detail;
        if (typeof detail === "string") assert.equal(erreur.code, detail);
        else if (Array.isArray(detail)) {
          assert.equal(erreur.code, null);
          assert.ok(erreur.erreursValidation.length > 0);
        } else {
          assert.equal(erreur.code, (detail as { code: string }).code);
          assert.equal(erreur.versionCourante, 1);
        }
        if (appel.retry_after) assert.equal(erreur.retryAfter, 60);
        for (const secret of [JETON_COMPTE, JETON_ELEVE, MDP, CODE]) {
          assert.ok(!erreur.message.includes(secret) && !String(erreur.stack).includes(secret), "fuite dans l'erreur");
        }
      }
    });
  }
});

describe("comportements du client", () => {
  const compte = { id: 1, email: "a@b.c", prenom: null, role: "parent", statut_abonnement: "aucun", email_verifie: false };
  const tutorat = echantillon(contrat.appels.find((a) => a.nom === "tuteur_start")!.reponse);

  it("jeton élève : 401 jeton_expire ⇒ UNE ré-émission puis nouvel essai", async () => {
    const f = fetchFactice([
      { status: 401, corps: { detail: "jeton_expire" } },
      { status: 200, corps: { token: "neuf", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 } },
      { status: 201, corps: tutorat },
    ]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    store.ecrireJetonEleve(PSEUDO, { token: "vieux", expireA: Number.MAX_SAFE_INTEGER });
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store, horloge: () => 0 });
    await c.tutoratStart({ student_pseudo_id: PSEUDO, requete_id: "r", exercice_id: "e" });
    assert.deepEqual(f.requetes.map((r) => [new URL(r.url).pathname, r.headers["Authorization"]]), [
      ["/api/v1/mika/session/start", "Bearer vieux"],
      ["/api/v1/auth/eleve/jeton", "Bearer compte"],
      ["/api/v1/mika/session/start", "Bearer neuf"],
    ]);
    assert.deepEqual(store.lireJetonEleve(PSEUDO), { token: "neuf", expireA: 7_200_000 });
  });

  it("jeton élève : deuxième jeton_expire ⇒ erreur (pas de boucle)", async () => {
    const f = fetchFactice([
      { status: 401, corps: { detail: "jeton_expire" } },
      { status: 200, corps: { token: "neuf", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 } },
      { status: 401, corps: { detail: "jeton_expire" } },
    ]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    store.ecrireJetonEleve(PSEUDO, { token: "vieux", expireA: Number.MAX_SAFE_INTEGER });
    const vus: string[] = [];
    const c = new MikaClient({
      baseUrl: BASE, fetchImpl: f.impl, tokenStore: store, surErreurAuth: (e, p) => vus.push(`${p}:${e.code}`),
    });
    await assert.rejects(c.prochaineEtape(PSEUDO), (e: unknown) => e instanceof ApiError && e.code === "jeton_expire");
    assert.equal(f.requetes.length, 3);
    assert.equal(store.lireJetonEleve(PSEUDO), null);
    assert.deepEqual(vus, ["eleve:jeton_expire"]);
    assert.equal(store.lireJetonCompte(), "compte", "le jeton de compte n'est pas touché");
  });

  it("jeton élève manquant ou proche de l'expiration ⇒ émission automatique (marge 5 min)", async () => {
    const f = fetchFactice([
      { status: 200, corps: { token: "neuf", token_type: "Bearer", typ: "mika-eleve", expires_in: 7200 } },
      { status: 200, corps: { exercice_id: "e", niveau: "4e", competence: "c", consigne: "x" } },
    ]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    store.ecrireJetonEleve(PSEUDO, { token: "presque-expire", expireA: 1_000_000 + 4 * 60_000 });
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store, horloge: () => 1_000_000 });
    await c.prochaineEtape(PSEUDO);
    assert.equal(f.requetes[1]!.headers["Authorization"], "Bearer neuf");
  });

  it("401 jeton_revoque sur une route compte ⇒ purge de tous les jetons + notification", async () => {
    const f = fetchFactice([{ status: 401, corps: { detail: "jeton_revoque" } }]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    store.ecrireJetonEleve(PSEUDO, { token: "e", expireA: Number.MAX_SAFE_INTEGER });
    const vus: string[] = [];
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store, surErreurAuth: (e, p) => vus.push(`${p}:${e.code}`) });
    await assert.rejects(c.moi(), ApiError);
    assert.equal(store.lireJetonCompte(), null);
    assert.equal(store.lireJetonEleve(PSEUDO), null);
    assert.deepEqual(vus, ["compte:jeton_revoque"]);
  });

  it("401 session_inactivite_5min ne purge aucun jeton", async () => {
    const f = fetchFactice([{ status: 401, corps: { detail: "session_inactivite_5min" } }]);
    const store = new MemoryTokenStore();
    store.ecrireJetonEleve(PSEUDO, { token: "e", expireA: Number.MAX_SAFE_INTEGER });
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store });
    await assert.rejects(c.heartbeat({ session_id: SID, user_id: PSEUDO }), (e: unknown) =>
      e instanceof ApiError && e.code === "session_inactivite_5min");
    assert.notEqual(store.lireJetonEleve(PSEUDO), null);
  });

  it("503 courriel_indisponible ⇒ ApiError typée", async () => {
    const f = fetchFactice([{ status: 503, corps: { detail: "courriel_indisponible" } }]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store });
    await assert.rejects(c.demanderVerification(), (e: unknown) =>
      e instanceof ApiError && e.status === 503 && e.code === "courriel_indisponible");
    assert.equal(store.lireJetonCompte(), "compte");
  });

  it("inscription / changement de mot de passe / d'adresse remplacent le jeton ; déconnexion et suppression purgent", async () => {
    const jeton = (t: string) => ({ status: 200, corps: { token: t, compte } });
    const f = fetchFactice([
      { status: 201, corps: { token: "t1", compte } }, jeton("t2"), jeton("t3"), { status: 204 },
      { status: 200, corps: { token: "t4", compte } },
      { status: 200, corps: { statut: "compte_supprime", liens_supprimes: 1 } },
    ]);
    const store = new MemoryTokenStore();
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store });
    await c.inscription({ email: "a@b.c", mot_de_passe: MDP });
    assert.equal(store.lireJetonCompte(), "t1");
    store.ecrireJetonEleve(PSEUDO, { token: "e", expireA: Number.MAX_SAFE_INTEGER });
    await c.changerMotDePasse({ ancien: MDP, nouveau: "autre-mot-de-passe" });
    assert.equal(store.lireJetonCompte(), "t2");
    assert.equal(store.lireJetonEleve(PSEUDO), null, "jetons élève révoqués côté serveur (cv)");
    await c.changerEmail({ nouvel_email: "x@y.z", mot_de_passe: "autre-mot-de-passe" });
    assert.equal(store.lireJetonCompte(), "t3");
    await c.deconnexion();
    assert.equal(store.lireJetonCompte(), null);
    await c.connexion({ email: "x@y.z", mot_de_passe: "autre-mot-de-passe" });
    await c.supprimerCompte({ mot_de_passe: "autre-mot-de-passe", confirmation: true });
    assert.equal(store.lireJetonCompte(), null);
    assert.equal(f.requetes[5]!.methode, "DELETE");
    assert.deepEqual(f.requetes[5]!.corps, { mot_de_passe: "autre-mot-de-passe", confirmation: true });
  });

  it("déconnexion : purge locale même si le serveur répond 401", async () => {
    const f = fetchFactice([{ status: 401, corps: { detail: "jeton_revoque" } }]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store });
    await assert.rejects(c.deconnexion(), ApiError);
    assert.equal(store.lireJetonCompte(), null);
  });

  it("effacement RGPD : purge le jeton élève de l'enfant", async () => {
    const eff = echantillon(contrat.appels.find((a) => a.nom === "effacement_rgpd")!.reponse);
    const f = fetchFactice([{ status: 200, corps: eff }]);
    const store = new MemoryTokenStore();
    store.ecrireJetonCompte("compte");
    store.ecrireJetonEleve(PSEUDO, { token: "e", expireA: Number.MAX_SAFE_INTEGER });
    const c = new MikaClient({ baseUrl: BASE, fetchImpl: f.impl, tokenStore: store });
    await c.effacerRgpdEleve(PSEUDO);
    assert.equal(store.lireJetonEleve(PSEUDO), null);
  });

  it("aucune écriture console pendant les appels (jamais de log du jeton)", async () => {
    const methodes = ["log", "info", "warn", "error", "debug", "trace"] as const;
    const originaux = methodes.map((m) => console[m]);
    const ecrits: unknown[][] = [];
    for (const m of methodes) console[m] = (...a: unknown[]) => { ecrits.push(a); };
    try {
      for (const appel of contrat.appels) {
        const { client } = clientPour(appel, [{
          status: appel.statut_http, corps: appel.statut_http === 204 ? undefined : echantillon(appel.reponse),
        }]);
        await INVOCATIONS[appel.nom](client).catch(() => undefined);
      }
    } finally {
      methodes.forEach((m, i) => { console[m] = originaux[i]!; });
    }
    assert.deepEqual(ecrits, []);
  });
});

describe("validateur runtime", () => {
  const soumission = echantillon(contrat.appels.find((a) => a.nom === "soumettre_exercice")!.reponse) as Record<string, unknown>;

  it("progression : champ optionnel (absent, null ou présent)", () => {
    const { progression: _p, ...sans } = soumission;
    assert.equal("progression" in valider(vReponseSoumission, sans, { strict: true }), false);
    assert.equal(valider(vReponseSoumission, { ...soumission, progression: null }).progression, null);
    assert.equal(valider(vReponseSoumission, soumission).progression?.niveau, "EN_COURS");
  });

  it("progression.niveau et etat_maitrise : valeurs hors énumération refusées", () => {
    const prog = soumission["progression"] as Record<string, unknown>;
    assert.throws(() => valider(vReponseSoumission, { ...soumission, progression: { ...prog, niveau: "MAITRISE" } }), ErreurContrat);
    for (const n of ["NON_EVALUEE", "NON_ACQUISE", "FRAGILE", "EN_COURS", "MAITRISEE"]) {
      valider(vReponseSoumission, { ...soumission, progression: { ...prog, niveau: n } });
    }
    for (const e of ["INCONNU", "FRAGILE", "EN_COURS", "ACQUIS_ASSISTE", "ACQUIS_AUTONOME", "A_REVOIR", "MAITRISE"]) {
      valider(vReponseSoumission, { ...soumission, etat_maitrise: e });
    }
    assert.throws(() => valider(vReponseSoumission, { ...soumission, etat_maitrise: "MAITRISEE" }), ErreurContrat);
  });

  it("mode strict : clé inconnue refusée ; souple : tolérée ; clé manquante toujours refusée", () => {
    assert.throws(() => valider(vReponseSoumission, { ...soumission, nouveau: 1 }, { strict: true }), ErreurContrat);
    valider(vReponseSoumission, { ...soumission, nouveau: 1 });
    const { est_correct: _e, ...incomplet } = soumission;
    assert.throws(() => valider(vReponseSoumission, incomplet), /est_correct/);
  });

  it("tableau de bord parent : schéma FERMÉ même en mode souple (minimisation)", () => {
    const d = echantillon(contrat.appels.find((a) => a.nom === "dashboard_parent")!.reponse) as Record<string, unknown>;
    valider(vDashboardParent, d);
    assert.throws(() => valider(vDashboardParent, { ...d, email: "fuite@example.com" }), ErreurContrat);
    const stats = d["statistiques_pedagogiques"] as Record<string, unknown>;
    assert.throws(() => valider(vDashboardParent, { ...d, statistiques_pedagogiques: { ...stats, reponses: [] } }), ErreurContrat);
  });
});
