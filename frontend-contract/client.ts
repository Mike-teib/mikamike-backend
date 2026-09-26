// client.ts — Client HTTP de référence du contrat MikaMike, basé sur `fetch` injectable.
//
// - Aucun stockage imposé : les jetons passent par une interface `TokenStore` (implémentation
//   mémoire fournie). Le jeton élève ne doit JAMAIS quitter la mémoire.
// - Aucun journal : ni jeton, ni corps de requête (mots de passe), ni code d'invitation ne sont
//   jamais écrits dans une console ou un message d'erreur.
// - Erreurs typées : `ApiError` (statut HTTP + code `detail`), `ErreurContrat` (réponse hors contrat).
// - Une méthode par opération ; `ROUTES` décrit chaque opération, `COUVERTURE_CONTRAT` relie
//   chaque appel de contrat_front/contrat.json à la méthode qui le réalise.

import type {
  AcceptationCorps, AuthRoute, ChangementEmailCorps, ChangementMotDePasseCorps, CodeErreur, Compte, ConfirmationEmailCorps,
  ConnexionCorps, DashboardParent, ErreurValidation, EtatVerificationEmail, ExportCompte, ExportRgpdEleve,
  InscriptionCorps, InvitationCorps, MethodeHttp, NomAppelContrat, Porteur, ProchaineEtape, ReponseAcceptation,
  ReponseConfirmationEmail, ReponseDemandeVerification, ReponseEffacementRgpd, ReponseHeartbeat, ReponseInvitation,
  ReponseJetonCompte, ReponseJetonEleve, ReponseNouvelleSeance, ReponseReconnexion, ReponseSauvegardeEtat,
  ReponseSoumission, ReponseSuppressionCompte, ReponseTutorat, SauvegardeEtatCorps, SeanceCorps, SoumissionCorps,
  SuppressionCompteCorps, TutoratReponseCorps, TutoratStartCorps, TutoratTransitionCorps, VueTutorat,
} from "./types.ts";
import {
  valider, vCompte, vDashboardParent, vEtatVerificationEmail, vExportCompte, vExportRgpdEleve, vProchaineEtape,
  vReponseAcceptation, vReponseConfirmationEmail, vReponseDemandeVerification, vReponseEffacementRgpd,
  vReponseHeartbeat, vReponseInvitation, vReponseJetonCompte, vReponseJetonEleve, vReponseNouvelleSeance,
  vReponseReconnexion, vReponseSauvegardeEtat, vReponseSoumission, vReponseSuppressionCompte, vReponseTutorat,
  vVueTutorat,
} from "./validators.ts";
import type { Validateur } from "./validators.ts";

export { ErreurContrat } from "./validators.ts";

// --------------------------------------------------------------------------------------------
// Stockage des jetons (injectable)
// --------------------------------------------------------------------------------------------
export interface JetonEleveMemorise {
  readonly token: string;
  /** Instant d'expiration, en millisecondes epoch (horloge du client). */
  readonly expireA: number;
}

export interface TokenStore {
  lireJetonCompte(): string | null;
  ecrireJetonCompte(jeton: string | null): void;
  lireJetonEleve(pseudo: string): JetonEleveMemorise | null;
  ecrireJetonEleve(pseudo: string, jeton: JetonEleveMemorise | null): void;
  purgerJetonsEleves(): void;
}

/** Stockage en mémoire (défaut). Rien ne survit au rechargement : c'est voulu. */
export class MemoryTokenStore implements TokenStore {
  #compte: string | null = null;
  readonly #eleves = new Map<string, JetonEleveMemorise>();

  lireJetonCompte(): string | null {
    return this.#compte;
  }

  ecrireJetonCompte(jeton: string | null): void {
    this.#compte = jeton;
  }

  lireJetonEleve(pseudo: string): JetonEleveMemorise | null {
    return this.#eleves.get(pseudo) ?? null;
  }

  ecrireJetonEleve(pseudo: string, jeton: JetonEleveMemorise | null): void {
    if (jeton === null) this.#eleves.delete(pseudo);
    else this.#eleves.set(pseudo, jeton);
  }

  purgerJetonsEleves(): void {
    this.#eleves.clear();
  }
}

// --------------------------------------------------------------------------------------------
// Erreurs
// --------------------------------------------------------------------------------------------
export class ApiError extends Error {
  readonly status: number;
  /** `detail` (chaîne) ou `detail.code` (409 version_perimee) ; null pour une 422 ou un corps illisible. */
  readonly code: CodeErreur | (string & {}) | null;
  /** Corps `detail` brut (jamais de jeton : c'est la réponse du serveur). */
  readonly detail: unknown;
  /** Secondes à attendre (en-tête Retry-After), pour les 429. */
  readonly retryAfter: number | null;
  /** 409 `version_perimee` : version courante du tutorat. */
  readonly versionCourante: number | null;
  /** 422 : erreurs de validation Pydantic. */
  readonly erreursValidation: readonly ErreurValidation[];

  constructor(status: number, detail: unknown, retryAfter: number | null) {
    const code = typeof detail === "string" ? detail
      : typeof detail === "object" && detail !== null && !Array.isArray(detail)
        && typeof (detail as { code?: unknown }).code === "string" ? (detail as { code: string }).code : null;
    super(`HTTP ${status}${code ? ` ${code}` : ""}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
    this.retryAfter = retryAfter;
    const vc = typeof detail === "object" && detail !== null ? (detail as { version_courante?: unknown }).version_courante : null;
    this.versionCourante = typeof vc === "number" ? vc : null;
    this.erreursValidation = Array.isArray(detail) ? (detail as ErreurValidation[]) : [];
  }

  get estAuth(): boolean {
    return this.status === 401;
  }

  get estInterdit(): boolean {
    return this.status === 403;
  }

  get estLimite(): boolean {
    return this.status === 429;
  }
}

// --------------------------------------------------------------------------------------------
// Description des opérations
// --------------------------------------------------------------------------------------------
export interface RouteDef {
  readonly methode: MethodeHttp;
  /** Relatif à `/api/v1`, avec paramètres `{nom}`. */
  readonly chemin: string;
  readonly auth: AuthRoute;
  /** Porteur utilisé par défaut quand l'appelant n'en précise pas. */
  readonly porteurDefaut: Porteur | null;
  readonly succes: readonly number[];
}

export const ROUTES = {
  inscription: { methode: "POST", chemin: "/comptes/inscription", auth: "aucune", porteurDefaut: null, succes: [201] },
  connexion: { methode: "POST", chemin: "/comptes/connexion", auth: "aucune", porteurDefaut: null, succes: [200] },
  moi: { methode: "GET", chemin: "/comptes/moi", auth: "compte", porteurDefaut: "compte", succes: [200] },
  etatVerificationEmail: { methode: "GET", chemin: "/comptes/verification-email", auth: "compte", porteurDefaut: "compte", succes: [200] },
  demanderVerification: { methode: "POST", chemin: "/comptes/verification-email", auth: "compte", porteurDefaut: "compte", succes: [202] },
  verifierEmail: { methode: "POST", chemin: "/comptes/verification-email/confirmer", auth: "aucune", porteurDefaut: null, succes: [200] },
  changerMotDePasse: { methode: "POST", chemin: "/comptes/mot-de-passe", auth: "compte", porteurDefaut: "compte", succes: [200] },
  changerEmail: { methode: "POST", chemin: "/comptes/email", auth: "compte", porteurDefaut: "compte", succes: [200] },
  deconnexion: { methode: "POST", chemin: "/comptes/deconnexion", auth: "compte", porteurDefaut: "compte", succes: [204] },
  exportCompte: { methode: "GET", chemin: "/comptes/moi/export", auth: "compte", porteurDefaut: "compte", succes: [200] },
  supprimerCompte: { methode: "DELETE", chemin: "/comptes/moi", auth: "compte", porteurDefaut: "compte", succes: [200] },
  jetonEleve: { methode: "POST", chemin: "/auth/eleve/jeton", auth: "compte", porteurDefaut: "compte", succes: [200] },
  emettreInvitation: { methode: "POST", chemin: "/liens/invitations", auth: "compte_ou_eleve", porteurDefaut: "eleve", succes: [201] },
  accepterInvitation: { methode: "POST", chemin: "/liens/accepter", auth: "compte", porteurDefaut: "compte", succes: [201] },
  nouvelleSession: { methode: "POST", chemin: "/session/nouvelle", auth: "eleve", porteurDefaut: "eleve", succes: [201] },
  heartbeat: { methode: "POST", chemin: "/session/heartbeat", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  sauverEtat: { methode: "POST", chemin: "/session/save-state", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  reconnecter: { methode: "POST", chemin: "/session/reconnect", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  soumettreExercice: { methode: "POST", chemin: "/exercices/soumettre", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  prochaineEtape: { methode: "GET", chemin: "/parcours/prochaine-etape", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  tutoratStart: { methode: "POST", chemin: "/mika/session/start", auth: "eleve", porteurDefaut: "eleve", succes: [201, 200] },
  tutoratAnswer: { methode: "POST", chemin: "/mika/session/answer", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  tutoratHelp: { methode: "POST", chemin: "/mika/session/help", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  tutoratComprehension: { methode: "POST", chemin: "/mika/session/comprehension", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  tutoratEtat: { methode: "GET", chemin: "/mika/session/{tutorat_id}", auth: "eleve", porteurDefaut: "eleve", succes: [200] },
  dashboardParent: { methode: "GET", chemin: "/parents/dashboard/{student_pseudo_id}", auth: "compte_ou_eleve", porteurDefaut: "compte", succes: [200] },
  exportRgpdEleve: { methode: "GET", chemin: "/rgpd/export/{student_pseudo_id}", auth: "compte_ou_eleve", porteurDefaut: "compte", succes: [200] },
  effacerRgpdEleve: { methode: "DELETE", chemin: "/rgpd/effacer/{student_pseudo_id}", auth: "compte", porteurDefaut: "compte", succes: [200] },
} as const satisfies Record<string, RouteDef>;

export type OperationId = keyof typeof ROUTES;

/** Chaque appel enregistré dans contrat_front/contrat.json → opération (= méthode) du client. */
export const COUVERTURE_CONTRAT = {
  inscription: "inscription",
  inscription_email_deja_utilise: "inscription",
  inscription_invalide: "inscription",
  inscription_parent2: "inscription",
  connexion: "connexion",
  connexion_refusee: "connexion",
  trop_de_tentatives: "connexion",
  moi: "moi",
  moi_sans_jeton: "moi",
  ancien_jeton_revoque: "moi",
  etat_verification_email: "etatVerificationEmail",
  demander_verification_email: "demanderVerification",
  confirmer_email_invalide: "verifierEmail",
  confirmer_email: "verifierEmail",
  jeton_eleve_sans_lien: "jetonEleve",
  jeton_eleve: "jetonEleve",
  accepter_invitation_sans_confirmation: "accepterInvitation",
  accepter_invitation_code_invalide: "accepterInvitation",
  accepter_invitation: "accepterInvitation",
  accepter_invitation_deja_utilisee: "accepterInvitation",
  accepter_invitation_email_non_verifie: "accepterInvitation",
  emettre_invitation: "emettreInvitation",
  nouvelle_seance: "nouvelleSession",
  seance_inconnue: "heartbeat",
  heartbeat: "heartbeat",
  jeton_eleve_revoque: "heartbeat",
  sauver_etat: "sauverEtat",
  reconnexion: "reconnecter",
  soumettre_exercice: "soumettreExercice",
  soumettre_sans_jeton: "soumettreExercice",
  prochaine_etape: "prochaineEtape",
  tuteur_start: "tutoratStart",
  tuteur_start_rejeu: "tutoratStart",
  tuteur_help: "tutoratHelp",
  tuteur_version_perimee: "tutoratAnswer",
  tuteur_answer: "tutoratAnswer",
  tuteur_comprehension: "tutoratComprehension",
  tuteur_etat: "tutoratEtat",
  dashboard_parent: "dashboardParent",
  dashboard_non_lie: "dashboardParent",
  export_rgpd_eleve: "exportRgpdEleve",
  export_compte: "exportCompte",
  effacement_par_eleve_refuse: "effacerRgpdEleve",
  effacement_rgpd: "effacerRgpdEleve",
  changer_mot_de_passe: "changerMotDePasse",
  deconnexion: "deconnexion",
} as const satisfies Record<NomAppelContrat, OperationId>;

// --------------------------------------------------------------------------------------------
// Client
// --------------------------------------------------------------------------------------------
export type ModeValidation = "stricte" | "souple" | "aucune";
export type FetchLike = (entree: string, init: RequestInit) => Promise<Response>;

export interface OptionsClient {
  /** Origine du backend, ex. `https://staging.example` (le préfixe `/api/v1` est ajouté). */
  readonly baseUrl: string;
  /** Défaut : `globalThis.fetch`. */
  readonly fetchImpl?: FetchLike;
  /** Défaut : `new MemoryTokenStore()`. */
  readonly tokenStore?: TokenStore;
  /** `souple` (défaut) : clés supplémentaires tolérées ; `stricte` : refusées ; `aucune`. */
  readonly validation?: ModeValidation;
  /** Horloge (ms epoch), injectable pour les tests. */
  readonly horloge?: () => number;
  /** Émettre automatiquement un jeton élève (avec le jeton de compte) quand il manque ou expire. Défaut : true. */
  readonly emissionAutoJetonEleve?: boolean;
  /** Marge de renouvellement du jeton élève avant expiration. Défaut : 5 min. */
  readonly margeRenouvellementMs?: number;
  /** Notifié (sans jeton) quand un 401 fait purger un jeton : brancher ici la machine d'état. */
  readonly surErreurAuth?: (erreur: ApiError, porteur: Porteur) => void;
}

export interface OptionsAppel {
  /** Force le porteur du jeton (ex. export RGPD avec le jeton élève). */
  readonly porteur?: Porteur;
  readonly signal?: AbortSignal;
}

interface Requete<T> {
  readonly params?: Readonly<Record<string, string>>;
  readonly query?: Readonly<Record<string, string>>;
  readonly corps?: unknown;
  readonly pseudo?: string;
  readonly validateur?: Validateur<T>;
  readonly options?: OptionsAppel | undefined;
}

/** Codes 401 qui invalident le jeton présenté (≠ `session_inactivite_5min`, qui vise la séance). */
const CODES_401_JETON = new Set<string>([
  "token_absent", "token_invalide", "compte_inconnu", "jeton_revoque", "jeton_requis", "jeton_invalide",
  "jeton_expire", "jeton_compte_requis",
]);

/** UUID v4 pour `requete_id` (une valeur par action, conservée pour les réessais). */
export function nouveauRequeteId(): string {
  return globalThis.crypto.randomUUID();
}

export class MikaClient {
  readonly #base: string;
  readonly #fetch: FetchLike;
  readonly #store: TokenStore;
  readonly #validation: ModeValidation;
  readonly #horloge: () => number;
  readonly #auto: boolean;
  readonly #marge: number;
  readonly #surErreurAuth: ((e: ApiError, p: Porteur) => void) | undefined;

  constructor(options: OptionsClient) {
    this.#base = options.baseUrl.replace(/\/+$/, "") + "/api/v1";
    const f = options.fetchImpl ?? (globalThis.fetch as FetchLike | undefined);
    if (!f) throw new Error("fetch indisponible : fournir fetchImpl");
    this.#fetch = options.fetchImpl ?? ((entree, init) => globalThis.fetch(entree, init));
    this.#store = options.tokenStore ?? new MemoryTokenStore();
    this.#validation = options.validation ?? "souple";
    this.#horloge = options.horloge ?? (() => Date.now());
    this.#auto = options.emissionAutoJetonEleve ?? true;
    this.#marge = options.margeRenouvellementMs ?? 5 * 60_000;
    this.#surErreurAuth = options.surErreurAuth;
  }

  get tokenStore(): TokenStore {
    return this.#store;
  }

  /** Vrai si un jeton de compte est détenu (le jeton lui-même n'est jamais exposé ici). */
  get connecte(): boolean {
    return this.#store.lireJetonCompte() !== null;
  }

  // --- Cœur -----------------------------------------------------------------------------------
  async #appeler<T>(op: OperationId, req: Requete<T>, dejaReessaye = false): Promise<T> {
    const route: RouteDef = ROUTES[op];
    const porteur = req.options?.porteur ?? route.porteurDefaut;
    const jeton = porteur === null ? null : await this.#jeton(porteur, req.pseudo);
    let chemin = route.chemin.replace(/\{(\w+)\}/g, (_m, nom: string) => {
      const v = req.params?.[nom];
      if (v === undefined) throw new Error(`paramètre de chemin manquant : ${nom}`);
      return encodeURIComponent(v);
    });
    if (req.query) chemin += "?" + new URLSearchParams(req.query).toString();
    const headers: Record<string, string> = { Accept: "application/json" };
    if (req.corps !== undefined) headers["Content-Type"] = "application/json";
    if (jeton !== null) headers["Authorization"] = `Bearer ${jeton}`;
    const init: RequestInit = { method: route.methode, headers };
    if (req.corps !== undefined) init.body = JSON.stringify(req.corps);
    if (req.options?.signal) init.signal = req.options.signal;

    const r = await this.#fetch(this.#base + chemin, init);
    const texte = r.status === 204 ? "" : await r.text();
    let json: unknown = null;
    if (texte) {
      try {
        json = JSON.parse(texte);
      } catch {
        json = null;
      }
    }
    if (!r.ok) {
      const brut = r.headers.get("Retry-After");
      const retry = brut !== null && /^\d+$/.test(brut.trim()) ? Number(brut.trim()) : null;
      const detail = typeof json === "object" && json !== null && "detail" in json ? (json as { detail: unknown }).detail : null;
      const err = new ApiError(r.status, detail, retry);
      if (porteur !== null && jeton !== null && r.status === 401 && err.code !== null && CODES_401_JETON.has(err.code)) {
        if (porteur === "eleve" && req.pseudo !== undefined) {
          this.#store.ecrireJetonEleve(req.pseudo, null);
          // Jeton élève expiré : UNE ré-émission puis un seul nouvel essai (FRONT_AUTH_INTEGRATION §3).
          if (err.code === "jeton_expire" && !dejaReessaye && this.#auto && this.#store.lireJetonCompte() !== null) {
            return this.#appeler(op, req, true);
          }
        } else if (porteur === "compte") {
          this.#store.ecrireJetonCompte(null);
          this.#store.purgerJetonsEleves();
        }
        this.#surErreurAuth?.(err, porteur);
      }
      throw err;
    }
    if (req.validateur === undefined || this.#validation === "aucune") return (r.status === 204 ? undefined : json) as T;
    return valider(req.validateur, json, { strict: this.#validation === "stricte" });
  }

  async #jeton(porteur: Porteur, pseudo: string | undefined): Promise<string | null> {
    if (porteur === "compte") return this.#store.lireJetonCompte();
    if (pseudo === undefined) return null;
    const memo = this.#store.lireJetonEleve(pseudo);
    if (memo !== null && this.#horloge() < memo.expireA - this.#marge) return memo.token;
    if (this.#auto && this.#store.lireJetonCompte() !== null) {
      return (await this.obtenirJetonEleve(pseudo, true)).token;
    }
    return memo?.token ?? null;
  }

  // --- Comptes --------------------------------------------------------------------------------
  /** 201. Mémorise le jeton de compte (adresse NON vérifiée : afficher le bandeau). */
  async inscription(corps: InscriptionCorps, options?: OptionsAppel): Promise<ReponseJetonCompte> {
    const r = await this.#appeler("inscription", { corps, validateur: vReponseJetonCompte, options });
    this.#store.purgerJetonsEleves();
    this.#store.ecrireJetonCompte(r.token);
    return r;
  }

  /** 200. 401 `identifiants_invalides` ; 429 `trop_de_tentatives` + `retryAfter`. */
  async connexion(corps: ConnexionCorps, options?: OptionsAppel): Promise<ReponseJetonCompte> {
    const r = await this.#appeler("connexion", { corps, validateur: vReponseJetonCompte, options });
    this.#store.purgerJetonsEleves();
    this.#store.ecrireJetonCompte(r.token);
    return r;
  }

  moi(options?: OptionsAppel): Promise<Compte> {
    return this.#appeler("moi", { validateur: vCompte, options });
  }

  etatVerificationEmail(options?: OptionsAppel): Promise<EtatVerificationEmail> {
    return this.#appeler("etatVerificationEmail", { validateur: vEtatVerificationEmail, options });
  }

  /** 202. Renvoie le courriel (5/h). 503 `courriel_indisponible` si le fournisseur refuse. */
  demanderVerification(options?: OptionsAppel): Promise<ReponseDemandeVerification> {
    return this.#appeler("demanderVerification", { validateur: vReponseDemandeVerification, options });
  }

  /** Sans authentification : le jeton reçu par courriel est la preuve. 400 `jeton_invalide_ou_expire`. */
  verifierEmail(corps: ConfirmationEmailCorps, options?: OptionsAppel): Promise<ReponseConfirmationEmail> {
    return this.#appeler("verifierEmail", { corps, validateur: vReponseConfirmationEmail, options });
  }

  /** Remplace le jeton de compte (les anciens et les jetons élève émis sont révoqués côté serveur). */
  async changerMotDePasse(corps: ChangementMotDePasseCorps, options?: OptionsAppel): Promise<ReponseJetonCompte> {
    const r = await this.#appeler("changerMotDePasse", { corps, validateur: vReponseJetonCompte, options });
    this.#store.purgerJetonsEleves();
    this.#store.ecrireJetonCompte(r.token);
    return r;
  }

  /** Remplace le jeton de compte ; la nouvelle adresse est à revérifier. */
  async changerEmail(corps: ChangementEmailCorps, options?: OptionsAppel): Promise<ReponseJetonCompte> {
    const r = await this.#appeler("changerEmail", { corps, validateur: vReponseJetonCompte, options });
    this.#store.purgerJetonsEleves();
    this.#store.ecrireJetonCompte(r.token);
    return r;
  }

  /** 204. Déconnexion GLOBALE (tous les appareils) ; les jetons locaux sont purgés dans tous les cas. */
  async deconnexion(options?: OptionsAppel): Promise<void> {
    try {
      await this.#appeler<undefined>("deconnexion", { options });
    } finally {
      this.#store.ecrireJetonCompte(null);
      this.#store.purgerJetonsEleves();
    }
  }

  /** Droit d'accès du titulaire du compte (à proposer en téléchargement JSON). */
  exportCompte(options?: OptionsAppel): Promise<ExportCompte> {
    return this.#appeler("exportCompte", { validateur: vExportCompte, options });
  }

  /** 200 puis purge locale. 403 `mot_de_passe_incorrect`, 409 `abonnement_en_cours`. */
  async supprimerCompte(corps: SuppressionCompteCorps, options?: OptionsAppel): Promise<ReponseSuppressionCompte> {
    const r = await this.#appeler("supprimerCompte", { corps, validateur: vReponseSuppressionCompte, options });
    this.#store.ecrireJetonCompte(null);
    this.#store.purgerJetonsEleves();
    return r;
  }

  // --- Jeton élève ----------------------------------------------------------------------------
  /** Émet un jeton élève (jeton de compte lié requis) et le mémorise. 403 `acces_refuse` si non lié. */
  async jetonEleve(corps: { readonly student_pseudo_id: string }, options?: OptionsAppel): Promise<ReponseJetonEleve> {
    const r = await this.#appeler("jetonEleve", { corps, validateur: vReponseJetonEleve, options });
    this.#store.ecrireJetonEleve(corps.student_pseudo_id, {
      token: r.token, expireA: this.#horloge() + r.expires_in * 1000,
    });
    return r;
  }

  /** Jeton élève valide (mémorisé, ou ré-émis s'il expire dans moins de la marge). */
  async obtenirJetonEleve(pseudo: string, forcer = false): Promise<JetonEleveMemorise> {
    const memo = this.#store.lireJetonEleve(pseudo);
    if (!forcer && memo !== null && this.#horloge() < memo.expireA - this.#marge) return memo;
    await this.jetonEleve({ student_pseudo_id: pseudo });
    const neuf = this.#store.lireJetonEleve(pseudo);
    if (neuf === null) throw new Error("jeton élève non mémorisé");
    return neuf;
  }

  // --- Invitations (D8) -----------------------------------------------------------------------
  /** Porteur par défaut : jeton ÉLÈVE ; `{porteur: "compte"}` pour un compte déjà lié. */
  emettreInvitation(corps: InvitationCorps, options?: OptionsAppel): Promise<ReponseInvitation> {
    return this.#appeler("emettreInvitation", {
      corps, pseudo: corps.student_pseudo_id, validateur: vReponseInvitation, options,
    });
  }

  /** 201. 400 `invitation_invalide`, 403 `email_non_verifie`, 409 `deja_lie`, 422 sans confirmation. */
  accepterInvitation(corps: AcceptationCorps, options?: OptionsAppel): Promise<ReponseAcceptation> {
    return this.#appeler("accepterInvitation", { corps, validateur: vReponseAcceptation, options });
  }

  // --- Séance (D15) ---------------------------------------------------------------------------
  nouvelleSession(corps: { readonly user_id: string }, options?: OptionsAppel): Promise<ReponseNouvelleSeance> {
    return this.#appeler("nouvelleSession", { corps, pseudo: corps.user_id, validateur: vReponseNouvelleSeance, options });
  }

  /** 401 `session_inactivite_5min` ⇒ ouvrir une nouvelle séance ; 404 `session_inconnue`. */
  heartbeat(corps: SeanceCorps, options?: OptionsAppel): Promise<ReponseHeartbeat> {
    return this.#appeler("heartbeat", { corps, pseudo: corps.user_id, validateur: vReponseHeartbeat, options });
  }

  sauverEtat(corps: SauvegardeEtatCorps, options?: OptionsAppel): Promise<ReponseSauvegardeEtat> {
    return this.#appeler("sauverEtat", { corps, pseudo: corps.user_id, validateur: vReponseSauvegardeEtat, options });
  }

  reconnecter(corps: SeanceCorps, options?: OptionsAppel): Promise<ReponseReconnexion> {
    return this.#appeler("reconnecter", { corps, pseudo: corps.user_id, validateur: vReponseReconnexion, options });
  }

  // --- Exercices / parcours -------------------------------------------------------------------
  soumettreExercice(corps: SoumissionCorps, options?: OptionsAppel): Promise<ReponseSoumission> {
    return this.#appeler("soumettreExercice", {
      corps, pseudo: corps.student_pseudo_id, validateur: vReponseSoumission, options,
    });
  }

  prochaineEtape(pseudo: string, options?: OptionsAppel): Promise<ProchaineEtape> {
    return this.#appeler("prochaineEtape", {
      query: { student_id: pseudo }, pseudo, validateur: vProchaineEtape, options,
    });
  }

  // --- Tuteur Mika ----------------------------------------------------------------------------
  /** 201 (créé) ou 200 (rejeu, `rejeu: true`). 404 `exercice_indisponible`. */
  tutoratStart(corps: TutoratStartCorps, options?: OptionsAppel): Promise<ReponseTutorat> {
    return this.#appeler("tutoratStart", { corps, pseudo: corps.student_pseudo_id, validateur: vReponseTutorat, options });
  }

  /** 409 `version_perimee` (`versionCourante`) ⇒ `tutoratEtat` puis nouvelle action, NOUVEAU requete_id. */
  tutoratAnswer(corps: TutoratReponseCorps, options?: OptionsAppel): Promise<ReponseTutorat> {
    return this.#appeler("tutoratAnswer", { corps, pseudo: corps.student_pseudo_id, validateur: vReponseTutorat, options });
  }

  tutoratHelp(corps: TutoratTransitionCorps, options?: OptionsAppel): Promise<ReponseTutorat> {
    return this.#appeler("tutoratHelp", { corps, pseudo: corps.student_pseudo_id, validateur: vReponseTutorat, options });
  }

  tutoratComprehension(corps: TutoratReponseCorps, options?: OptionsAppel): Promise<ReponseTutorat> {
    return this.#appeler("tutoratComprehension", {
      corps, pseudo: corps.student_pseudo_id, validateur: vReponseTutorat, options,
    });
  }

  tutoratEtat(tutoratId: string, pseudo: string, options?: OptionsAppel): Promise<VueTutorat> {
    return this.#appeler("tutoratEtat", {
      params: { tutorat_id: tutoratId }, query: { student_id: pseudo }, pseudo, validateur: vVueTutorat, options,
    });
  }

  // --- Parent / RGPD --------------------------------------------------------------------------
  /** Porteur par défaut : compte (parent lié) ; 403 `acces_refuse` si non lié ou lien révoqué. */
  dashboardParent(pseudo: string, options?: OptionsAppel): Promise<DashboardParent> {
    return this.#appeler("dashboardParent", {
      params: { student_pseudo_id: pseudo }, pseudo, validateur: vDashboardParent, options,
    });
  }

  /** 404 `aucune_donnee_trouvee_pour_cet_identifiant` si rien n'est enregistré. */
  exportRgpdEleve(pseudo: string, options?: OptionsAppel): Promise<ExportRgpdEleve> {
    return this.#appeler("exportRgpdEleve", {
      params: { student_pseudo_id: pseudo }, pseudo, validateur: vExportRgpdEleve, options,
    });
  }

  /** Compte PARENT lié uniquement (D9). Purge le jeton élève local de cet enfant. */
  async effacerRgpdEleve(pseudo: string, options?: OptionsAppel): Promise<ReponseEffacementRgpd> {
    const r = await this.#appeler("effacerRgpdEleve", {
      params: { student_pseudo_id: pseudo }, pseudo, validateur: vReponseEffacementRgpd, options,
    });
    this.#store.ecrireJetonEleve(pseudo, null);
    return r;
  }
}
