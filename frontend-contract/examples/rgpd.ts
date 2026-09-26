// Parcours 5 — RGPD : export (enfant, compte) et suppression (effacement enfant, suppression du compte).

import { transition } from "../auth-state.ts";
import type { EtatAuth } from "../auth-state.ts";
import { ApiError, MikaClient } from "../client.ts";
import type { ExportCompte, ExportRgpdEleve } from "../types.ts";

/** Export des données d'apprentissage de l'enfant, proposé en téléchargement JSON. */
export async function exporterEnfant(parent: MikaClient, pseudo: string): Promise<ExportRgpdEleve | null> {
  try {
    return await parent.exportRgpdEleve(pseudo);
  } catch (e) {
    if (e instanceof ApiError && e.code === "aucune_donnee_trouvee_pour_cet_identifiant") return null;
    throw e;
  }
}

export function exporterCompte(client: MikaClient): Promise<ExportCompte> {
  return client.exportCompte();
}

/** Effacement (double confirmation côté interface) : PARENT lié uniquement (D9). */
export async function effacerEnfant(parent: MikaClient, pseudo: string, doubleConfirmation: boolean): Promise<boolean> {
  if (!doubleConfirmation) return false;
  await parent.effacerRgpdEleve(pseudo); // jetons élève révoqués côté serveur, purgés localement
  return true;
}

/** Suppression du compte : mot de passe + case cochée ; 409 abonnement_en_cours ⇒ résilier d'abord. */
export async function supprimerMonCompte(client: MikaClient, auth: EtatAuth, motDePasse: string): Promise<EtatAuth> {
  try {
    await client.supprimerCompte({ mot_de_passe: motDePasse, confirmation: true });
  } catch (e) {
    if (e instanceof ApiError && (e.code === "abonnement_en_cours" || e.code === "mot_de_passe_incorrect")) return auth;
    throw e;
  }
  return transition(auth, { type: "COMPTE_SUPPRIME" }); // SUPPRIME : état terminal
}
