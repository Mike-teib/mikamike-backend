// Parcours 4 — Tableau de bord parent (jeton de compte parent lié). Schéma fermé : progression,
// compétences, activité ; aucune donnée nominative.

import { transitionLien } from "../parent-link-state.ts";
import type { EtatLien } from "../parent-link-state.ts";
import { ApiError, MikaClient } from "../client.ts";
import type { DashboardParent } from "../types.ts";

export async function chargerDashboard(parent: MikaClient, lien: EtatLien): Promise<{
  lien: EtatLien; dashboard: DashboardParent | null;
}> {
  if (lien.etat !== "ACCEPTEE") return { lien, dashboard: null }; // dashboardAccessible(lien) === false
  try {
    const d = await parent.dashboardParent(lien.pseudo);
    return { lien: transitionLien(lien, { type: "DASHBOARD_OK" }), dashboard: d };
  } catch (e) {
    // 403 acces_refuse : lien supprimé (effacement RGPD, compte supprimé) ⇒ retirer l'enfant de l'interface.
    if (e instanceof ApiError && e.status === 403) return { lien: transitionLien(lien, { type: "DASHBOARD_REFUSE", status: 403 }), dashboard: null };
    throw e;
  }
}

/** Libellé accessible du taux de réussite (« 7 sur 10 »), sans information par la couleur seule. */
export function libelleTaux(d: DashboardParent): string {
  const s = d.statistiques_pedagogiques;
  return `${s.exercices_reussis} sur ${s.exercices_tentes} exercices réussis`;
}
