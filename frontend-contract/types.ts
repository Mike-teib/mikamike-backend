// types.ts — Types exacts du contrat front MikaMike (préfixe /api/v1).
//
// Source de vérité : contrat_front/contrat.json (46 appels réels enregistrés) + code des routes
// (paiement_comptes/router_comptes.py, app/api/v1/{liens,auth,session,tutorat,mikamike,rgpd}).
// Syntaxe EFFAÇABLE uniquement (ni enum, ni namespace, ni propriété de paramètre) : Node exécute
// ce fichier nativement (type stripping) et le front peut l'importer tel quel.

// --------------------------------------------------------------------------------------------
// Énumérations (unions littérales + tableaux « as const » pour les validateurs runtime)
// --------------------------------------------------------------------------------------------
export const ROLES = ["parent", "eleve"] as const;
/** Rôle d'un compte. `admin` existe dans le modèle mais aucune route ne l'honore. */
export type Role = (typeof ROLES)[number];

export const RELATIONS = ["parent", "eleve"] as const;
export type Relation = (typeof RELATIONS)[number];

export const STATUTS_ABONNEMENT = ["aucun", "essai", "actif", "impaye", "annule", "expire"] as const;
export type StatutAbonnement = (typeof STATUTS_ABONNEMENT)[number];

export const STATUTS_VERIFICATION_EMAIL = ["EMAIL_UNVERIFIED", "VERIFICATION_TOKEN_CREATED", "EMAIL_VERIFIED"] as const;
export type StatutVerificationEmail = (typeof STATUTS_VERIFICATION_EMAIL)[number];

/** Les 7 états de maîtrise historiques du Learning Engine (LE-03), champ `etat_maitrise`. */
export const ETATS_MAITRISE = [
  "INCONNU", "FRAGILE", "EN_COURS", "ACQUIS_ASSISTE", "ACQUIS_AUTONOME", "A_REVOIR", "MAITRISE",
] as const;
export type EtatMaitrise = (typeof ETATS_MAITRISE)[number];

/** Niveaux du moteur de progression sur historique (session 5), champ `progression.niveau`. */
export const NIVEAUX_PROGRESSION = ["NON_EVALUEE", "NON_ACQUISE", "FRAGILE", "EN_COURS", "MAITRISEE"] as const;
export type NiveauProgression = (typeof NIVEAUX_PROGRESSION)[number];

/** `progression.prochaine_action` (app/curriculum/pedagogie/progression.py, PROCHAINE_ACTION). */
export const PROCHAINES_ACTIONS = [
  "observer_encore", "reprendre_prerequis", "guidage_pas_a_pas", "entrainement_autonome", "retest_espace",
] as const;
export type ProchaineAction = (typeof PROCHAINES_ACTIONS)[number];

export const MOTEURS_PROGRESSION = ["historique"] as const;
export type MoteurProgression = (typeof MOTEURS_PROGRESSION)[number];

/** Actions du tuteur Mika (contrat `mika-tutorat/1`). */
export const ACTIONS_TUTEUR = [
  "PRESENTER_EXERCICE", "REMEDIER_PREREQUIS", "IDENTIFIER_BLOCAGE", "QUESTION_INTERMEDIAIRE",
  "DONNER_INDICE", "LAISSER_REESSAYER", "AUTRE_METHODE", "VERIFIER_COMPREHENSION", "CONSOLIDATION",
  "DEMANDER_REFORMULATION", "CORRECTION_COMMENTEE", "REVUE_HUMAINE",
] as const;
export type ActionTuteur = (typeof ACTIONS_TUTEUR)[number];

export const CONTRACT_VERSION_TUTORAT = "mika-tutorat/1" as const;

// --------------------------------------------------------------------------------------------
// Codes d'erreur (`detail` des réponses d'erreur). Relevés dans le code, pas seulement dans
// contrat.json. Le front ne doit jamais afficher ces codes bruts : les traduire.
// --------------------------------------------------------------------------------------------
export const CODES_ERREUR_AUTH = [
  // Routes « compte » (paiement_comptes/router_comptes.py::compte_courant)
  "token_absent", "token_invalide", "compte_inconnu", "jeton_revoque",
  // Routes protégées par app/core/auth.py (jeton élève ou compte)
  "jeton_requis", "jeton_invalide", "jeton_expire", "jeton_compte_requis",
  // Séance : inactivité > 5 min (401)
  "session_inactivite_5min",
] as const;
export type CodeErreurAuth = (typeof CODES_ERREUR_AUTH)[number];

export const CODES_ERREUR = [
  ...CODES_ERREUR_AUTH,
  // 401 (connexion)
  "identifiants_invalides",
  // 400
  "email_deja_utilise", "email_invalide", "mot_de_passe_trop_court", "email_indisponible", "email_identique",
  "jeton_invalide_ou_expire", "invitation_invalide",
  // 403
  "acces_refuse", "email_non_verifie", "mot_de_passe_incorrect", "session_non_autorisee",
  // 404
  "session_inconnue", "exercice_inconnu", "exercice_indisponible", "tutorat_inconnu",
  "aucune_donnee_trouvee_pour_cet_identifiant", "aucune_donnee_a_effacer",
  // 409
  "abonnement_en_cours", "trop_d_invitations_actives", "deja_lie", "version_perimee", "tutorat_termine",
  "comprehension_attendue", "comprehension_non_demandee", "comprehension_non_verifiable", "contenu_retire",
  "requete_id_reutilise_avec_un_autre_contenu", "conflit_de_creation",
  // 413
  "etat_session_trop_volumineux",
  // 429
  "trop_de_tentatives",
  // 500 (configuration / état serveur)
  "auth_mal_configuree", "limitation_mal_configuree", "auth_non_configuree", "jwt_indisponible",
  "etat_tutorat_illisible", "invariant_avec_aide_viole", "generation_session_impossible",
  "invitation_mal_configuree",
  // 503 (nouveau, session 5) : le fournisseur de courriel a refusé le renvoi de vérification
  "courriel_indisponible",
] as const;
export type CodeErreur = (typeof CODES_ERREUR)[number];

/** Élément d'une erreur 422 FastAPI/Pydantic (`detail` est alors un tableau). */
export interface ErreurValidation {
  readonly loc: readonly (string | number)[];
  readonly msg: string;
  readonly type: string;
  readonly input?: unknown;
  readonly ctx?: unknown;
  readonly url?: string;
}

/** 409 du verrou optimiste du tuteur : `detail` est un objet. */
export interface DetailVersionPerimee {
  readonly code: "version_perimee";
  readonly version_courante: number;
}

export type DetailErreur = CodeErreur | DetailVersionPerimee | readonly ErreurValidation[];

export interface ReponseErreur {
  readonly detail: DetailErreur;
}

// --------------------------------------------------------------------------------------------
// Comptes (/comptes/*)
// --------------------------------------------------------------------------------------------
export interface Compte {
  readonly id: number;
  readonly email: string;
  readonly prenom: string | null;
  readonly role: Role;
  readonly statut_abonnement: StatutAbonnement;
  readonly email_verifie: boolean;
}

export interface InscriptionCorps {
  readonly email: string;
  /** 8 à 200 caractères. */
  readonly mot_de_passe: string;
  readonly prenom?: string | null;
  /** Défaut serveur `parent` ; toute autre valeur que parent|eleve est ramenée à `parent`. */
  readonly role?: Role;
}

export interface ConnexionCorps {
  readonly email: string;
  readonly mot_de_passe: string;
}

/** Réponse d'inscription, connexion, changement de mot de passe ou d'adresse. */
export interface ReponseJetonCompte {
  readonly token: string;
  readonly compte: Compte;
}

export interface EtatVerificationEmail {
  readonly statut: StatutVerificationEmail;
  readonly email_verifie: boolean;
}

/** 202 (renvoi du courriel) ; `EMAIL_VERIFIED` si l'adresse était déjà vérifiée. */
export interface ReponseDemandeVerification {
  readonly statut: "VERIFICATION_TOKEN_CREATED" | "EMAIL_VERIFIED";
}

export interface ConfirmationEmailCorps {
  /** Jeton reçu PAR COURRIEL uniquement (jamais renvoyé par HTTP). 1 à 128 caractères. */
  readonly jeton: string;
}

export interface ReponseConfirmationEmail {
  readonly statut: "EMAIL_VERIFIED";
}

export interface ChangementMotDePasseCorps {
  readonly ancien: string;
  /** 8 à 200 caractères. */
  readonly nouveau: string;
}

export interface ChangementEmailCorps {
  readonly nouvel_email: string;
  readonly mot_de_passe: string;
}

export interface SuppressionCompteCorps {
  readonly mot_de_passe: string;
  /** Le booléen JSON `true` est exigé (case cochée explicitement). */
  readonly confirmation: true;
}

export interface ReponseSuppressionCompte {
  readonly statut: "compte_supprime";
  readonly liens_supprimes: number;
}

export interface ExportCompte {
  readonly contexte_rgpd: string;
  readonly compte: {
    readonly id: number;
    readonly email: string;
    readonly prenom: string | null;
    readonly role: Role;
    readonly actif: boolean;
    readonly cree_le: string | null;
    readonly derniere_connexion: string | null;
  };
  readonly verification_email: EtatVerificationEmail;
  readonly abonnement: { readonly statut: StatutAbonnement };
  readonly liens_eleves: readonly { readonly relation: Relation; readonly cree_le: string | null }[];
  readonly invitations_acceptees: number;
}

// --------------------------------------------------------------------------------------------
// Jeton élève (/auth/eleve/jeton)
// --------------------------------------------------------------------------------------------
export interface JetonEleveCorps {
  readonly student_pseudo_id: string;
}

export interface ReponseJetonEleve {
  readonly token: string;
  readonly token_type: "Bearer";
  readonly typ: "mika-eleve";
  /** Durée de vie en secondes (7 200 par défaut, 43 200 max). */
  readonly expires_in: number;
}

// --------------------------------------------------------------------------------------------
// Liens parent ↔ élève par invitation (/liens/*, décision D8)
// --------------------------------------------------------------------------------------------
export interface InvitationCorps {
  readonly student_pseudo_id: string;
  readonly relation?: Relation;
}

export interface ReponseInvitation {
  /** Code `XXXX-XXXX-…` à afficher UNE fois ; ne jamais le stocker. */
  readonly code: string;
  readonly relation: Relation;
  readonly expires_in: number;
  /** ISO 8601 UTC suffixé `Z`. */
  readonly expire_le: string;
  readonly usage_unique: true;
}

export interface AcceptationCorps {
  /** Tolérant à la casse, aux espaces et aux tirets. 1 à 64 caractères. */
  readonly code: string;
  /** Le booléen JSON `true` est exigé (case « je suis le parent de cet enfant »). */
  readonly confirmation: true;
}

export interface ReponseAcceptation {
  readonly statut: "lien_cree";
  readonly relation: Relation;
  readonly student_pseudo_id: string;
}

// --------------------------------------------------------------------------------------------
// Séance élève (/session/*, décision D15)
// --------------------------------------------------------------------------------------------
export interface NouvelleSeanceCorps {
  readonly user_id: string;
}

export interface ReponseNouvelleSeance {
  readonly statut: "session_creee";
  /** Généré par le serveur (`s` + 48 hex). Ne jamais générer côté front. */
  readonly session_id: string;
  readonly is_active: boolean;
}

export interface SeanceCorps {
  readonly session_id: string;
  readonly user_id: string;
}

export interface SauvegardeEtatCorps extends SeanceCorps {
  readonly state_data: Readonly<Record<string, unknown>>;
}

export interface ReponseHeartbeat {
  /** `session_creee` uniquement en mode `off` (création implicite, interdite en production). */
  readonly statut: "heartbeat_ok" | "session_creee";
  readonly session_id: string;
  readonly is_active: boolean;
}

export interface ReponseSauvegardeEtat {
  readonly statut: "etat_sauvegarde";
  readonly session_id: string;
}

export interface ReponseReconnexion {
  readonly statut: "reconnexion_reussie";
  readonly session_id: string;
  readonly session_state: Readonly<Record<string, unknown>>;
  readonly duree_reconnexion_ms: number;
  readonly reconnexion_inf_2s: boolean;
}

// --------------------------------------------------------------------------------------------
// Exercices, progression, parcours
// --------------------------------------------------------------------------------------------
export interface SoumissionCorps {
  readonly exercice_id: string;
  readonly student_pseudo_id: string;
  /** ≤ 500 caractères. */
  readonly reponse: string;
  readonly avec_aide?: boolean;
}

export interface Remediation {
  readonly explication_concept: string;
  readonly exercice_prerequis: string;
  readonly competence_lacune: string | null;
}

/** Diagnostic du moteur sur historique (session 5). Absent / null en mode `legacy`. */
export interface Progression {
  readonly moteur: MoteurProgression;
  readonly niveau: NiveauProgression;
  readonly prochaine_action: ProchaineAction;
  readonly observations: number;
  /** Codes de règles (ex. `R1_observations_insuffisantes`) : libellés à traduire côté front. */
  readonly raisons: readonly string[];
}

export interface ReponseSoumission {
  readonly est_correct: boolean;
  readonly etat_maitrise: EtatMaitrise;
  readonly message: string | null;
  readonly remediation: Remediation | null;
  /** Nouveau champ (session 5), optionnel : un serveur plus ancien peut l'omettre. */
  readonly progression?: Progression | null;
}

export interface ProchaineEtape {
  readonly exercice_id: string;
  readonly niveau: string;
  readonly competence: string;
  readonly consigne: string;
}

// --------------------------------------------------------------------------------------------
// Tuteur Mika (/mika/session/*, contrat mika-tutorat/1)
// --------------------------------------------------------------------------------------------
export interface TutoratStartCorps {
  readonly student_pseudo_id: string;
  /** UUID v4 par action, conservé pour les réessais (idempotence). */
  readonly requete_id: string;
  readonly exercice_id: string;
}

export interface TutoratTransitionCorps {
  readonly student_pseudo_id: string;
  readonly requete_id: string;
  /** 32 hex. */
  readonly tutorat_id: string;
  /** Version de la dernière réponse reçue, [1, 10 000]. */
  readonly version: number;
}

export interface TutoratReponseCorps extends TutoratTransitionCorps {
  /** ≤ 500 caractères. */
  readonly reponse: string;
}

export interface EtatTutoratPublic {
  readonly tentatives: number;
  readonly indices_donnes: number;
  readonly questions_posees: number;
  readonly methodes_donnees: number;
  readonly niveau_aide: number;
  readonly avec_aide: boolean;
  readonly resolu: boolean;
  readonly termine: boolean;
  readonly attend_comprehension: boolean;
  readonly comprehension_verifiee: boolean | null;
  readonly niveau_estime: EtatMaitrise;
  readonly prerequis_manquant: string | null;
  readonly messages: readonly string[];
}

export interface ReponseMika {
  readonly action: ActionTuteur;
  readonly message: string;
  readonly difficulte_proposee: number;
  readonly exercice_id: string | null;
  readonly notion_cible: string | null;
}

/** GET /mika/session/{id} : sans `reponse` ni `rejeu`. */
export interface VueTutorat {
  readonly contract_version: typeof CONTRACT_VERSION_TUTORAT;
  readonly tutorat_id: string;
  readonly version: number;
  readonly exercice_id: string;
  readonly derniere_action: ActionTuteur;
  readonly etat: EtatTutoratPublic;
}

/** start / answer / help / comprehension. */
export interface ReponseTutorat extends VueTutorat {
  readonly reponse: ReponseMika;
  readonly rejeu: boolean;
}

// --------------------------------------------------------------------------------------------
// Tableau de bord parent (schéma FERMÉ côté serveur, minimisation)
// --------------------------------------------------------------------------------------------
export interface StatCompetence {
  readonly tentatives: number;
  readonly reussites: number;
  readonly etat: EtatMaitrise;
}

export interface StatistiquesParent {
  readonly exercices_tentes: number;
  readonly exercices_reussis: number;
  /** Entre 0 et 1, arrondi à 3 décimales. */
  readonly taux_reussite: number;
  readonly competences: Readonly<Record<string, StatCompetence>>;
  /** Libellé lisible : `demarrage` ou `n/m competences consolidees`. */
  readonly niveau_actuel: string;
}

export interface DashboardParent {
  readonly pseudo_id: string;
  readonly statistiques_pedagogiques: StatistiquesParent;
}

// --------------------------------------------------------------------------------------------
// RGPD élève (/rgpd/*)
// --------------------------------------------------------------------------------------------
export interface TentativeExport {
  readonly id: number;
  readonly exercice_id: string;
  readonly matiere: string;
  readonly niveau: string;
  readonly competence: string;
  readonly est_correct: boolean;
  readonly avec_aide: boolean;
  readonly date_heure: string | null;
}

export interface RappelMemoireExport {
  readonly notion_id: string;
  readonly statut_fragilite: boolean;
  readonly repetition_count: number;
  readonly intervalle_jours: number;
  readonly prochain_rappel_date: string | null;
}

export interface SeanceExport {
  readonly session_id: string;
  readonly is_active: boolean;
  readonly created_at: string | null;
  readonly last_activity_ts: string | null;
  /** Mémoire de séance telle que sauvegardée (`{"_brut_illisible": true}` si corrompue). */
  readonly etat_seance: Readonly<Record<string, unknown>>;
}

export interface TutoratExport {
  readonly tutorat_id: string;
  readonly exercice_id: string;
  readonly derniere_action: ActionTuteur;
  readonly termine: boolean;
  readonly cree_le: string | null;
  readonly maj_le: string | null;
  /** État INTERNE complet du tutorat (droit d'accès) : forme non contractuelle. */
  readonly etat: Readonly<Record<string, unknown>>;
}

export interface RequeteTutoratExport {
  readonly tutorat_id: string;
  readonly requete_id: string;
  readonly cree_le: string | null;
  /** Réponse enregistrée (journal d'idempotence) : forme de `ReponseTutorat`, non revalidée. */
  readonly reponse: Readonly<Record<string, unknown>>;
}

export interface LienExport {
  readonly relation: Relation;
  readonly cree_le: string | null;
}

export interface InvitationExport {
  readonly relation: Relation;
  /** `eleve`, `compte` ou `operateur` (jamais l'identifiant du compte). */
  readonly emis_par: string;
  readonly cree_le: string | null;
  readonly expire_le: string | null;
  readonly utilisee: boolean;
}

/** Tentative de quiz exportée (session 6) : jamais la réponse saisie, seulement le verdict. */
export interface QuizTentativeExport {
  readonly tentative_id: string;
  readonly question_id: string;
  readonly notion_id: string;
  readonly etat: "EN_COURS" | "TERMINEE";
  readonly avec_aide: boolean;
  readonly aides: number;
  readonly verdict: "CORRECT" | "INCORRECT" | "A_REVOIR" | null;
  readonly cree_le: string | null;
  readonly maj_le: string | null;
}

export interface RequeteQuizExport {
  readonly tentative_id: string;
  readonly requete_id: string;
  readonly cree_le: string | null;
  readonly reponse: Readonly<Record<string, unknown>>;
}

export interface ExportRgpdEleve {
  readonly contexte_rgpd: string;
  readonly student_pseudo_id: string;
  readonly anonymisation: string;
  readonly total_tentatives: number;
  readonly total_competences_suivies: number;
  readonly etats_maitrise: Readonly<Record<string, EtatMaitrise>>;
  readonly historique_tentatives: readonly TentativeExport[];
  readonly rappels_memoire: readonly RappelMemoireExport[];
  readonly sessions: readonly SeanceExport[];
  readonly tutorats_mika: readonly TutoratExport[];
  readonly requetes_tutorat_mika: readonly RequeteTutoratExport[];
  readonly quiz_tentatives: readonly QuizTentativeExport[];
  readonly requetes_quiz: readonly RequeteQuizExport[];
  readonly liens_comptes: readonly LienExport[];
  readonly invitations_liens: readonly InvitationExport[];
}

export interface ReponseEffacementRgpd {
  readonly statut: "effacement_effectue";
  readonly message: string;
  readonly student_pseudo_id: string;
  readonly tentatives_supprimees: number;
  readonly etats_supprimes: number;
  readonly rappels_memoire_supprimes: number;
  readonly sessions_supprimees: number;
  readonly tutorats_supprimes: number;
  readonly requetes_tutorat_supprimees: number;
  readonly quiz_tentatives_supprimees: number;
  readonly requetes_quiz_supprimees: number;
  readonly liens_compte_supprimes: number;
  readonly invitations_supprimees: number;
}

// --------------------------------------------------------------------------------------------
// Noms des appels enregistrés dans contrat_front/contrat.json (46). Le test contractuel échoue
// si le contrat en ajoute / retire un sans que cette union (et le client) suive.
// --------------------------------------------------------------------------------------------
export const NOMS_APPELS_CONTRAT = [
  "inscription", "inscription_email_deja_utilise", "inscription_invalide", "connexion", "connexion_refusee",
  "moi", "moi_sans_jeton", "etat_verification_email", "demander_verification_email",
  "confirmer_email_invalide", "confirmer_email", "jeton_eleve_sans_lien",
  "accepter_invitation_sans_confirmation", "accepter_invitation_code_invalide", "accepter_invitation",
  "accepter_invitation_deja_utilisee", "jeton_eleve", "nouvelle_seance", "seance_inconnue", "heartbeat",
  "sauver_etat", "reconnexion", "soumettre_exercice", "soumettre_sans_jeton", "prochaine_etape",
  "tuteur_start", "tuteur_start_rejeu", "tuteur_help", "tuteur_version_perimee", "tuteur_answer",
  "tuteur_comprehension", "tuteur_etat", "emettre_invitation", "inscription_parent2",
  "accepter_invitation_email_non_verifie", "dashboard_parent", "dashboard_non_lie", "export_rgpd_eleve",
  "export_compte", "effacement_par_eleve_refuse", "effacement_rgpd", "jeton_eleve_revoque",
  "changer_mot_de_passe", "ancien_jeton_revoque", "deconnexion", "trop_de_tentatives",
] as const;
export type NomAppelContrat = (typeof NOMS_APPELS_CONTRAT)[number];

/** Porteur du jeton attendu par une route. */
export type Porteur = "compte" | "eleve";
export type AuthRoute = Porteur | "compte_ou_eleve" | "aucune";
export type MethodeHttp = "GET" | "POST" | "DELETE";
