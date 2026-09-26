// Les exemples s'exécutent réellement (type stripping Node) et suivent les machines d'état.

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { MemoryTokenStore, MikaClient } from "../client.ts";
import { chargerDashboard } from "../examples/dashboard-parent.ts";
import { confirmerDepuisLien, inscrire, renvoyerCourriel } from "../examples/inscription-verification.ts";
import { saisirCode } from "../examples/invitation-rattachement.ts";
import { effacerEnfant } from "../examples/rgpd.ts";
import { demarrerTutorat } from "../examples/seance-mika.ts";
import { fetchFactice } from "./contrat.ts";
import type { ReponseFactice } from "./contrat.ts";

const compte = { id: 1, email: "a@b.c", prenom: null, role: "parent", statut_abonnement: "aucun", email_verifie: false };
const client = (reponses: ReponseFactice[], compteConnecte = true) => {
  const store = new MemoryTokenStore();
  if (compteConnecte) store.ecrireJetonCompte("c");
  store.ecrireJetonEleve("e1", { token: "e", expireA: Number.MAX_SAFE_INTEGER });
  return new MikaClient({ baseUrl: "https://api.test", fetchImpl: fetchFactice(reponses).impl, tokenStore: store });
};

describe("exemples", () => {
  it("inscription → renvoi 503 → lien du courriel → CONNECTE", async () => {
    const auth = await inscrire(client([{ status: 201, corps: { token: "t", compte } }], false), "a@b.c", "12345678");
    assert.equal(auth.etat, "INSCRIT_NON_VERIFIE");
    const v = await renvoyerCourriel(client([{ status: 503, corps: { detail: "courriel_indisponible" } }]), { etat: "ENVOYEE" });
    assert.equal(v.etat, "ECHEC_ENVOI");
    const r = await confirmerDepuisLien(client([
      { status: 200, corps: { statut: "EMAIL_VERIFIED" } }, { status: 200, corps: { ...compte, email_verifie: true } },
    ]), "jeton", auth);
    assert.equal(r.auth.etat, "CONNECTE");
    assert.equal(r.verification.etat, "VERIFIEE");
    const refus = await confirmerDepuisLien(client([{ status: 400, corps: { detail: "jeton_invalide_ou_expire" } }]), "x", auth);
    assert.equal(refus.verification.etat, "JETON_INVALIDE");
  });

  it("saisie du code : 403 email_non_verifie ⇒ vérification ; case non cochée ⇒ aucun appel", async () => {
    const e = await saisirCode(client([{ status: 403, corps: { detail: "email_non_verifie" } }]), "abcd", true);
    assert.equal(e.etat, "REFUSEE_EMAIL_NON_VERIFIE");
    const rien = await saisirCode(client([]), "abcd", false);
    assert.equal(rien.etat, "CODE_EMIS");
  });

  it("dashboard 403 ⇒ LIEN_REVOQUE ; effacement ; tuteur sans contenu ⇒ null", async () => {
    const r = await chargerDashboard(client([{ status: 403, corps: { detail: "acces_refuse" } }]),
      { etat: "ACCEPTEE", pseudo: "e1", relation: "parent", dejaLie: false });
    assert.equal(r.lien.etat, "LIEN_REVOQUE");
    assert.equal(await effacerEnfant(client([]), "e1", false), false);
    assert.equal(await demarrerTutorat(client([{ status: 404, corps: { detail: "exercice_indisponible" } }]), "e1", "x"), null);
  });
});
