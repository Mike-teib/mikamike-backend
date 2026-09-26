// validators.ts — Validation runtime légère (sans dépendance) des réponses du contrat.
//
// Chaque validateur est typé `Validateur<T>` avec T le type exact de types.ts : `objet<T>()`
// exige un validateur pour CHAQUE clé de T (vérifié par tsc). En mode strict, une clé inconnue
// est refusée (détection de dérive du contrat) ; en mode souple (défaut du client), les clés
// supplémentaires sont tolérées pour la compatibilité ascendante.

import {
  ACTIONS_TUTEUR, CODES_ERREUR, CONTRACT_VERSION_TUTORAT, ETATS_MAITRISE, MOTEURS_PROGRESSION,
  NIVEAUX_PROGRESSION, PROCHAINES_ACTIONS, RELATIONS, ROLES, STATUTS_ABONNEMENT, STATUTS_VERIFICATION_EMAIL,
} from "./types.ts";
import type {
  Compte, DashboardParent, DetailVersionPerimee, ErreurValidation, EtatTutoratPublic, EtatVerificationEmail,
  ExportCompte, ExportRgpdEleve, InvitationExport, LienExport, ProchaineEtape, Progression, RappelMemoireExport,
  Remediation, ReponseAcceptation, ReponseConfirmationEmail, ReponseDemandeVerification, ReponseEffacementRgpd,
  ReponseHeartbeat, ReponseInvitation, ReponseJetonCompte, ReponseJetonEleve, ReponseMika, ReponseNouvelleSeance,
  ReponseReconnexion, ReponseSauvegardeEtat, ReponseSoumission, ReponseSuppressionCompte, ReponseTutorat,
  RequeteTutoratExport, SeanceExport, StatCompetence, StatistiquesParent, TentativeExport, TutoratExport, VueTutorat,
} from "./types.ts";

export class ErreurContrat extends Error {
  readonly chemin: string;

  constructor(chemin: string, message: string) {
    super(`${chemin || "$"} : ${message}`);
    this.name = "ErreurContrat";
    this.chemin = chemin || "$";
  }
}

export interface Contexte {
  readonly strict: boolean;
}

export type Validateur<T> = ((valeur: unknown, chemin: string, ctx: Contexte) => T) & { readonly optionnel?: true };

const decrire = (v: unknown): string =>
  v === null ? "null" : Array.isArray(v) ? "tableau" : typeof v === "string" ? JSON.stringify(v.slice(0, 40)) : typeof v;

export const chaine: Validateur<string> = (v, chemin) => {
  if (typeof v !== "string") throw new ErreurContrat(chemin, `chaîne attendue, reçu ${decrire(v)}`);
  return v;
};

export const entier: Validateur<number> = (v, chemin) => {
  if (typeof v !== "number" || !Number.isInteger(v)) throw new ErreurContrat(chemin, `entier attendu, reçu ${decrire(v)}`);
  return v;
};

export const nombre: Validateur<number> = (v, chemin) => {
  if (typeof v !== "number" || !Number.isFinite(v)) throw new ErreurContrat(chemin, `nombre attendu, reçu ${decrire(v)}`);
  return v;
};

export const booleen: Validateur<boolean> = (v, chemin) => {
  if (typeof v !== "boolean") throw new ErreurContrat(chemin, `booléen attendu, reçu ${decrire(v)}`);
  return v;
};

export function litteral<const T extends string | number | boolean>(attendu: T): Validateur<T> {
  return (v, chemin) => {
    if (v !== attendu) throw new ErreurContrat(chemin, `${JSON.stringify(attendu)} attendu, reçu ${decrire(v)}`);
    return attendu;
  };
}

export function parmi<const T extends string>(valeurs: readonly T[]): Validateur<T> {
  return (v, chemin) => {
    if (typeof v !== "string" || !(valeurs as readonly string[]).includes(v)) {
      throw new ErreurContrat(chemin, `une valeur parmi ${valeurs.join("|")} attendue, reçu ${decrire(v)}`);
    }
    return v as T;
  };
}

export function nullable<T>(interne: Validateur<T>): Validateur<T | null> {
  return (v, chemin, ctx) => (v === null ? null : interne(v, chemin, ctx));
}

/** Clé facultative : absente (ou `undefined`) ⇒ omise du résultat. */
export function optionnel<T>(interne: Validateur<T>): Validateur<T | undefined> {
  const f = (v: unknown, chemin: string, ctx: Contexte): T | undefined =>
    v === undefined ? undefined : interne(v, chemin, ctx);
  return Object.assign(f, { optionnel: true as const });
}

export function tableau<T>(element: Validateur<T>): Validateur<readonly T[]> {
  return (v, chemin, ctx) => {
    if (!Array.isArray(v)) throw new ErreurContrat(chemin, `tableau attendu, reçu ${decrire(v)}`);
    return v.map((x, i) => element(x, `${chemin}[${i}]`, ctx));
  };
}

const estObjet = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

export function dictionnaire<T>(valeur: Validateur<T>): Validateur<Readonly<Record<string, T>>> {
  return (v, chemin, ctx) => {
    if (!estObjet(v)) throw new ErreurContrat(chemin, `objet attendu, reçu ${decrire(v)}`);
    const sortie: Record<string, T> = {};
    for (const [k, x] of Object.entries(v)) sortie[k] = valeur(x, `${chemin}.${k}`, ctx);
    return sortie;
  };
}

/** Objet JSON de forme libre (non contractuelle). */
export const objetLibre: Validateur<Readonly<Record<string, unknown>>> = (v, chemin) => {
  if (!estObjet(v)) throw new ErreurContrat(chemin, `objet attendu, reçu ${decrire(v)}`);
  return v;
};

export type Forme<T> = { readonly [K in keyof T]-?: Validateur<T[K]> };

/**
 * Objet à clés connues. `ferme: true` refuse toute clé inconnue quel que soit le mode (schéma
 * fermé côté serveur, ex. tableau de bord parent) ; sinon seulement en mode strict.
 */
export function objet<T extends object>(forme: Forme<T>, options: { readonly ferme?: boolean } = {}): Validateur<T> {
  const cles = Object.keys(forme) as (keyof T & string)[];
  return (v, chemin, ctx) => {
    if (!estObjet(v)) throw new ErreurContrat(chemin, `objet attendu, reçu ${decrire(v)}`);
    if (options.ferme === true || ctx.strict) {
      for (const k of Object.keys(v)) {
        if (!(k in forme)) throw new ErreurContrat(`${chemin}.${k}`, "clé inconnue du contrat");
      }
    }
    const sortie: Partial<Record<keyof T, unknown>> = {};
    for (const k of cles) {
      const val = forme[k];
      if (!(k in v) && val.optionnel !== true) throw new ErreurContrat(`${chemin}.${k}`, "clé obligatoire absente");
      const r = val(v[k], `${chemin}.${k}`, ctx);
      if (r !== undefined) sortie[k] = r;
    }
    return sortie as T;
  };
}

export function valider<T>(validateur: Validateur<T>, valeur: unknown, options: { readonly strict?: boolean } = {}): T {
  return validateur(valeur, "$", { strict: options.strict === true });
}

// --------------------------------------------------------------------------------------------
// Validateurs du contrat
// --------------------------------------------------------------------------------------------
const date = nullable(chaine); // ISO 8601 ; null possible quand la colonne est vide

export const vCompte = objet<Compte>({
  id: entier, email: chaine, prenom: nullable(chaine), role: parmi(ROLES),
  statut_abonnement: parmi(STATUTS_ABONNEMENT), email_verifie: booleen,
});
export const vReponseJetonCompte = objet<ReponseJetonCompte>({ token: chaine, compte: vCompte });
export const vEtatVerificationEmail = objet<EtatVerificationEmail>({
  statut: parmi(STATUTS_VERIFICATION_EMAIL), email_verifie: booleen,
});
export const vReponseDemandeVerification = objet<ReponseDemandeVerification>({
  statut: parmi(["VERIFICATION_TOKEN_CREATED", "EMAIL_VERIFIED"] as const),
});
export const vReponseConfirmationEmail = objet<ReponseConfirmationEmail>({ statut: litteral("EMAIL_VERIFIED") });
export const vReponseSuppressionCompte = objet<ReponseSuppressionCompte>({
  statut: litteral("compte_supprime"), liens_supprimes: entier,
});
export const vExportCompte = objet<ExportCompte>({
  contexte_rgpd: chaine,
  compte: objet<ExportCompte["compte"]>({
    id: entier, email: chaine, prenom: nullable(chaine), role: parmi(ROLES), actif: booleen,
    cree_le: date, derniere_connexion: date,
  }),
  verification_email: vEtatVerificationEmail,
  abonnement: objet<ExportCompte["abonnement"]>({ statut: parmi(STATUTS_ABONNEMENT) }),
  liens_eleves: tableau(objet<LienExport>({ relation: parmi(RELATIONS), cree_le: date })),
  invitations_acceptees: entier,
});

export const vReponseJetonEleve = objet<ReponseJetonEleve>({
  token: chaine, token_type: litteral("Bearer"), typ: litteral("mika-eleve"), expires_in: entier,
});

export const vReponseInvitation = objet<ReponseInvitation>({
  code: chaine, relation: parmi(RELATIONS), expires_in: entier, expire_le: chaine, usage_unique: litteral(true),
});
export const vReponseAcceptation = objet<ReponseAcceptation>({
  statut: litteral("lien_cree"), relation: parmi(RELATIONS), student_pseudo_id: chaine,
});

export const vReponseNouvelleSeance = objet<ReponseNouvelleSeance>({
  statut: litteral("session_creee"), session_id: chaine, is_active: booleen,
});
export const vReponseHeartbeat = objet<ReponseHeartbeat>({
  statut: parmi(["heartbeat_ok", "session_creee"] as const), session_id: chaine, is_active: booleen,
});
export const vReponseSauvegardeEtat = objet<ReponseSauvegardeEtat>({
  statut: litteral("etat_sauvegarde"), session_id: chaine,
});
export const vReponseReconnexion = objet<ReponseReconnexion>({
  statut: litteral("reconnexion_reussie"), session_id: chaine, session_state: objetLibre,
  duree_reconnexion_ms: nombre, reconnexion_inf_2s: booleen,
});

export const vProgression = objet<Progression>({
  moteur: parmi(MOTEURS_PROGRESSION), niveau: parmi(NIVEAUX_PROGRESSION),
  prochaine_action: parmi(PROCHAINES_ACTIONS), observations: entier, raisons: tableau(chaine),
});
export const vRemediation = objet<Remediation>({
  explication_concept: chaine, exercice_prerequis: chaine, competence_lacune: nullable(chaine),
});
export const vReponseSoumission = objet<ReponseSoumission>({
  est_correct: booleen, etat_maitrise: parmi(ETATS_MAITRISE), message: nullable(chaine),
  remediation: nullable(vRemediation), progression: optionnel(nullable(vProgression)),
});
export const vProchaineEtape = objet<ProchaineEtape>({
  exercice_id: chaine, niveau: chaine, competence: chaine, consigne: chaine,
});

export const vEtatTutoratPublic = objet<EtatTutoratPublic>({
  tentatives: entier, indices_donnes: entier, questions_posees: entier, methodes_donnees: entier,
  niveau_aide: entier, avec_aide: booleen, resolu: booleen, termine: booleen, attend_comprehension: booleen,
  comprehension_verifiee: nullable(booleen), niveau_estime: parmi(ETATS_MAITRISE),
  prerequis_manquant: nullable(chaine), messages: tableau(chaine),
});
export const vReponseMika = objet<ReponseMika>({
  action: parmi(ACTIONS_TUTEUR), message: chaine, difficulte_proposee: entier,
  exercice_id: nullable(chaine), notion_cible: nullable(chaine),
});
const formeVue: Forme<VueTutorat> = {
  contract_version: litteral(CONTRACT_VERSION_TUTORAT), tutorat_id: chaine, version: entier, exercice_id: chaine,
  derniere_action: parmi(ACTIONS_TUTEUR), etat: vEtatTutoratPublic,
};
export const vVueTutorat = objet<VueTutorat>(formeVue);
export const vReponseTutorat = objet<ReponseTutorat>({ ...formeVue, reponse: vReponseMika, rejeu: booleen });

export const vStatCompetence = objet<StatCompetence>(
  { tentatives: entier, reussites: entier, etat: parmi(ETATS_MAITRISE) }, { ferme: true });
export const vStatistiquesParent = objet<StatistiquesParent>({
  exercices_tentes: entier, exercices_reussis: entier, taux_reussite: nombre,
  competences: dictionnaire(vStatCompetence), niveau_actuel: chaine,
}, { ferme: true });
export const vDashboardParent = objet<DashboardParent>(
  { pseudo_id: chaine, statistiques_pedagogiques: vStatistiquesParent }, { ferme: true });

export const vExportRgpdEleve = objet<ExportRgpdEleve>({
  contexte_rgpd: chaine, student_pseudo_id: chaine, anonymisation: chaine, total_tentatives: entier,
  total_competences_suivies: entier, etats_maitrise: dictionnaire(parmi(ETATS_MAITRISE)),
  historique_tentatives: tableau(objet<TentativeExport>({
    id: entier, exercice_id: chaine, matiere: chaine, niveau: chaine, competence: chaine, est_correct: booleen,
    avec_aide: booleen, date_heure: date,
  })),
  rappels_memoire: tableau(objet<RappelMemoireExport>({
    notion_id: chaine, statut_fragilite: booleen, repetition_count: entier, intervalle_jours: entier,
    prochain_rappel_date: date,
  })),
  sessions: tableau(objet<SeanceExport>({
    session_id: chaine, is_active: booleen, created_at: date, last_activity_ts: date, etat_seance: objetLibre,
  })),
  tutorats_mika: tableau(objet<TutoratExport>({
    tutorat_id: chaine, exercice_id: chaine, derniere_action: parmi(ACTIONS_TUTEUR), termine: booleen,
    cree_le: date, maj_le: date, etat: objetLibre,
  })),
  requetes_tutorat_mika: tableau(objet<RequeteTutoratExport>({
    tutorat_id: chaine, requete_id: chaine, cree_le: date, reponse: objetLibre,
  })),
  liens_comptes: tableau(objet<LienExport>({ relation: parmi(RELATIONS), cree_le: date })),
  invitations_liens: tableau(objet<InvitationExport>({
    relation: parmi(RELATIONS), emis_par: chaine, cree_le: date, expire_le: date, utilisee: booleen,
  })),
});
export const vReponseEffacementRgpd = objet<ReponseEffacementRgpd>({
  statut: litteral("effacement_effectue"), message: chaine, student_pseudo_id: chaine,
  tentatives_supprimees: entier, etats_supprimes: entier, rappels_memoire_supprimes: entier,
  sessions_supprimees: entier, tutorats_supprimes: entier, requetes_tutorat_supprimees: entier,
  liens_compte_supprimes: entier, invitations_supprimees: entier,
});

// Erreurs ------------------------------------------------------------------------------------
export const vCodeErreur = parmi(CODES_ERREUR);
export const vDetailVersionPerimee = objet<DetailVersionPerimee>({
  code: litteral("version_perimee"), version_courante: entier,
});
export const vErreurValidation = objet<ErreurValidation>({
  loc: tableau<string | number>((v, chemin) => {
    if (typeof v === "string" || (typeof v === "number" && Number.isInteger(v))) return v;
    throw new ErreurContrat(chemin, "chaîne ou entier attendu");
  }),
  msg: chaine, type: chaine,
  input: optionnel<unknown>((v) => v), ctx: optionnel<unknown>((v) => v), url: optionnel(chaine),
});
