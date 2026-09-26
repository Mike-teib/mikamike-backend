// Tests unitaires des machines d'état pures de auth-state.ts : matrice COMPLÈTE état × événement
// (transition attendue ou refus), états terminaux, pureté (entrées non modifiées).

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  aUnJetonDeCompte, afficherBandeauVerification, doitCreerNouvelleSeance, doitReemettreJeton, doitSeReconnecter,
  estTerminal, ETAT_AUTH_INITIAL, ETAT_SEANCE_INITIAL, ETAT_VERIFICATION_INITIAL, peutRenvoyerCourriel,
  peutTransitionner, peutTransitionnerSeance, peutTransitionnerVerification, raisonDepuisCode401, transition,
  TransitionRefusee, transitionSeance, transitionVerification,
} from "../auth-state.ts";
import type {
  EtatAuth, EtatSeance, EtatVerification, EvenementAuth, EvenementSeance, EvenementVerification,
} from "../auth-state.ts";
import type { Compte } from "../types.ts";

const compteNonVerifie: Compte = {
  id: 1, email: "p@example.com", prenom: null, role: "parent", statut_abonnement: "aucun", email_verifie: false,
};
const compteVerifie: Compte = { ...compteNonVerifie, email_verifie: true };

const figer = <T>(o: T): T => {
  if (typeof o === "object" && o !== null) {
    for (const v of Object.values(o)) figer(v);
    Object.freeze(o);
  }
  return o;
};

// --------------------------------------------------------------------------------------------
describe("machine auth (compte)", () => {
  const etats: Record<string, EtatAuth> = {
    ANONYME: { etat: "ANONYME", raison: null },
    INSCRIT_NON_VERIFIE: { etat: "INSCRIT_NON_VERIFIE", compte: compteNonVerifie },
    VERIFIE_AVEC_JETON: { etat: "VERIFIE", compte: compteNonVerifie, avecJeton: true },
    VERIFIE_SANS_JETON: { etat: "VERIFIE", compte: null, avecJeton: false },
    CONNECTE: { etat: "CONNECTE", compte: compteVerifie },
    SUPPRIME: { etat: "SUPPRIME" },
  };
  const evenements: Record<string, EvenementAuth> = {
    INSCRIPTION: { type: "INSCRIPTION_REUSSIE", compte: compteNonVerifie },
    CONNEXION_V: { type: "CONNEXION_REUSSIE", compte: compteVerifie },
    CONNEXION_NV: { type: "CONNEXION_REUSSIE", compte: compteNonVerifie },
    EMAIL_CONFIRME: { type: "EMAIL_CONFIRME" },
    PROFIL_V: { type: "PROFIL_CHARGE", compte: compteVerifie },
    PROFIL_NV: { type: "PROFIL_CHARGE", compte: compteNonVerifie },
    EMAIL_CHANGE: { type: "EMAIL_CHANGE", compte: compteVerifie },
    MDP: { type: "MOT_DE_PASSE_CHANGE", compte: compteVerifie },
    ERR_EXPIRE: { type: "ERREUR_AUTH", code: "jeton_expire" },
    ERR_REVOQUE: { type: "ERREUR_AUTH", code: "jeton_revoque" },
    ERR_INACTIVITE: { type: "ERREUR_AUTH", code: "session_inactivite_5min" },
    DECONNEXION: { type: "DECONNEXION" },
    SUPPRESSION: { type: "COMPTE_SUPPRIME" },
  };
  // Cible attendue : nom d'état (+ raison / avecJeton), ou "X" = refus.
  const X = "X";
  const A = (r: string) => `ANONYME:${r}`;
  const matrice: Record<string, Record<string, string>> = {
    ANONYME: {
      INSCRIPTION: "INSCRIT_NON_VERIFIE", CONNEXION_V: "CONNECTE", CONNEXION_NV: "INSCRIT_NON_VERIFIE",
      EMAIL_CONFIRME: "VERIFIE:sans", PROFIL_V: X, PROFIL_NV: X, EMAIL_CHANGE: X, MDP: X, ERR_EXPIRE: X,
      ERR_REVOQUE: X, ERR_INACTIVITE: X, DECONNEXION: X, SUPPRESSION: X,
    },
    INSCRIT_NON_VERIFIE: {
      INSCRIPTION: X, CONNEXION_V: X, CONNEXION_NV: X, EMAIL_CONFIRME: "VERIFIE:avec", PROFIL_V: "CONNECTE",
      PROFIL_NV: "INSCRIT_NON_VERIFIE", EMAIL_CHANGE: "INSCRIT_NON_VERIFIE", MDP: "CONNECTE",
      ERR_EXPIRE: A("expiration"), ERR_REVOQUE: A("revocation"), ERR_INACTIVITE: X, DECONNEXION: A("deconnexion"),
      SUPPRESSION: "SUPPRIME",
    },
    VERIFIE_AVEC_JETON: {
      INSCRIPTION: X, CONNEXION_V: X, CONNEXION_NV: X, EMAIL_CONFIRME: X, PROFIL_V: "CONNECTE",
      PROFIL_NV: "INSCRIT_NON_VERIFIE", EMAIL_CHANGE: "INSCRIT_NON_VERIFIE", MDP: "CONNECTE",
      ERR_EXPIRE: A("expiration"), ERR_REVOQUE: A("revocation"), ERR_INACTIVITE: X, DECONNEXION: A("deconnexion"),
      SUPPRESSION: "SUPPRIME",
    },
    VERIFIE_SANS_JETON: {
      INSCRIPTION: X, CONNEXION_V: "CONNECTE", CONNEXION_NV: "INSCRIT_NON_VERIFIE", EMAIL_CONFIRME: X, PROFIL_V: X,
      PROFIL_NV: X, EMAIL_CHANGE: X, MDP: X, ERR_EXPIRE: X, ERR_REVOQUE: X, ERR_INACTIVITE: X, DECONNEXION: X,
      SUPPRESSION: X,
    },
    CONNECTE: {
      INSCRIPTION: X, CONNEXION_V: X, CONNEXION_NV: X, EMAIL_CONFIRME: X, PROFIL_V: "CONNECTE",
      PROFIL_NV: "INSCRIT_NON_VERIFIE", EMAIL_CHANGE: "INSCRIT_NON_VERIFIE", MDP: "CONNECTE",
      ERR_EXPIRE: A("expiration"), ERR_REVOQUE: A("revocation"), ERR_INACTIVITE: X, DECONNEXION: A("deconnexion"),
      SUPPRESSION: "SUPPRIME",
    },
    SUPPRIME: Object.fromEntries(Object.keys(evenements).map((k) => [k, X])),
  };
  const resume = (e: EtatAuth): string =>
    e.etat === "ANONYME" ? `ANONYME:${e.raison}` : e.etat === "VERIFIE" ? `VERIFIE:${e.avecJeton ? "avec" : "sans"}` : e.etat;

  for (const [nomEtat, etat] of Object.entries(etats)) {
    for (const [nomEv, ev] of Object.entries(evenements)) {
      const attendu = matrice[nomEtat]?.[nomEv];
      it(`${nomEtat} × ${nomEv} → ${attendu}`, () => {
        assert.ok(attendu !== undefined, "matrice incomplète");
        const gele = figer(structuredClone(etat));
        if (attendu === X) {
          assert.equal(peutTransitionner(gele, ev), false);
          assert.throws(() => transition(gele, ev), TransitionRefusee);
        } else {
          assert.equal(peutTransitionner(gele, ev), true);
          assert.equal(resume(transition(gele, ev)), attendu);
        }
      });
    }
  }

  it("SUPPRIME est le seul état terminal", () => {
    for (const [nom, e] of Object.entries(etats)) assert.equal(estTerminal(e), nom === "SUPPRIME", nom);
  });

  it("parcours nominal ANONYME → INSCRIT_NON_VERIFIE → VERIFIE → CONNECTE", () => {
    let e = ETAT_AUTH_INITIAL;
    e = transition(e, { type: "INSCRIPTION_REUSSIE", compte: compteNonVerifie });
    assert.equal(afficherBandeauVerification(e), true);
    e = transition(e, { type: "EMAIL_CONFIRME" });
    assert.equal(e.etat, "VERIFIE");
    e = transition(e, { type: "PROFIL_CHARGE", compte: compteVerifie });
    assert.deepEqual(e, { etat: "CONNECTE", compte: compteVerifie });
    assert.equal(afficherBandeauVerification(e), false);
    assert.equal(aUnJetonDeCompte(e), true);
  });

  it("le changement d'adresse force la revérification même si le serveur renvoie email_verifie=true", () => {
    const e = transition({ etat: "CONNECTE", compte: compteVerifie }, { type: "EMAIL_CHANGE", compte: compteVerifie });
    assert.equal(e.etat, "INSCRIT_NON_VERIFIE");
    assert.equal(e.etat === "INSCRIT_NON_VERIFIE" && e.compte.email_verifie, false);
  });

  it("codes 401 → raisons (et codes qui ne déconnectent pas)", () => {
    assert.equal(raisonDepuisCode401("jeton_expire"), "expiration");
    assert.equal(raisonDepuisCode401("jeton_revoque"), "revocation");
    assert.equal(raisonDepuisCode401("token_invalide"), "jeton_invalide");
    assert.equal(raisonDepuisCode401("jeton_invalide"), "jeton_invalide");
    assert.equal(raisonDepuisCode401("token_absent"), "jeton_absent");
    assert.equal(raisonDepuisCode401("jeton_requis"), "jeton_absent");
    assert.equal(raisonDepuisCode401("jeton_compte_requis"), "jeton_absent");
    assert.equal(raisonDepuisCode401("compte_inconnu"), "compte_inconnu");
    assert.equal(raisonDepuisCode401("session_inactivite_5min"), null);
    assert.equal(raisonDepuisCode401("identifiants_invalides"), null);
    const e = transition({ etat: "CONNECTE", compte: compteVerifie }, { type: "ERREUR_AUTH", code: "compte_inconnu" });
    assert.deepEqual(e, { etat: "ANONYME", raison: "compte_inconnu" });
  });

  it("aUnJetonDeCompte", () => {
    assert.equal(aUnJetonDeCompte(etats["ANONYME"]!), false);
    assert.equal(aUnJetonDeCompte(etats["VERIFIE_SANS_JETON"]!), false);
    assert.equal(aUnJetonDeCompte(etats["VERIFIE_AVEC_JETON"]!), true);
    assert.equal(aUnJetonDeCompte(etats["SUPPRIME"]!), false);
  });
});

// --------------------------------------------------------------------------------------------
describe("machine vérification e-mail", () => {
  const etats: Record<string, EtatVerification> = {
    NON_DEMANDEE: { etat: "NON_DEMANDEE" }, ENVOYEE: { etat: "ENVOYEE" }, ECHEC_ENVOI: { etat: "ECHEC_ENVOI" },
    VERIFIEE: { etat: "VERIFIEE" }, JETON_INVALIDE: { etat: "JETON_INVALIDE" },
  };
  const evenements: Record<string, EvenementVerification> = {
    STATUT_UNVERIFIED: { type: "STATUT_LU", statut: "EMAIL_UNVERIFIED" },
    STATUT_CREATED: { type: "STATUT_LU", statut: "VERIFICATION_TOKEN_CREATED" },
    STATUT_VERIFIED: { type: "STATUT_LU", statut: "EMAIL_VERIFIED" },
    DEMANDE_202: { type: "DEMANDE_ACCEPTEE", statut: "VERIFICATION_TOKEN_CREATED" },
    DEMANDE_202_DEJA: { type: "DEMANDE_ACCEPTEE", statut: "EMAIL_VERIFIED" },
    DEMANDE_503: { type: "DEMANDE_ECHOUEE" },
    CONFIRMATION_200: { type: "CONFIRMATION_REUSSIE" },
    CONFIRMATION_400: { type: "CONFIRMATION_REFUSEE" },
    ADRESSE_CHANGEE: { type: "ADRESSE_CHANGEE" },
  };
  const nonVerifie = {
    STATUT_UNVERIFIED: "NON_DEMANDEE", STATUT_CREATED: "ENVOYEE", STATUT_VERIFIED: "VERIFIEE", DEMANDE_202: "ENVOYEE",
    DEMANDE_202_DEJA: "VERIFIEE", DEMANDE_503: "ECHEC_ENVOI", CONFIRMATION_200: "VERIFIEE",
    CONFIRMATION_400: "JETON_INVALIDE", ADRESSE_CHANGEE: "ENVOYEE",
  };
  const matrice: Record<string, Record<string, string>> = {
    NON_DEMANDEE: nonVerifie, ENVOYEE: nonVerifie, ECHEC_ENVOI: nonVerifie, JETON_INVALIDE: nonVerifie,
    VERIFIEE: {
      STATUT_UNVERIFIED: "NON_DEMANDEE", STATUT_CREATED: "ENVOYEE", STATUT_VERIFIED: "VERIFIEE", DEMANDE_202: "X",
      DEMANDE_202_DEJA: "X", DEMANDE_503: "X", CONFIRMATION_200: "X", CONFIRMATION_400: "X", ADRESSE_CHANGEE: "ENVOYEE",
    },
  };
  for (const [nomEtat, etat] of Object.entries(etats)) {
    for (const [nomEv, ev] of Object.entries(evenements)) {
      const attendu = matrice[nomEtat]?.[nomEv];
      it(`${nomEtat} × ${nomEv} → ${attendu}`, () => {
        if (attendu === "X") {
          assert.equal(peutTransitionnerVerification(etat, ev), false);
          assert.throws(() => transitionVerification(etat, ev), TransitionRefusee);
        } else {
          assert.equal(transitionVerification(figer({ ...etat }), ev).etat, attendu);
        }
      });
    }
  }

  it("parcours avec panne du fournisseur (503) puis succès", () => {
    let e = ETAT_VERIFICATION_INITIAL;
    e = transitionVerification(e, { type: "DEMANDE_ECHOUEE" });
    assert.equal(e.etat, "ECHEC_ENVOI");
    assert.equal(peutRenvoyerCourriel(e), true);
    e = transitionVerification(e, { type: "DEMANDE_ACCEPTEE", statut: "VERIFICATION_TOKEN_CREATED" });
    e = transitionVerification(e, { type: "CONFIRMATION_REFUSEE" });
    assert.equal(e.etat, "JETON_INVALIDE");
    e = transitionVerification(e, { type: "DEMANDE_ACCEPTEE", statut: "VERIFICATION_TOKEN_CREATED" });
    e = transitionVerification(e, { type: "CONFIRMATION_REUSSIE" });
    assert.equal(e.etat, "VERIFIEE");
    assert.equal(peutRenvoyerCourriel(e), false);
  });
});

// --------------------------------------------------------------------------------------------
describe("machine séance élève", () => {
  const P = "eleve-01";
  const T = 1_000_000;
  const jeton = (pseudo = P, expireA = T + 7_200_000): EvenementSeance => ({ type: "JETON_OBTENU", pseudo, expireA });
  const err = (status: number, code: string | null): EvenementSeance => ({ type: "ERREUR", status, code });
  const ouverte: EtatSeance = { etat: "OUVERTE", pseudo: P, expireA: T + 7_200_000, reemis: false, sessionId: "s1" };

  it("AUCUNE → JETON_PRET → OUVERTE (POST /session/nouvelle)", () => {
    let e = ETAT_SEANCE_INITIAL;
    assert.equal(doitCreerNouvelleSeance(e), false);
    e = transitionSeance(e, jeton());
    assert.equal(e.etat, "JETON_PRET");
    assert.equal(doitCreerNouvelleSeance(e), true);
    e = transitionSeance(e, { type: "SEANCE_CREEE", sessionId: "s1" });
    assert.deepEqual(e, ouverte);
    assert.deepEqual(transitionSeance(e, { type: "ACTIVITE" }), ouverte);
  });

  it("inactivité 5 min ⇒ EXPIREE(inactivite) ⇒ nouvelle séance sans nouveau jeton", () => {
    const e = transitionSeance(ouverte, err(401, "session_inactivite_5min"));
    assert.equal(e.etat, "EXPIREE");
    assert.equal(e.etat === "EXPIREE" && e.raison, "inactivite");
    assert.equal(doitCreerNouvelleSeance(e), true);
    assert.equal(doitReemettreJeton(e), false);
    const r = transitionSeance(e, { type: "SEANCE_CREEE", sessionId: "s2" });
    assert.equal(r.etat === "OUVERTE" && r.sessionId, "s2");
  });

  it("jeton_expire ⇒ une seule ré-émission, puis reconnexion si le nouveau jeton expire aussi sans succès", () => {
    let e = transitionSeance(ouverte, err(401, "jeton_expire"));
    assert.equal(doitReemettreJeton(e), true);
    assert.equal(doitSeReconnecter(e), false);
    e = transitionSeance(e, jeton(P, T + 9_000_000));
    assert.equal(e.etat === "JETON_PRET" && e.reemis, true);
    e = transitionSeance(e, { type: "SEANCE_CREEE", sessionId: "s3" });
    e = transitionSeance(e, err(401, "jeton_expire"));
    assert.equal(doitSeReconnecter(e), true);
    assert.equal(peutTransitionnerSeance(e, jeton()), false);
    assert.throws(() => transitionSeance(e, jeton()), TransitionRefusee);
    assert.equal(transitionSeance(e, { type: "FERMER" }).etat, "AUCUNE");
  });

  it("un succès après ré-émission réarme la ré-émission suivante", () => {
    let e = transitionSeance(ouverte, err(401, "jeton_expire"));
    e = transitionSeance(e, jeton());
    e = transitionSeance(e, { type: "SEANCE_CREEE", sessionId: "s4" });
    e = transitionSeance(e, { type: "ACTIVITE" });
    e = transitionSeance(e, err(401, "jeton_expire"));
    assert.equal(doitReemettreJeton(e), true);
  });

  it("expiration par l'horloge (TEMPS ≥ expireA)", () => {
    assert.deepEqual(transitionSeance(ouverte, { type: "TEMPS", maintenant: T }), ouverte);
    const e = transitionSeance(ouverte, { type: "TEMPS", maintenant: T + 7_200_000 });
    assert.equal(e.etat === "EXPIREE" && e.raison, "jeton_expire");
    assert.equal(peutTransitionnerSeance(ETAT_SEANCE_INITIAL, { type: "TEMPS", maintenant: T }), false);
  });

  it("jeton_revoque ⇒ REVOQUEE (retour au choix d'enfant) depuis tout état actif", () => {
    const actifs: EtatSeance[] = [
      { etat: "JETON_PRET", pseudo: P, expireA: T, reemis: false }, ouverte,
      { etat: "EXPIREE", pseudo: P, expireA: T, raison: "inactivite", reemissionTentee: false },
    ];
    for (const e of actifs) assert.deepEqual(transitionSeance(e, err(401, "jeton_revoque")), { etat: "REVOQUEE", pseudo: P });
    const r: EtatSeance = { etat: "REVOQUEE", pseudo: P };
    assert.equal(peutTransitionnerSeance(r, err(403, "acces_refuse")), false);
    assert.equal(peutTransitionnerSeance(r, { type: "SEANCE_CREEE", sessionId: "x" }), false);
    assert.equal(transitionSeance(r, jeton()).etat, "JETON_PRET");
  });

  it("404 session_inconnue ⇒ JETON_PRET ; autres erreurs ⇒ inchangé", () => {
    assert.equal(transitionSeance(ouverte, err(404, "session_inconnue")).etat, "JETON_PRET");
    for (const [s, c] of [[403, "acces_refuse"], [413, "etat_session_trop_volumineux"], [429, "trop_de_tentatives"], [409, "version_perimee"]] as const) {
      assert.deepEqual(transitionSeance(ouverte, err(s, c)), ouverte);
    }
  });

  it("événements invalides refusés", () => {
    const refus: [EtatSeance, EvenementSeance][] = [
      [ETAT_SEANCE_INITIAL, { type: "SEANCE_CREEE", sessionId: "s" }],
      [ETAT_SEANCE_INITIAL, { type: "ACTIVITE" }],
      [ETAT_SEANCE_INITIAL, err(401, "jeton_expire")],
      [{ etat: "JETON_PRET", pseudo: P, expireA: T, reemis: false }, { type: "ACTIVITE" }],
      [{ etat: "JETON_PRET", pseudo: P, expireA: T, reemis: false }, err(401, "session_inactivite_5min")],
      [ouverte, { type: "SEANCE_CREEE", sessionId: "s" }],
      [ouverte, jeton("autre-eleve")],
      [{ etat: "EXPIREE", pseudo: P, expireA: T, raison: "jeton_expire", reemissionTentee: false }, { type: "SEANCE_CREEE", sessionId: "s" }],
      [{ etat: "EXPIREE", pseudo: P, expireA: T, raison: "inactivite", reemissionTentee: false }, { type: "ACTIVITE" }],
    ];
    for (const [e, ev] of refus) {
      assert.equal(peutTransitionnerSeance(e, ev), false, `${e.etat} × ${ev.type}`);
      assert.throws(() => transitionSeance(e, ev), TransitionRefusee);
    }
  });

  it("renouvellement anticipé du jeton pendant une séance ouverte", () => {
    const e = transitionSeance(ouverte, jeton(P, T + 99));
    assert.equal(e.etat === "OUVERTE" && e.expireA, T + 99);
  });
});
