// Tests unitaires de la machine d'état du rattachement parent ↔ enfant (parent-link-state.ts).

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { TransitionRefusee } from "../auth-state.ts";
import {
  codeInutilisable, dashboardAccessible, doitVerifierEmail, ETAT_LIEN_INITIAL, expireLeEnMs, peutTransitionnerLien,
  transitionLien,
} from "../parent-link-state.ts";
import type { EtatLien, EvenementLien } from "../parent-link-state.ts";

const T = Date.parse("2026-09-26T10:00:00Z");
const P = "eleve-01";

describe("machine lien parent (invitation D8)", () => {
  const etats: Record<string, EtatLien> = {
    AUCUNE: { etat: "AUCUNE" },
    CODE_EMIS: { etat: "CODE_EMIS", expireA: T },
    ACCEPTEE: { etat: "ACCEPTEE", pseudo: P, relation: "parent", dejaLie: false },
    EXPIREE: { etat: "EXPIREE" },
    REFUSEE_EMAIL_NON_VERIFIE: { etat: "REFUSEE_EMAIL_NON_VERIFIE", expireA: T },
    INVALIDE: { etat: "INVALIDE" },
    LIEN_REVOQUE: { etat: "LIEN_REVOQUE", pseudo: P },
  };
  const evenements: Record<string, EvenementLien> = {
    CODE_EMIS: { type: "CODE_EMIS", expireA: T + 1 },
    ACCEPTATION_201: { type: "ACCEPTATION_REUSSIE", pseudo: P, relation: "parent" },
    REFUS_403_EMAIL: { type: "ACCEPTATION_REFUSEE", status: 403, code: "email_non_verifie" },
    REFUS_400: { type: "ACCEPTATION_REFUSEE", status: 400, code: "invitation_invalide" },
    REFUS_409_DEJA_LIE: { type: "ACCEPTATION_REFUSEE", status: 409, code: "deja_lie", pseudo: P },
    REFUS_422: { type: "ACCEPTATION_REFUSEE", status: 422, code: null },
    TEMPS_AVANT: { type: "TEMPS", maintenant: T - 1 },
    TEMPS_APRES: { type: "TEMPS", maintenant: T },
    DASHBOARD_200: { type: "DASHBOARD_OK" },
    DASHBOARD_403: { type: "DASHBOARD_REFUSE", status: 403 },
    DASHBOARD_429: { type: "DASHBOARD_REFUSE", status: 429 },
    REVOCATION: { type: "LIEN_REVOQUE" },
  };
  const X = "X";
  const enAttente = (moi: string) => ({
    CODE_EMIS: moi === "REFUSEE_EMAIL_NON_VERIFIE" ? X : "CODE_EMIS", ACCEPTATION_201: "ACCEPTEE",
    REFUS_403_EMAIL: "REFUSEE_EMAIL_NON_VERIFIE", REFUS_400: "INVALIDE", REFUS_409_DEJA_LIE: "ACCEPTEE", REFUS_422: moi,
    TEMPS_AVANT: moi, TEMPS_APRES: "EXPIREE", DASHBOARD_200: X, DASHBOARD_403: X, DASHBOARD_429: X, REVOCATION: X,
  });
  const inactif = (moi: string) => ({
    CODE_EMIS: "CODE_EMIS", ACCEPTATION_201: X, REFUS_403_EMAIL: X, REFUS_400: X, REFUS_409_DEJA_LIE: X, REFUS_422: X,
    TEMPS_AVANT: moi, TEMPS_APRES: moi, DASHBOARD_200: X, DASHBOARD_403: X, DASHBOARD_429: X, REVOCATION: X,
  });
  const matrice: Record<string, Record<string, string>> = {
    AUCUNE: inactif("AUCUNE"),
    CODE_EMIS: enAttente("CODE_EMIS"),
    REFUSEE_EMAIL_NON_VERIFIE: enAttente("REFUSEE_EMAIL_NON_VERIFIE"),
    ACCEPTEE: {
      CODE_EMIS: X, ACCEPTATION_201: X, REFUS_403_EMAIL: X, REFUS_400: X, REFUS_409_DEJA_LIE: X, REFUS_422: X,
      TEMPS_AVANT: "ACCEPTEE", TEMPS_APRES: "ACCEPTEE", DASHBOARD_200: "ACCEPTEE", DASHBOARD_403: "LIEN_REVOQUE",
      DASHBOARD_429: "ACCEPTEE", REVOCATION: "LIEN_REVOQUE",
    },
    EXPIREE: inactif("EXPIREE"),
    INVALIDE: inactif("INVALIDE"),
    LIEN_REVOQUE: inactif("LIEN_REVOQUE"),
  };

  for (const [nomEtat, etat] of Object.entries(etats)) {
    for (const [nomEv, ev] of Object.entries(evenements)) {
      const attendu = matrice[nomEtat]?.[nomEv];
      it(`${nomEtat} × ${nomEv} → ${attendu}`, () => {
        assert.ok(attendu !== undefined, "matrice incomplète");
        const gele = Object.freeze({ ...etat });
        if (attendu === X) {
          assert.equal(peutTransitionnerLien(gele, ev), false);
          assert.throws(() => transitionLien(gele, ev), TransitionRefusee);
        } else {
          assert.equal(transitionLien(gele, ev).etat, attendu);
        }
      });
    }
  }

  it("dashboard accessible UNIQUEMENT après acceptation, plus après révocation (403)", () => {
    for (const [nom, e] of Object.entries(etats)) assert.equal(dashboardAccessible(e), nom === "ACCEPTEE", nom);
    let e = transitionLien(ETAT_LIEN_INITIAL, { type: "CODE_EMIS", expireA: expireLeEnMs("2026-09-28T10:00:00Z") });
    e = transitionLien(e, { type: "ACCEPTATION_REUSSIE", pseudo: P, relation: "parent" });
    assert.equal(dashboardAccessible(e), true);
    e = transitionLien(e, { type: "DASHBOARD_REFUSE", status: 403 });
    assert.deepEqual(e, { etat: "LIEN_REVOQUE", pseudo: P });
    assert.equal(dashboardAccessible(e), false);
  });

  it("email non vérifié : le code n'est pas consommé, l'acceptation réussit après vérification", () => {
    let e = transitionLien(ETAT_LIEN_INITIAL, { type: "CODE_EMIS", expireA: null });
    e = transitionLien(e, { type: "ACCEPTATION_REFUSEE", status: 403, code: "email_non_verifie" });
    assert.equal(doitVerifierEmail(e), true);
    e = transitionLien(e, { type: "ACCEPTATION_REUSSIE", pseudo: P, relation: "parent" });
    assert.equal(e.etat, "ACCEPTEE");
  });

  it("code sans échéance connue : TEMPS ne l'expire pas ; 409 deja_lie sans pseudo : inchangé", () => {
    const e: EtatLien = { etat: "CODE_EMIS", expireA: null };
    assert.deepEqual(transitionLien(e, { type: "TEMPS", maintenant: Number.MAX_SAFE_INTEGER }), e);
    assert.deepEqual(transitionLien(e, { type: "ACCEPTATION_REFUSEE", status: 409, code: "deja_lie" }), e);
    const d = transitionLien(e, { type: "ACCEPTATION_REFUSEE", status: 409, code: "deja_lie", pseudo: P });
    assert.equal(d.etat === "ACCEPTEE" && d.dejaLie, true);
  });

  it("codeInutilisable (message unique « code invalide ou expiré »)", () => {
    assert.equal(codeInutilisable({ etat: "INVALIDE" }), true);
    assert.equal(codeInutilisable({ etat: "EXPIREE" }), true);
    assert.equal(codeInutilisable({ etat: "CODE_EMIS", expireA: null }), false);
  });

  it("expireLeEnMs", () => {
    assert.equal(expireLeEnMs("2026-09-26T10:00:00Z"), T);
    assert.equal(expireLeEnMs("pas une date"), null);
  });
});
