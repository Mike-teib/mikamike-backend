// contrat.ts — Outils partagés des tests : lecture de contrat_front/contrat.json, génération
// d'une réponse échantillon à partir d'une FORME enregistrée, `fetch` factice.

import { existsSync, readFileSync } from "node:fs";

import type { MethodeHttp, NomAppelContrat } from "../types.ts";

export type Forme = string | boolean | readonly Forme[] | { readonly [cle: string]: Forme };

export interface AppelContrat {
  readonly nom: NomAppelContrat;
  readonly methode: MethodeHttp;
  readonly chemin: string;
  readonly auth: "compte" | "eleve" | null;
  readonly corps: Readonly<Record<string, unknown>> | null;
  readonly statut_http: number;
  readonly reponse: Forme;
  readonly retry_after?: boolean;
}

export interface Contrat {
  readonly version_contrat: number;
  readonly base: string;
  readonly appels: readonly AppelContrat[];
}

/** `MIKA_CONTRAT_JSON` ou, par défaut, `../../contrat_front/contrat.json` (dépôt backend). */
export function chargerContrat(): Contrat {
  const chemin = process.env["MIKA_CONTRAT_JSON"] ?? new URL("../../contrat_front/contrat.json", import.meta.url);
  if (!existsSync(chemin)) {
    throw new Error("contrat.json introuvable : définir MIKA_CONTRAT_JSON (copie de contrat_front/contrat.json)");
  }
  return JSON.parse(readFileSync(chemin, "utf8")) as Contrat;
}

const MARQUEURS = new Set(["string", "integer", "number", "boolean", "null"]);

/**
 * Valeur échantillon pour un champ enregistré « string » dont le type TS est plus précis
 * (énumération) : contrat.json ne conserve la valeur que pour quelques clés contractuelles.
 */
function raffiner(chemin: readonly string[]): string {
  const dernier = chemin[chemin.length - 1];
  const parent = chemin[chemin.length - 2];
  const grandParent = chemin[chemin.length - 3];
  if (dernier === "etat_maitrise") return "EN_COURS";
  if (parent === "progression") {
    if (dernier === "niveau") return "EN_COURS";
    if (dernier === "moteur") return "historique";
    if (dernier === "prochaine_action") return "entrainement_autonome";
  }
  if (grandParent === "competences" && dernier === "etat") return "INCONNU";
  if (parent === "etats_maitrise") return "ACQUIS_ASSISTE";
  if (dernier === "statut_abonnement") return "aucun";
  if (dernier === "token_type") return "Bearer";
  return "texte";
}

/** Instancie une forme : « integer » → 1, « string » → texte, valeur littérale conservée. */
export function echantillon(forme: Forme, chemin: readonly string[] = []): unknown {
  if (typeof forme === "boolean") return forme;
  if (typeof forme === "string") {
    if (!MARQUEURS.has(forme)) return forme; // énumération / code d'erreur conservé tel quel
    switch (forme) {
      case "string": return raffiner(chemin);
      case "integer": return 1;
      case "number": return 0.5;
      case "boolean": return true;
      default: return null;
    }
  }
  if (Array.isArray(forme)) return forme.map((f, i) => echantillon(f, [...chemin, String(i)]));
  const o: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(forme as Record<string, Forme>)) o[k] = echantillon(v, [...chemin, k]);
  return o;
}

export interface RequeteEnregistree {
  readonly url: string;
  readonly methode: string;
  readonly headers: Readonly<Record<string, string>>;
  readonly corps: unknown;
}

export interface ReponseFactice {
  readonly status: number;
  readonly corps?: unknown;
  readonly headers?: Readonly<Record<string, string>>;
}

/** `fetch` factice : répond dans l'ordre de `reponses`, enregistre chaque requête. */
export function fetchFactice(reponses: ReponseFactice[]) {
  const requetes: RequeteEnregistree[] = [];
  const impl = async (url: string, init: RequestInit): Promise<Response> => {
    const h = (init.headers ?? {}) as Record<string, string>;
    requetes.push({
      url, methode: init.method ?? "GET", headers: { ...h },
      corps: typeof init.body === "string" ? JSON.parse(init.body) : undefined,
    });
    const r = reponses.shift();
    if (r === undefined) throw new Error(`requête inattendue : ${init.method} ${url}`);
    const corps = r.status === 204 || r.corps === undefined ? null : JSON.stringify(r.corps);
    return new Response(corps, {
      status: r.status, headers: { "Content-Type": "application/json", ...(r.headers ?? {}) },
    });
  };
  return { impl, requetes };
}
