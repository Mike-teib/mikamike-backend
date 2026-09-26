#!/usr/bin/env node
// verifier_contrat.mjs — Rejoue la partie PUBLIQUE du contrat front contre un serveur réel.
//
//   node contrat_front/verifier_contrat.mjs http://127.0.0.1:8000
//
// Node >= 18, aucune dépendance. Pour chaque étape : même statut HTTP et même FORME de réponse
// que dans contrat.json (types ; valeurs d'énumération et codes d'erreur à l'identique).
// Les étapes qui exigent un courriel reçu ou un code d'opérateur ne sont vérifiables qu'en
// processus (tools/contrat_front.py) : elles ne sont pas rejouées ici.
// À utiliser par le front contre un environnement de STAGING, jamais contre la production.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const base = (process.argv[2] || process.env.MIKA_BASE_URL || "").replace(/\/$/, "");
if (!base) {
  console.error("usage : node verifier_contrat.mjs <base-url>");
  process.exit(2);
}
const ici = dirname(fileURLToPath(import.meta.url));
const contrat = JSON.parse(readFileSync(join(ici, "contrat.json"), "utf8"));
const parNom = Object.fromEntries(contrat.appels.map((a) => [a.nom, a]));

const CONTRACTUELLES = new Set(["detail", "statut", "relation", "typ", "token_type", "contract_version", "action",
  "derniere_action", "role", "usage_unique", "niveau_estime", "code"]);
const ENUM = /^([a-z][a-z0-9_:/.\-]{0,59}|[A-Z][A-Z_]{2,40})$/;

// Même normalisation que tools/contrat_front.py::forme.
function forme(v, cle) {
  if (CONTRACTUELLES.has(cle) && (typeof v === "boolean" || (typeof v === "string" && ENUM.test(v)))) return v;
  if (typeof v === "boolean") return "boolean";
  if (typeof v === "number") return Number.isInteger(v) ? "integer" : "number";
  if (v === null || v === undefined) return "null";
  if (typeof v === "string") return "string";
  if (Array.isArray(v)) return v.length ? [forme(v[0])] : [];
  if (typeof v === "object") {
    const o = {};
    for (const k of Object.keys(v).sort()) o[k] = forme(v[k], k);
    return o;
  }
  return typeof v;
}

const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
let echecs = 0;
const suffixe = `${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
const EMAIL = `contrat-${suffixe}@example.com`;
const MDP = "motdepasse-contrat-01";

async function etape(nom, { methode, chemin, jeton, corps }) {
  const attendu = parNom[nom];
  if (!attendu) throw new Error(`étape inconnue du contrat : ${nom}`);
  const r = await fetch(base + chemin, {
    method: methode,
    headers: { "Content-Type": "application/json", ...(jeton ? { Authorization: `Bearer ${jeton}` } : {}) },
    body: corps === undefined ? undefined : JSON.stringify(corps),
  });
  const texte = await r.text();
  let json = null;
  try { json = texte ? JSON.parse(texte) : null; } catch { json = texte.slice(0, 40); }
  const ok = r.status === attendu.statut_http && egal(forme(json), attendu.reponse);
  if (!ok) {
    echecs += 1;
    console.log(`ÉCHEC ${nom} : HTTP ${r.status} (attendu ${attendu.statut_http})`);
    console.log(`  reçu    ${JSON.stringify(forme(json))}`);
    console.log(`  attendu ${JSON.stringify(attendu.reponse)}`);
  } else {
    console.log(`ok     ${nom}`);
  }
  return json;
}

const P = "/api/v1";
let t = (await etape("inscription", { methode: "POST", chemin: `${P}/comptes/inscription`,
  corps: { email: EMAIL, mot_de_passe: MDP, prenom: "Prénom", role: "parent" } }))?.token;
await etape("inscription_email_deja_utilise", { methode: "POST", chemin: `${P}/comptes/inscription`,
  corps: { email: EMAIL, mot_de_passe: MDP } });
await etape("inscription_invalide", { methode: "POST", chemin: `${P}/comptes/inscription`,
  corps: { email: "pas-un-email", mot_de_passe: "court" } });
t = (await etape("connexion", { methode: "POST", chemin: `${P}/comptes/connexion`,
  corps: { email: EMAIL, mot_de_passe: MDP } }))?.token;
await etape("connexion_refusee", { methode: "POST", chemin: `${P}/comptes/connexion`,
  corps: { email: EMAIL, mot_de_passe: "mauvais-mdp-00" } });
await etape("moi", { methode: "GET", chemin: `${P}/comptes/moi`, jeton: t });
await etape("moi_sans_jeton", { methode: "GET", chemin: `${P}/comptes/moi` });
await etape("etat_verification_email", { methode: "GET", chemin: `${P}/comptes/verification-email`, jeton: t });
await etape("demander_verification_email", { methode: "POST", chemin: `${P}/comptes/verification-email`, jeton: t });
await etape("confirmer_email_invalide", { methode: "POST", chemin: `${P}/comptes/verification-email/confirmer`,
  corps: { jeton: "jeton-inconnu" } });
await etape("jeton_eleve_sans_lien", { methode: "POST", chemin: `${P}/auth/eleve/jeton`, jeton: t,
  corps: { student_pseudo_id: `eleve-contrat-${suffixe}` } });
await etape("soumettre_sans_jeton", { methode: "POST", chemin: `${P}/exercices/soumettre`,
  corps: { exercice_id: "exo-maths-calcul-litteral-1", student_pseudo_id: "eleve-contrat-01", reponse: "5x" } });
const nouveau = (await etape("changer_mot_de_passe", { methode: "POST", chemin: `${P}/comptes/mot-de-passe`,
  jeton: t, corps: { ancien: MDP, nouveau: "nouveau-mdp-contrat" } }))?.token;
await etape("ancien_jeton_revoque", { methode: "GET", chemin: `${P}/comptes/moi`, jeton: t });
await etape("deconnexion", { methode: "POST", chemin: `${P}/comptes/deconnexion`, jeton: nouveau });

console.log(echecs ? `\n${echecs} écart(s) au contrat` : "\ncontrat respecté");
process.exit(echecs ? 1 : 0);
