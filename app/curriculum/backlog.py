"""
backlog.py — Backlog canonique REPRODUCTIBLE (Phase 19).

Calcule, par matière / programme / niveau / chapitre, à partir des données
(jamais à la main) :
  NOTIONS_TOTAL, PROVEN, NOT_EVIDENCED, AMBIGUOUS, QUARANTINED,
  WITH_EXERCISE, WITH_QUIZ, WITH_BOTH, NEED_EXERCISE, NEED_QUIZ,
  WAITING_ORACLE, WAITING_SOURCE.

Définitions :
  - le statut de preuve est RECALCULÉ (evaluer_preuve), pas lu tel que déclaré ;
  - NEED_EXERCISE / NEED_QUIZ : notion PROVEN (génération autorisée) sans exercice / quiz ;
  - WAITING_SOURCE : notion non PROVEN (preuve absente, ambiguë ou en quarantaine) ;
  - WAITING_ORACLE : notion PROVEN dont aucun exercice n'a de vérificateur
    automatique qui valide sa propre réponse (vérification humaine requise) ;
  - les notions optionnelles sont exclues des totaux (comptées à part : OPTIONAL) ;
  - VERROU D'INTÉGRITÉ (session 2) : NEED_EXERCISE / NEED_QUIZ ne comptent que les notions
    « générables » du rapport `integrite.verifier_integrite` — si l'intégrité croisée du lot
    n'est pas démontrée, aucune notion n'est à générer ;
  - ventilations : par matière, programme, niveau, chapitre, et HIÉRARCHIQUE
    `matière / niveau / programme / chapitre` (`par_hierarchie`).
Sortie triée ⇒ deux exécutions sur les mêmes données donnent un résultat identique.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence

from app.curriculum.exercices import Exercice
from app.curriculum.integrite import RapportIntegrite, verifier_integrite
from app.curriculum.model import Referentiel, StatutPreuve
from app.curriculum.provenance import autorisation_generation, evaluer_preuve
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import verifier

INDICATEURS = (
    "NOTIONS_TOTAL", "OPTIONAL", "PROVEN", "NOT_EVIDENCED", "AMBIGUOUS", "QUARANTINED",
    "WITH_EXERCISE", "WITH_QUIZ", "WITH_BOTH", "NEED_EXERCISE", "NEED_QUIZ",
    "WAITING_ORACLE", "WAITING_SOURCE",
)


def _vide() -> Dict[str, int]:
    return {k: 0 for k in INDICATEURS}


def calculer_backlog(
    ref: Referentiel,
    exercices: Sequence[Exercice] = (),
    quiz: Sequence[QuestionQuiz] = (),
    *,
    autoriser_fictif: bool = False,
    integrite: Optional[RapportIntegrite] = None,
) -> Dict[str, object]:
    idx = ref.index()
    if integrite is None:
        integrite = verifier_integrite(ref, exercices, quiz, autoriser_fictif=autoriser_fictif)
    exo_par_notion: Dict[str, List[Exercice]] = defaultdict(list)
    for e in exercices:
        exo_par_notion[e.notion_id].append(e)
    quiz_notions = {q.notion_id for q in quiz}

    axes = ("matiere", "programme", "niveau", "chapitre", "hierarchie")
    par: Dict[str, Dict[str, Dict[str, int]]] = {a: defaultdict(_vide) for a in axes}
    total = _vide()
    detail_notions: List[Dict[str, str]] = []

    for n in sorted(ref.notions, key=lambda x: x.id):
        cles = {
            "matiere": n.matiere.value,
            "programme": n.programme_id,
            "niveau": n.niveau.value,
            "chapitre": n.chapitre_id or "(sans chapitre)",
        }
        cles["hierarchie"] = " / ".join((cles["matiere"], cles["niveau"], cles["programme"], cles["chapitre"]))
        buckets = [total] + [par[a][cles[a]] for a in axes]
        if n.optionnelle:
            for b in buckets:
                b["OPTIONAL"] += 1
            continue

        source = idx.sources.get(n.preuve.source_id) if n.preuve else None
        statut = evaluer_preuve(n, source, autoriser_fictif=autoriser_fictif).statut
        autorise = autorisation_generation(n, idx, autoriser_fictif=autoriser_fictif).autorise \
            and n.id in integrite.generables
        a_exo, a_quiz = bool(exo_par_notion.get(n.id)), n.id in quiz_notions
        oracle_ok = any(
            verifier(e.type_verification, e.reponse_attendue, e.reponse_attendue,
                     e.parametres_verification).verdict == Verdict.VALID
            for e in exo_par_notion.get(n.id, [])
        )
        drapeaux = {
            "NOTIONS_TOTAL": True,
            "PROVEN": statut == StatutPreuve.PROVEN,
            "NOT_EVIDENCED": statut == StatutPreuve.NOT_EVIDENCED,
            "AMBIGUOUS": statut == StatutPreuve.AMBIGUOUS,
            "QUARANTINED": statut == StatutPreuve.QUARANTINED,
            "WITH_EXERCISE": a_exo,
            "WITH_QUIZ": a_quiz,
            "WITH_BOTH": a_exo and a_quiz,
            "NEED_EXERCISE": autorise and not a_exo,
            "NEED_QUIZ": autorise and not a_quiz,
            "WAITING_ORACLE": statut == StatutPreuve.PROVEN and a_exo and not oracle_ok,
            "WAITING_SOURCE": statut != StatutPreuve.PROVEN,
        }
        for b in buckets:
            for k, v in drapeaux.items():
                b[k] += int(v)
        detail_notions.append({"notion_id": n.id, "statut_preuve": statut.value,
                               "generation_autorisee": str(autorise).lower()})

    codes: Dict[str, int] = defaultdict(int)
    for a in integrite.anomalies:
        codes[a.code] += 1
    return {
        "integrite": {"demontree": integrite.demontree, "anomalies": len(integrite.anomalies),
                      "codes": dict(sorted(codes.items()))},
        "total": total,
        **{f"par_{a}": {k: par[a][k] for k in sorted(par[a])} for a in axes},
        "notions": detail_notions,
    }


def en_markdown(backlog: Dict[str, object], titre: str = "Backlog canonique") -> str:
    integ = backlog.get("integrite", {})  # type: ignore[union-attr]
    lignes = [f"# {titre}", "",
              f"Intégrité démontrée : **{'OUI' if integ.get('demontree') else 'NON'}** "
              f"({integ.get('anomalies', 0)} anomalie(s)) — sans intégrité, aucune génération.", "",
              "| Indicateur | Valeur |", "|---|---|"]
    lignes += [f"| {k} | {v} |" for k, v in backlog["total"].items()]  # type: ignore[union-attr]
    if backlog.get("par_hierarchie"):
        cols_h = ("NOTIONS_TOTAL", "PROVEN", "NOT_EVIDENCED", "QUARANTINED", "WITH_EXERCISE", "WITH_QUIZ",
                  "WITH_BOTH", "NEED_EXERCISE", "NEED_QUIZ", "WAITING_SOURCE", "WAITING_ORACLE")
        lignes += ["", "## Par matière / niveau / programme / chapitre", "",
                   "| Matière / niveau / programme / chapitre | " + " | ".join(cols_h) + " |",
                   "|---|" + "---|" * len(cols_h)]
        for cle, vals in backlog["par_hierarchie"].items():  # type: ignore[union-attr]
            lignes.append(f"| `{cle}` | " + " | ".join(str(vals[c]) for c in cols_h) + " |")
    for axe in ("par_matiere", "par_niveau", "par_programme", "par_chapitre"):
        groupes = backlog[axe]  # type: ignore[index]
        if not groupes:
            continue
        cols = ("NOTIONS_TOTAL", "PROVEN", "WAITING_SOURCE", "NEED_EXERCISE", "NEED_QUIZ", "WITH_BOTH")
        lignes += ["", f"## {axe.replace('_', ' ')}", "", "| Clé | " + " | ".join(cols) + " |",
                   "|---|" + "---|" * len(cols)]
        for cle, vals in groupes.items():  # type: ignore[union-attr]
            lignes.append(f"| `{cle}` | " + " | ".join(str(vals[c]) for c in cols) + " |")
    return "\n".join(lignes) + "\n"


def notions_a_traiter(backlog: Dict[str, object]) -> Iterable[str]:
    return (d["notion_id"] for d in backlog["notions"] if d["generation_autorisee"] == "true")  # type: ignore[index]
