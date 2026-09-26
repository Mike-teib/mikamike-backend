// auth-state.ts — Machines d'état PURES (aucun effet, aucun appel réseau, aucune horloge
// implicite) : cycle de vie du compte, vérification d'adresse, séance élève Mika.
//
// `transition(etat, evenement)` renvoie le nouvel état ou lève `TransitionRefusee` si
// l'événement est invalide dans l'état courant. `peutTransitionner` permet de tester sans lever.
// Les jetons ne sont JAMAIS dans ces états (ils vivent dans le TokenStore du client).

import type { Compte, StatutVerificationEmail } from "./types.ts";

export class TransitionRefusee extends Error {
  readonly etat: string;
  readonly evenement: string;

  constructor(machine: string, etat: string, evenement: string) {
    super(`${machine} : événement ${evenement} refusé dans l'état ${etat}`);
    this.name = "TransitionRefusee";
    this.etat = etat;
    this.evenement = evenement;
  }
}

// ============================================================================================
// 1. Compte / session de compte
// ============================================================================================
/**
 * ANONYME ──INSCRIPTION_REUSSIE──▶ INSCRIT_NON_VERIFIE ──EMAIL_CONFIRME──▶ VERIFIE ──PROFIL_CHARGE/CONNEXION──▶ CONNECTE
 * États « avec jeton » : INSCRIT_NON_VERIFIE, CONNECTE (et VERIFIE si `avecJeton`).
 * 401 jeton_expire / jeton_revoque / … ⇒ ANONYME avec raison. COMPTE_SUPPRIME ⇒ SUPPRIME (terminal).
 */
export type RaisonDeconnexion =
  | "deconnexion"          // POST /comptes/deconnexion (204) : tous les appareils
  | "expiration"           // 401 jeton_expire
  | "revocation"           // 401 jeton_revoque (mot de passe / adresse changés ailleurs, déconnexion globale)
  | "jeton_invalide"       // 401 token_invalide / jeton_invalide
  | "jeton_absent"         // 401 token_absent / jeton_requis / jeton_compte_requis (bug du front)
  | "compte_inconnu";      // 401 compte_inconnu (compte supprimé ou désactivé)

export type EtatAuth =
  | { readonly etat: "ANONYME"; readonly raison: RaisonDeconnexion | null }
  | { readonly etat: "INSCRIT_NON_VERIFIE"; readonly compte: Compte }
  /** Adresse vérifiée (lien du courriel). `avecJeton=false` : lien ouvert hors session ⇒ se connecter. */
  | { readonly etat: "VERIFIE"; readonly compte: Compte | null; readonly avecJeton: boolean }
  | { readonly etat: "CONNECTE"; readonly compte: Compte }
  | { readonly etat: "SUPPRIME" };

export type EvenementAuth =
  | { readonly type: "INSCRIPTION_REUSSIE"; readonly compte: Compte }
  | { readonly type: "CONNEXION_REUSSIE"; readonly compte: Compte }
  /** POST /comptes/verification-email/confirmer → 200. */
  | { readonly type: "EMAIL_CONFIRME" }
  /** GET /comptes/moi → 200. */
  | { readonly type: "PROFIL_CHARGE"; readonly compte: Compte }
  /** POST /comptes/email → 200 : nouveau jeton, adresse à revérifier. */
  | { readonly type: "EMAIL_CHANGE"; readonly compte: Compte }
  /** POST /comptes/mot-de-passe → 200 : nouveau jeton, même état. */
  | { readonly type: "MOT_DE_PASSE_CHANGE"; readonly compte: Compte }
  /** 401 sur une route « compte » (le code `detail` décide de la raison). */
  | { readonly type: "ERREUR_AUTH"; readonly code: string }
  | { readonly type: "DECONNEXION" }
  /** DELETE /comptes/moi → 200. */
  | { readonly type: "COMPTE_SUPPRIME" };

export const ETAT_AUTH_INITIAL: EtatAuth = { etat: "ANONYME", raison: null };

/** Code 401 → raison ; null si le code n'invalide pas le jeton de compte. */
export function raisonDepuisCode401(code: string): RaisonDeconnexion | null {
  switch (code) {
    case "jeton_expire": return "expiration";
    case "jeton_revoque": return "revocation";
    case "token_invalide":
    case "jeton_invalide": return "jeton_invalide";
    case "token_absent":
    case "jeton_requis":
    case "jeton_compte_requis": return "jeton_absent";
    case "compte_inconnu": return "compte_inconnu";
    default: return null; // ex. session_inactivite_5min, identifiants_invalides : pas une perte de session
  }
}

const avecCompte = (compte: Compte): EtatAuth =>
  compte.email_verifie ? { etat: "CONNECTE", compte } : { etat: "INSCRIT_NON_VERIFIE", compte };

function transitionAuthOuNull(e: EtatAuth, ev: EvenementAuth): EtatAuth | null {
  if (e.etat === "SUPPRIME") return null; // terminal
  const avecJeton = e.etat === "INSCRIT_NON_VERIFIE" || e.etat === "CONNECTE" || (e.etat === "VERIFIE" && e.avecJeton);
  switch (ev.type) {
    case "INSCRIPTION_REUSSIE":
      return e.etat === "ANONYME" ? { etat: "INSCRIT_NON_VERIFIE", compte: ev.compte } : null;
    case "CONNEXION_REUSSIE":
      return e.etat === "ANONYME" || (e.etat === "VERIFIE" && !e.avecJeton) ? avecCompte(ev.compte) : null;
    case "EMAIL_CONFIRME":
      if (e.etat === "INSCRIT_NON_VERIFIE") return { etat: "VERIFIE", compte: e.compte, avecJeton: true };
      if (e.etat === "ANONYME") return { etat: "VERIFIE", compte: null, avecJeton: false };
      return null;
    case "PROFIL_CHARGE":
      return avecJeton ? avecCompte(ev.compte) : null;
    case "EMAIL_CHANGE":
      return e.etat === "CONNECTE" || e.etat === "INSCRIT_NON_VERIFIE" || (e.etat === "VERIFIE" && e.avecJeton)
        ? { etat: "INSCRIT_NON_VERIFIE", compte: { ...ev.compte, email_verifie: false } } : null;
    case "MOT_DE_PASSE_CHANGE":
      return avecJeton ? avecCompte(ev.compte) : null;
    case "ERREUR_AUTH": {
      const raison = raisonDepuisCode401(ev.code);
      return avecJeton && raison !== null ? { etat: "ANONYME", raison } : null;
    }
    case "DECONNEXION":
      return avecJeton ? { etat: "ANONYME", raison: "deconnexion" } : null;
    case "COMPTE_SUPPRIME":
      return avecJeton ? { etat: "SUPPRIME" } : null;
  }
}

export function transition(etat: EtatAuth, evenement: EvenementAuth): EtatAuth {
  const r = transitionAuthOuNull(etat, evenement);
  if (r === null) throw new TransitionRefusee("auth", etat.etat, evenement.type);
  return r;
}

export function peutTransitionner(etat: EtatAuth, evenement: EvenementAuth): boolean {
  return transitionAuthOuNull(etat, evenement) !== null;
}

export function estTerminal(etat: EtatAuth): boolean {
  return etat.etat === "SUPPRIME";
}

/** Le front détient-il (logiquement) un jeton de compte valide dans cet état ? */
export function aUnJetonDeCompte(etat: EtatAuth): boolean {
  return etat.etat === "INSCRIT_NON_VERIFIE" || etat.etat === "CONNECTE" || (etat.etat === "VERIFIE" && etat.avecJeton);
}

/** Bandeau « vérifiez votre adresse » (data-testid `bandeau-verif-email`). */
export function afficherBandeauVerification(etat: EtatAuth): boolean {
  return etat.etat === "INSCRIT_NON_VERIFIE";
}

// ============================================================================================
// 2. Vérification d'adresse e-mail
// ============================================================================================
/**
 * NON_DEMANDEE ──DEMANDE_ACCEPTEE(202)──▶ ENVOYEE ──CONFIRMATION_REUSSIE(200)──▶ VERIFIEE
 *      │                                   │  └──CONFIRMATION_REFUSEE(400)──▶ JETON_INVALIDE ──DEMANDE_ACCEPTEE──▶ ENVOYEE
 *      └──DEMANDE_ECHOUEE(503 courriel_indisponible)──▶ ECHEC_ENVOI ──DEMANDE_ACCEPTEE──▶ ENVOYEE
 * VERIFIEE ──ADRESSE_CHANGEE──▶ ENVOYEE (le serveur envoie un courriel à la nouvelle adresse)
 */
export type EtatVerification =
  | { readonly etat: "NON_DEMANDEE" }
  | { readonly etat: "ENVOYEE" }
  | { readonly etat: "ECHEC_ENVOI" }
  | { readonly etat: "VERIFIEE" }
  | { readonly etat: "JETON_INVALIDE" };

export type EvenementVerification =
  /** GET /comptes/verification-email → statut serveur (resynchronisation). */
  | { readonly type: "STATUT_LU"; readonly statut: StatutVerificationEmail }
  /** POST /comptes/verification-email → 202. */
  | { readonly type: "DEMANDE_ACCEPTEE"; readonly statut: "VERIFICATION_TOKEN_CREATED" | "EMAIL_VERIFIED" }
  /** POST /comptes/verification-email → 503 courriel_indisponible. */
  | { readonly type: "DEMANDE_ECHOUEE" }
  | { readonly type: "CONFIRMATION_REUSSIE" }
  /** 400 jeton_invalide_ou_expire (réponse unique : inconnu, expiré, déjà utilisé, adresse changée). */
  | { readonly type: "CONFIRMATION_REFUSEE" }
  | { readonly type: "ADRESSE_CHANGEE" };

export const ETAT_VERIFICATION_INITIAL: EtatVerification = { etat: "NON_DEMANDEE" };

const depuisStatut = (s: StatutVerificationEmail): EtatVerification =>
  s === "EMAIL_VERIFIED" ? { etat: "VERIFIEE" } : s === "VERIFICATION_TOKEN_CREATED" ? { etat: "ENVOYEE" } : { etat: "NON_DEMANDEE" };

function transitionVerifOuNull(e: EtatVerification, ev: EvenementVerification): EtatVerification | null {
  switch (ev.type) {
    case "STATUT_LU":
      return depuisStatut(ev.statut);
    case "DEMANDE_ACCEPTEE":
      if (e.etat === "VERIFIEE") return null;
      return ev.statut === "EMAIL_VERIFIED" ? { etat: "VERIFIEE" } : { etat: "ENVOYEE" };
    case "DEMANDE_ECHOUEE":
      return e.etat === "VERIFIEE" ? null : { etat: "ECHEC_ENVOI" };
    case "CONFIRMATION_REUSSIE":
      // Le lien peut être ouvert sur un autre appareil : toute situation non vérifiée l'accepte.
      return e.etat === "VERIFIEE" ? null : { etat: "VERIFIEE" };
    case "CONFIRMATION_REFUSEE":
      return e.etat === "VERIFIEE" ? null : { etat: "JETON_INVALIDE" };
    case "ADRESSE_CHANGEE":
      return { etat: "ENVOYEE" };
  }
}

export function transitionVerification(etat: EtatVerification, evenement: EvenementVerification): EtatVerification {
  const r = transitionVerifOuNull(etat, evenement);
  if (r === null) throw new TransitionRefusee("verification", etat.etat, evenement.type);
  return r;
}

export function peutTransitionnerVerification(etat: EtatVerification, evenement: EvenementVerification): boolean {
  return transitionVerifOuNull(etat, evenement) !== null;
}

/** Bouton « renvoyer le courriel » (data-testid `verif-renvoyer`). */
export function peutRenvoyerCourriel(etat: EtatVerification): boolean {
  return etat.etat !== "VERIFIEE";
}

// ============================================================================================
// 3. Séance élève Mika (jeton élève + séance serveur, décision D15)
// ============================================================================================
/**
 * AUCUNE ──JETON_OBTENU──▶ JETON_PRET ──SEANCE_CREEE(POST /session/nouvelle 201)──▶ OUVERTE
 * OUVERTE ──ERREUR(401 session_inactivite_5min)──▶ EXPIREE(inactivite) ──SEANCE_CREEE──▶ OUVERTE
 * OUVERTE ──ERREUR(401 jeton_expire) | TEMPS ≥ expireA──▶ EXPIREE(jeton_expire) ──JETON_OBTENU (1 seule fois)──▶ JETON_PRET
 *   (si le jeton ré-émis expire à son tour avant tout succès : EXPIREE(reemissionTentee) ⇒ reconnexion)
 * * ──ERREUR(401 jeton_revoque)──▶ REVOQUEE (retour au choix d'enfant) ; OUVERTE ──ERREUR(404 session_inconnue)──▶ JETON_PRET
 * * ──FERMER──▶ AUCUNE
 */
export type RaisonExpirationSeance = "inactivite" | "jeton_expire";

/**
 * `reemis` : le jeton courant provient d'une ré-émission suite à `jeton_expire` et n'a pas encore
 * servi avec succès. Un nouveau `jeton_expire` dans cette situation ⇒ `reemissionTentee` ⇒ reconnexion.
 */
export type EtatSeance =
  | { readonly etat: "AUCUNE" }
  | { readonly etat: "JETON_PRET"; readonly pseudo: string; readonly expireA: number; readonly reemis: boolean }
  | { readonly etat: "OUVERTE"; readonly pseudo: string; readonly expireA: number; readonly reemis: boolean; readonly sessionId: string }
  | {
    readonly etat: "EXPIREE"; readonly pseudo: string; readonly expireA: number;
    readonly raison: RaisonExpirationSeance; readonly reemissionTentee: boolean;
  }
  | { readonly etat: "REVOQUEE"; readonly pseudo: string };

export type EvenementSeance =
  /** POST /auth/eleve/jeton → 200 ; `expireA` = maintenant + expires_in (calculé par l'appelant). */
  | { readonly type: "JETON_OBTENU"; readonly pseudo: string; readonly expireA: number }
  /** POST /session/nouvelle → 201. */
  | { readonly type: "SEANCE_CREEE"; readonly sessionId: string }
  /** Appel d'apprentissage réussi (heartbeat, save-state, reconnect, exercice, tuteur…). */
  | { readonly type: "ACTIVITE" }
  /** Erreur HTTP sur une route d'apprentissage. */
  | { readonly type: "ERREUR"; readonly status: number; readonly code: string | null }
  /** Horloge : l'appelant fournit l'instant (la machine reste pure). */
  | { readonly type: "TEMPS"; readonly maintenant: number }
  | { readonly type: "FERMER" };

export const ETAT_SEANCE_INITIAL: EtatSeance = { etat: "AUCUNE" };

function transitionSeanceOuNull(e: EtatSeance, ev: EvenementSeance): EtatSeance | null {
  switch (ev.type) {
    case "FERMER":
      return { etat: "AUCUNE" };
    case "JETON_OBTENU":
      if (e.etat === "AUCUNE" || e.etat === "REVOQUEE") {
        return { etat: "JETON_PRET", pseudo: ev.pseudo, expireA: ev.expireA, reemis: false };
      }
      if (ev.pseudo !== e.pseudo) return null; // changer d'enfant : FERMER d'abord
      if (e.etat === "EXPIREE") {
        if (e.raison === "jeton_expire" && e.reemissionTentee) return null; // une seule ré-émission
        return { etat: "JETON_PRET", pseudo: ev.pseudo, expireA: ev.expireA, reemis: e.raison === "jeton_expire" };
      }
      return { ...e, expireA: ev.expireA }; // renouvellement anticipé (expires_in − 5 min)
    case "SEANCE_CREEE":
      if (e.etat === "JETON_PRET") return { ...e, etat: "OUVERTE", sessionId: ev.sessionId };
      if (e.etat === "EXPIREE" && e.raison === "inactivite") {
        return { etat: "OUVERTE", pseudo: e.pseudo, expireA: e.expireA, reemis: false, sessionId: ev.sessionId };
      }
      return null;
    case "ACTIVITE":
      return e.etat === "OUVERTE" ? { ...e, reemis: false } : null;
    case "TEMPS":
      if (e.etat === "AUCUNE") return null;
      if ((e.etat === "OUVERTE" || e.etat === "JETON_PRET") && ev.maintenant >= e.expireA) {
        return { etat: "EXPIREE", pseudo: e.pseudo, expireA: e.expireA, raison: "jeton_expire", reemissionTentee: e.reemis };
      }
      return e;
    case "ERREUR": {
      if (e.etat === "AUCUNE") return null;
      if (ev.status === 401 && ev.code === "jeton_revoque") return { etat: "REVOQUEE", pseudo: e.pseudo };
      if (e.etat === "REVOQUEE") return null;
      if (ev.status === 401 && ev.code === "jeton_expire") {
        const tente = e.etat === "EXPIREE" ? e.raison === "jeton_expire" : e.reemis;
        return { etat: "EXPIREE", pseudo: e.pseudo, expireA: e.expireA, raison: "jeton_expire", reemissionTentee: tente };
      }
      if (e.etat !== "OUVERTE") return null;
      if (ev.status === 401 && ev.code === "session_inactivite_5min") {
        return { etat: "EXPIREE", pseudo: e.pseudo, expireA: e.expireA, raison: "inactivite", reemissionTentee: false };
      }
      if (ev.status === 404 && ev.code === "session_inconnue") {
        return { etat: "JETON_PRET", pseudo: e.pseudo, expireA: e.expireA, reemis: e.reemis };
      }
      return e; // autres erreurs (403, 409, 413, 422, 429…) : la séance ne change pas
    }
  }
}

export function transitionSeance(etat: EtatSeance, evenement: EvenementSeance): EtatSeance {
  const r = transitionSeanceOuNull(etat, evenement);
  if (r === null) throw new TransitionRefusee("seance", etat.etat, evenement.type);
  return r;
}

export function peutTransitionnerSeance(etat: EtatSeance, evenement: EvenementSeance): boolean {
  return transitionSeanceOuNull(etat, evenement) !== null;
}

/** Jeton prêt sans séance, ou séance expirée par inactivité : appeler POST /session/nouvelle. */
export function doitCreerNouvelleSeance(etat: EtatSeance): boolean {
  return etat.etat === "JETON_PRET" || (etat.etat === "EXPIREE" && etat.raison === "inactivite");
}

/** Jeton élève expiré, ré-émission encore permise : appeler POST /auth/eleve/jeton (une fois). */
export function doitReemettreJeton(etat: EtatSeance): boolean {
  return etat.etat === "EXPIREE" && etat.raison === "jeton_expire" && !etat.reemissionTentee;
}

/** EXPIREE sur jeton_expire après une ré-émission déjà tentée : retour à la connexion. */
export function doitSeReconnecter(etat: EtatSeance): boolean {
  return etat.etat === "EXPIREE" && etat.raison === "jeton_expire" && etat.reemissionTentee;
}
