// parent-link-state.ts — Machine d'état PURE du rattachement parent ↔ enfant par invitation (D8).
//
//            CODE_EMIS (enfant : POST /liens/invitations 201, ou code remis par l'établissement)
//   AUCUNE ─────────────▶ CODE_EMIS ──ACCEPTATION_REUSSIE (201)──────────────▶ ACCEPTEE ⇒ dashboard accessible
//                            │  ├──ACCEPTATION_REFUSEE 403 email_non_verifie──▶ REFUSEE_EMAIL_NON_VERIFIE
//                            │  │      (code NON consommé : après vérification, ACCEPTATION_REUSSIE ⇒ ACCEPTEE)
//                            │  ├──ACCEPTATION_REFUSEE 400 invitation_invalide ▶ INVALIDE (inconnu/utilisé/expiré)
//                            │  ├──ACCEPTATION_REFUSEE 409 deja_lie ─────────▶ ACCEPTEE (dejaLie)
//                            └──TEMPS ≥ expire_le ─────────────────────────────▶ EXPIREE
//   ACCEPTEE ──DASHBOARD_REFUSE (403) | LIEN_REVOQUE (effacement RGPD, suppression de compte) ▶ LIEN_REVOQUE
//   EXPIREE | INVALIDE | LIEN_REVOQUE ──CODE_EMIS──▶ CODE_EMIS (nouveau code)
//
// Le code lui-même n'est JAMAIS dans l'état (à afficher une fois, jamais stocké).

import { TransitionRefusee } from "./auth-state.ts";
import type { Relation } from "./types.ts";

export type EtatLien =
  | { readonly etat: "AUCUNE" }
  /** `expireA` : ms epoch (depuis `expire_le`), null si inconnu (code reçu hors application). */
  | { readonly etat: "CODE_EMIS"; readonly expireA: number | null }
  | { readonly etat: "ACCEPTEE"; readonly pseudo: string; readonly relation: Relation; readonly dejaLie: boolean }
  | { readonly etat: "EXPIREE" }
  | { readonly etat: "REFUSEE_EMAIL_NON_VERIFIE"; readonly expireA: number | null }
  | { readonly etat: "INVALIDE" }
  | { readonly etat: "LIEN_REVOQUE"; readonly pseudo: string };

export type EvenementLien =
  | { readonly type: "CODE_EMIS"; readonly expireA: number | null }
  | { readonly type: "ACCEPTATION_REUSSIE"; readonly pseudo: string; readonly relation: Relation }
  | { readonly type: "ACCEPTATION_REFUSEE"; readonly status: number; readonly code: string | null; readonly pseudo?: string }
  | { readonly type: "TEMPS"; readonly maintenant: number }
  | { readonly type: "DASHBOARD_OK" }
  | { readonly type: "DASHBOARD_REFUSE"; readonly status: number }
  | { readonly type: "LIEN_REVOQUE" };

export const ETAT_LIEN_INITIAL: EtatLien = { etat: "AUCUNE" };

/** Convertit `expire_le` (ISO 8601, suffixe Z) en ms epoch ; null si illisible. */
export function expireLeEnMs(expireLe: string): number | null {
  const t = Date.parse(expireLe);
  return Number.isNaN(t) ? null : t;
}

function transitionLienOuNull(e: EtatLien, ev: EvenementLien): EtatLien | null {
  switch (ev.type) {
    case "CODE_EMIS":
      return e.etat === "ACCEPTEE" || e.etat === "REFUSEE_EMAIL_NON_VERIFIE" ? null : { etat: "CODE_EMIS", expireA: ev.expireA };
    case "ACCEPTATION_REUSSIE":
      return e.etat === "CODE_EMIS" || e.etat === "REFUSEE_EMAIL_NON_VERIFIE"
        ? { etat: "ACCEPTEE", pseudo: ev.pseudo, relation: ev.relation, dejaLie: false } : null;
    case "ACCEPTATION_REFUSEE": {
      if (e.etat !== "CODE_EMIS" && e.etat !== "REFUSEE_EMAIL_NON_VERIFIE") return null;
      if (ev.status === 403 && ev.code === "email_non_verifie") return { etat: "REFUSEE_EMAIL_NON_VERIFIE", expireA: e.expireA };
      if (ev.status === 400 && ev.code === "invitation_invalide") return { etat: "INVALIDE" };
      if (ev.status === 409 && ev.code === "deja_lie" && ev.pseudo !== undefined) {
        return { etat: "ACCEPTEE", pseudo: ev.pseudo, relation: "parent", dejaLie: true };
      }
      return e; // 409 deja_lie sans pseudo connu, 422 (confirmation), 429 : l'état ne change pas
    }
    case "TEMPS":
      if ((e.etat === "CODE_EMIS" || e.etat === "REFUSEE_EMAIL_NON_VERIFIE") && e.expireA !== null && ev.maintenant >= e.expireA) {
        return { etat: "EXPIREE" };
      }
      return e;
    case "DASHBOARD_OK":
      return e.etat === "ACCEPTEE" ? e : null;
    case "DASHBOARD_REFUSE":
      if (e.etat !== "ACCEPTEE") return null;
      return ev.status === 403 ? { etat: "LIEN_REVOQUE", pseudo: e.pseudo } : e;
    case "LIEN_REVOQUE":
      return e.etat === "ACCEPTEE" ? { etat: "LIEN_REVOQUE", pseudo: e.pseudo } : null;
  }
}

export function transitionLien(etat: EtatLien, evenement: EvenementLien): EtatLien {
  const r = transitionLienOuNull(etat, evenement);
  if (r === null) throw new TransitionRefusee("lien", etat.etat, evenement.type);
  return r;
}

export function peutTransitionnerLien(etat: EtatLien, evenement: EvenementLien): boolean {
  return transitionLienOuNull(etat, evenement) !== null;
}

/** Le tableau de bord n'est accessible (et appelé) qu'une fois le lien accepté. */
export function dashboardAccessible(etat: EtatLien): boolean {
  return etat.etat === "ACCEPTEE";
}

/** Rediriger vers la vérification d'adresse (data-testid `bandeau-verif-email`). */
export function doitVerifierEmail(etat: EtatLien): boolean {
  return etat.etat === "REFUSEE_EMAIL_NON_VERIFIE";
}

/** Message unique « code invalide ou expiré » (pas d'oracle côté serveur). */
export function codeInutilisable(etat: EtatLien): boolean {
  return etat.etat === "INVALIDE" || etat.etat === "EXPIREE";
}
