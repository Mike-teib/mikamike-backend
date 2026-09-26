// Parcours 1 — Inscription puis vérification de l'adresse (FRONT_IMPLEMENTATION_PACK §4).
// Page d'inscription → bandeau « vérifiez votre adresse » → page /verifier?jeton=… (lien du courriel).

import { transition, transitionVerification } from "../auth-state.ts";
import type { EtatAuth, EtatVerification } from "../auth-state.ts";
import { ApiError, MikaClient } from "../client.ts";

export async function inscrire(client: MikaClient, email: string, motDePasse: string): Promise<EtatAuth> {
  try {
    const r = await client.inscription({ email, mot_de_passe: motDePasse, role: "parent" });
    // Le jeton de compte est déjà dans le TokenStore du client ; on ne le manipule jamais ici.
    return transition({ etat: "ANONYME", raison: null }, { type: "INSCRIPTION_REUSSIE", compte: r.compte });
  } catch (e) {
    if (e instanceof ApiError && e.code === "email_deja_utilise") throw new Error("Cette adresse est déjà utilisée.");
    if (e instanceof ApiError && e.status === 422) throw new Error("Adresse ou mot de passe (8 caractères min.) invalide.");
    if (e instanceof ApiError && e.estLimite) throw new Error(`Trop d'essais : réessayez dans ${e.retryAfter ?? 60} s.`);
    throw e;
  }
}

/** Bouton « renvoyer le courriel » : gère le 503 `courriel_indisponible` (fournisseur en panne). */
export async function renvoyerCourriel(client: MikaClient, etat: EtatVerification): Promise<EtatVerification> {
  try {
    const r = await client.demanderVerification();
    return transitionVerification(etat, { type: "DEMANDE_ACCEPTEE", statut: r.statut });
  } catch (e) {
    if (e instanceof ApiError && e.status === 503) return transitionVerification(etat, { type: "DEMANDE_ECHOUEE" });
    throw e;
  }
}

/**
 * Page du lien : poste le jeton UNE seule fois (ne pas le stocker, le retirer de l'URL ensuite
 * avec history.replaceState), puis relit le profil si une session est ouverte.
 */
export async function confirmerDepuisLien(client: MikaClient, jeton: string, auth: EtatAuth): Promise<{
  auth: EtatAuth; verification: EtatVerification;
}> {
  let verification: EtatVerification = { etat: "ENVOYEE" };
  try {
    await client.verifierEmail({ jeton });
  } catch (e) {
    if (e instanceof ApiError && e.code === "jeton_invalide_ou_expire") {
      // Message unique : « lien expiré ou déjà utilisé » + bouton « renvoyer » si connecté.
      return { auth, verification: transitionVerification(verification, { type: "CONFIRMATION_REFUSEE" }) };
    }
    throw e;
  }
  verification = transitionVerification(verification, { type: "CONFIRMATION_REUSSIE" });
  let a = transition(auth, { type: "EMAIL_CONFIRME" });
  if (client.connecte) a = transition(a, { type: "PROFIL_CHARGE", compte: await client.moi() });
  return { auth: a, verification };
}
