// Parcours 3 — Jeton élève → séance (POST /session/nouvelle) → exercice → tuteur Mika.

import { transitionSeance } from "../auth-state.ts";
import type { EtatSeance } from "../auth-state.ts";
import { ApiError, MikaClient, nouveauRequeteId } from "../client.ts";
import type { ReponseSoumission, ReponseTutorat } from "../types.ts";

export async function ouvrirSeance(client: MikaClient, pseudo: string): Promise<EtatSeance> {
  const jeton = await client.obtenirJetonEleve(pseudo); // émis avec le jeton de compte, gardé en mémoire
  let etat = transitionSeance({ etat: "AUCUNE" }, { type: "JETON_OBTENU", pseudo, expireA: jeton.expireA });
  const s = await client.nouvelleSession({ user_id: pseudo }); // jamais de session_id généré côté front
  etat = transitionSeance(etat, { type: "SEANCE_CREEE", sessionId: s.session_id });
  return etat;
}

/** À appeler toutes les 60 s ; renvoie le nouvel état (inactivité, révocation…). */
export async function battement(client: MikaClient, etat: EtatSeance): Promise<EtatSeance> {
  if (etat.etat !== "OUVERTE") return etat;
  try {
    await client.heartbeat({ session_id: etat.sessionId, user_id: etat.pseudo });
    return transitionSeance(etat, { type: "ACTIVITE" });
  } catch (e) {
    if (e instanceof ApiError) return transitionSeance(etat, { type: "ERREUR", status: e.status, code: e.code });
    throw e;
  }
}

export async function repondreExercice(client: MikaClient, pseudo: string, exerciceId: string,
                                       reponse: string): Promise<ReponseSoumission> {
  const r = await client.soumettreExercice({ exercice_id: exerciceId, student_pseudo_id: pseudo, reponse });
  // `progression` (session 5) est facultatif : un serveur en mode legacy l'omet ou envoie null.
  if (r.progression) {
    // ex. r.progression.niveau === "FRAGILE" && r.progression.prochaine_action === "guidage_pas_a_pas"
  }
  return r;
}

/**
 * Action du tuteur avec idempotence : un `requete_id` par action, conservé pour les réessais
 * réseau ; 409 `version_perimee` ⇒ relire le tutorat puis NOUVEAU requete_id.
 */
export async function demanderAide(client: MikaClient, pseudo: string, t: ReponseTutorat): Promise<ReponseTutorat> {
  const requeteId = nouveauRequeteId();
  try {
    return await client.tutoratHelp({ student_pseudo_id: pseudo, tutorat_id: t.tutorat_id, version: t.version, requete_id: requeteId });
  } catch (e) {
    if (e instanceof ApiError && e.code === "version_perimee") {
      const vue = await client.tutoratEtat(t.tutorat_id, pseudo);
      return client.tutoratHelp({ student_pseudo_id: pseudo, tutorat_id: vue.tutorat_id, version: vue.version, requete_id: nouveauRequeteId() });
    }
    throw e; // 404 exercice_indisponible / tutorat_inconnu, 409 tutorat_termine… : suivre `etat`
  }
}

export async function demarrerTutorat(client: MikaClient, pseudo: string, exerciceId: string): Promise<ReponseTutorat | null> {
  try {
    return await client.tutoratStart({ student_pseudo_id: pseudo, exercice_id: exerciceId, requete_id: nouveauRequeteId() });
  } catch (e) {
    if (e instanceof ApiError && e.code === "exercice_indisponible") return null; // aucun contenu prouvé
    throw e;
  }
}
