// Parcours 2 — Invitation (enfant) puis rattachement (parent), décision D8.

import { expireLeEnMs, transitionLien } from "../parent-link-state.ts";
import type { EtatLien } from "../parent-link-state.ts";
import { ApiError, MikaClient } from "../client.ts";

/** Côté ENFANT (jeton élève) : afficher le code UNE fois, avec son heure d'expiration. */
export async function inviterUnParent(enfant: MikaClient, pseudo: string): Promise<{
  codeAAfficher: string; expireLe: string; etat: EtatLien;
}> {
  const r = await enfant.emettreInvitation({ student_pseudo_id: pseudo }); // porteur « eleve » par défaut
  return {
    codeAAfficher: r.code, // à afficher puis oublier : jamais de stockage, jamais de log
    expireLe: r.expire_le,
    etat: transitionLien({ etat: "AUCUNE" }, { type: "CODE_EMIS", expireA: expireLeEnMs(r.expire_le) }),
  };
}

/**
 * Côté PARENT (jeton de compte) : `confirmationCochee` provient de la case « je suis le parent de
 * cet enfant » ; `confirmation: true` n'est envoyé QUE si elle est cochée.
 */
export async function saisirCode(parent: MikaClient, codeSaisi: string, confirmationCochee: boolean,
                                 etat: EtatLien = { etat: "CODE_EMIS", expireA: null }): Promise<EtatLien> {
  if (!confirmationCochee) return etat; // bouton désactivé tant que la case n'est pas cochée
  try {
    const r = await parent.accepterInvitation({ code: codeSaisi.trim(), confirmation: true });
    return transitionLien(etat, { type: "ACCEPTATION_REUSSIE", pseudo: r.student_pseudo_id, relation: r.relation });
  } catch (e) {
    if (e instanceof ApiError && [400, 403, 409, 422].includes(e.status)) {
      // 403 email_non_verifie ⇒ rediriger vers la vérification ; 400 ⇒ « code invalide ou expiré » ;
      // 409 deja_lie ⇒ « déjà rattaché ».
      return transitionLien(etat, { type: "ACCEPTATION_REFUSEE", status: e.status, code: e.code });
    }
    throw e;
  }
}
