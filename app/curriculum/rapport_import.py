"""
rapport_import.py — Simulation à blanc (« dry-run »), rapport, métriques, quarantaine et
comparaison avant/après d'un lot d'artefacts (lot 6, session 4).

`simuler(dossier, sha)` n'écrit RIEN hors de son éventuel checkpoint : il importe (manifest
épinglé, intégrité croisée), mesure, liste la quarantaine et compare au lot ACTIF du dépôt
(ajouts, retraits, modifications par empreinte de contenu, changements de statut de preuve).
C'est le rapport que l'on lit AVANT `DepotContenu.publier`. Déterministe (tri partout).

Quarantaine = toute notion non PROVEN (NOT_EVIDENCED, AMBIGUOUS, QUARANTINED) ou touchée par
une anomalie, avec ses raisons. Rien n'y est « corrigé » automatiquement.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

from app.curriculum.depot import DepotContenu, DepotInvalide
from app.curriculum.importers import ResultatImport, importer
from app.curriculum.model import StatutPreuve
from app.curriculum.provenance import evaluer_preuve


def _empreinte(obj) -> str:
    brut = json.dumps(obj.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def _index(res: Optional[ResultatImport]) -> Dict[str, Dict[str, str]]:
    if res is None or res.referentiel is None:
        return {"notions": {}, "contenus": {}}
    return {"notions": {n.id: _empreinte(n) for n in res.referentiel.notions},
            "contenus": {c.id: _empreinte(c) for c in [*res.exercices, *res.quiz]}}


def _statuts(res: Optional[ResultatImport], autoriser_fictif: bool) -> Dict[str, str]:
    if res is None or res.referentiel is None:
        return {}
    idx = res.referentiel.index()
    return {n.id: evaluer_preuve(n, idx.sources.get(n.preuve.source_id) if n.preuve else None,
                                 autoriser_fictif=autoriser_fictif).statut.value for n in res.referentiel.notions}


def comparer(avant: Optional[ResultatImport], apres: ResultatImport, *, autoriser_fictif: bool = False) -> Dict[str, Any]:
    a, b = _index(avant), _index(apres)
    out: Dict[str, Any] = {}
    for genre in ("notions", "contenus"):
        ka, kb = set(a[genre]), set(b[genre])
        out[genre] = {"ajoutes": sorted(kb - ka), "retires": sorted(ka - kb),
                      "modifies": sorted(k for k in ka & kb if a[genre][k] != b[genre][k])}
    sa, sb = _statuts(avant, autoriser_fictif), _statuts(apres, autoriser_fictif)
    out["changements_de_preuve"] = sorted(
        {"notion_id": k, "avant": sa[k], "apres": sb[k]} for k in set(sa) & set(sb) if sa[k] != sb[k])
    identique = not any(out[g][x] for g in ("notions", "contenus") for x in ("ajoutes", "retires", "modifies"))
    out["identique_au_lot_actif"] = bool(avant is not None and identique)
    return out


def simuler(dossier: Path, sha256_manifest: str, *, depot: Optional[Path] = None, rentree: Optional[int] = None,
            autoriser_fictif: bool = False, checkpoint: Optional[Path] = None) -> Dict[str, Any]:
    res = importer(Path(dossier), sha256_manifest=sha256_manifest, rentree=rentree,
                   autoriser_fictif=autoriser_fictif, checkpoint=checkpoint)
    rapport: Dict[str, Any] = {
        "mode": "SIMULATION",  # rien n'est publié ni activé
        "statut": res.statut,
        "lot": res.manifest,
        "fichiers": {k: res.fichiers[k] for k in sorted(res.fichiers)},
        "publiable": res.statut == "VALIDATED",
    }
    if res.statut == "FAILED":
        return rapport
    statuts = _statuts(res, autoriser_fictif)
    touches = {a.objet_id for a in res.anomalies}
    ref = res.referentiel
    rapport["metriques"] = {
        "notions": len(ref.notions),
        "notions_par_statut_preuve": dict(sorted(Counter(statuts.values()).items())),
        "notions_par_matiere_niveau": dict(sorted(Counter(f"{n.matiere.value}/{n.niveau.value}" for n in ref.notions).items())),
        "chapitres": len(ref.chapitres), "programmes": len(ref.programmes), "sources": len(ref.sources),
        "exercices": len(res.exercices), "quiz": len(res.quiz), "plans": len(res.plans),
        "documents_sources": len(res.documents),
        "opaques_par_role": dict(sorted(Counter(o.get("role", o.get("statut")) for o in res.opaques).items())),
        "anomalies_par_code": dict(sorted(Counter(a.code for a in res.anomalies).items())),
        "generables": len(res.integrite.generables) if res.integrite else 0,
    }
    rapport["quarantaine"] = sorted(
        ({"notion_id": nid, "statut_preuve": st,
          "raisons": sorted({a.code for a in res.anomalies if a.objet_id == nid})}
         for nid, st in statuts.items() if st != StatutPreuve.PROVEN.value or nid in touches),
        key=lambda x: x["notion_id"])
    rapport["anomalies"] = [{"code": a.code, "objet": a.objet_id, "detail": a.detail} for a in res.anomalies]
    if depot is not None:
        try:
            actif = DepotContenu(Path(depot), autoriser_fictif=autoriser_fictif).charger_actif()
        except DepotInvalide as exc:
            rapport["comparaison"] = {"erreur": str(exc)}
        else:
            rapport["comparaison"] = comparer(actif, res, autoriser_fictif=autoriser_fictif)
            if rapport["comparaison"]["identique_au_lot_actif"]:
                rapport["avertissements"] = ["LOT_IDENTIQUE_AU_LOT_ACTIF"]
    return rapport


def en_markdown(r: Dict[str, Any]) -> str:
    lignes = [f"# Rapport d'import — {r.get('lot', {}).get('lot_id', '?')} ({r['mode']})", "",
              f"Statut : **{r['statut']}** · publiable : **{'oui' if r['publiable'] else 'non'}**", ""]
    lignes += ["| Fichier | État | Détail |", "|---|---|---|"]
    lignes += [f"| `{k}` | {v['etat']} | {v.get('raison', '')} |" for k, v in r["fichiers"].items()]
    if "metriques" in r:
        lignes += ["", "## Métriques", "```json", json.dumps(r["metriques"], ensure_ascii=False, indent=2), "```",
                   "", f"## Quarantaine ({len(r['quarantaine'])})"]
        lignes += [f"- `{q['notion_id']}` {q['statut_preuve']} {', '.join(q['raisons'])}" for q in r["quarantaine"][:200]]
    if "comparaison" in r:
        lignes += ["", "## Comparaison avec le lot actif", "```json",
                   json.dumps(r["comparaison"], ensure_ascii=False, indent=2), "```"]
    for a in r.get("avertissements", []):
        lignes.append(f"\n**AVERTISSEMENT : {a}**")
    return "\n".join(lignes) + "\n"
