"""
coverage.py — Matrice de couverture 6e → Terminale (Maths, PC, SVT + ST 6e, ES 1re/Tle).

  python -m pedagogy.coverage [--out-dir DIR]
  → PEDAGOGY_COVERAGE_MATRIX.csv et PEDAGOGY_COVERAGE_REPORT.md (déterministes, sans horodatage)

QA_STATUS par notion :
  BLOCKED_UNPROVEN     notion non prouvée officiellement : aucun contenu autorisé
  BLOCKED_CONFLICT     sources contradictoires
  NO_CONTENT           notion prouvée, banque vide
  CONTENT_QA_FAIL      notion prouvée, au moins un exercice/quiz avec BLOCKER/ERROR
  CONTENT_QA_PASS      notion prouvée, contenu présent sans BLOCKER/ERROR
Les couples matière × niveau sans enseignement propre (PC/SVT en 6e, ES avant la 1re…) sont
listés avec NOTION_ID vide et QA_STATUS=NOT_APPLICABLE et la raison.
"""

from __future__ import annotations

import argparse
import csv
import io
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from pedagogy.issues import Severity
from pedagogy.models import (
    BANK_TARGET,
    LEVEL_ORDER,
    QUIZ_TARGET_PER_NOTION,
    SUBJECT_LEVELS,
    ProofStatus,
    Subject,
)
from pedagogy.registry import DATA_DIR, REPO_ROOT, Registry, load_registry

COLUMNS = ["SUBJECT", "LEVEL", "COURSE", "DOMAIN", "CHAPTER", "NOTION_ID", "NOTION_TITLE", "PROOF_STATUS",
           "SOURCE", "EXERCISES_COUNT", "QUIZ_COUNT", "QA_STATUS"]

REPORTED_SUBJECTS = (Subject.MATHS, Subject.PHYSIQUE_CHIMIE, Subject.SVT,
                     Subject.SCIENCES_TECHNOLOGIE, Subject.ENSEIGNEMENT_SCIENTIFIQUE)

NOT_APPLICABLE_REASON = {
    Subject.PHYSIQUE_CHIMIE: "en 6e (cycle 3) : enseignement « Sciences et technologie » (voir SUBJECT=SCIENCES_TECHNOLOGIE)",
    Subject.SVT: "en 6e (cycle 3) : enseignement « Sciences et technologie » (voir SUBJECT=SCIENCES_TECHNOLOGIE)",
    Subject.SCIENCES_TECHNOLOGIE: "enseignement du cycle 3 uniquement (6e dans le périmètre)",
    Subject.ENSEIGNEMENT_SCIENTIFIQUE: "tronc commun de 1re et Terminale uniquement",
}


def _content_issues(reg: Registry) -> Dict[str, List[Tuple[str, str]]]:
    """Anomalies BLOCKER/ERROR par notion, issues des validateurs de contenu (si disponibles)."""
    from pedagogy.validators.exercise import validate_exercise
    from pedagogy.validators.quiz import validate_quiz

    out: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for items, fn in ((reg.exercises.values(), validate_exercise), (reg.quizzes.values(), validate_quiz)):
        for it in items:
            try:
                issues = fn(it, reg)
            except NotImplementedError:
                continue
            for i in issues:
                if i.severity in (Severity.BLOCKER, Severity.ERROR):
                    out[it.notion_id].append((i.code, i.object_id))
    return out


def build_rows(reg: Registry) -> List[Dict[str, str]]:
    ex_count = Counter(e.notion_id for e in reg.exercises.values())
    qz_count = Counter(q.notion_id for q in reg.quizzes.values())
    bad = _content_issues(reg)
    rows: List[Dict[str, str]] = []
    for subject in REPORTED_SUBJECTS:
        for level in LEVEL_ORDER:
            if level not in SUBJECT_LEVELS[subject]:
                rows.append({c: "" for c in COLUMNS} | {
                    "SUBJECT": subject.value, "LEVEL": level.value, "QA_STATUS": "NOT_APPLICABLE",
                    "NOTION_TITLE": NOT_APPLICABLE_REASON[subject], "EXERCISES_COUNT": "0", "QUIZ_COUNT": "0"})
                continue
            notions = reg.by_subject_level(subject, level)
            if not notions:
                rows.append({c: "" for c in COLUMNS} | {
                    "SUBJECT": subject.value, "LEVEL": level.value, "QA_STATUS": "NO_NOTION",
                    "NOTION_TITLE": "aucune notion dans le registre", "EXERCISES_COUNT": "0", "QUIZ_COUNT": "0"})
                continue
            for n in sorted(notions, key=lambda x: (x.course.value, x.domain_code, x.chapter, x.notion_id)):
                if n.proof_status == ProofStatus.CONFLICT:
                    qa = "BLOCKED_CONFLICT"
                elif n.proof_status != ProofStatus.PROVEN_OFFICIAL:
                    qa = "BLOCKED_UNPROVEN"
                elif not ex_count[n.notion_id] and not qz_count[n.notion_id]:
                    qa = "NO_CONTENT"
                else:
                    qa = "CONTENT_QA_FAIL" if bad.get(n.notion_id) else "CONTENT_QA_PASS"
                rows.append({
                    "SUBJECT": subject.value, "LEVEL": level.value, "COURSE": n.course.value,
                    "DOMAIN": n.domain, "CHAPTER": n.chapter, "NOTION_ID": n.notion_id, "NOTION_TITLE": n.title,
                    "PROOF_STATUS": n.proof_status.value,
                    "SOURCE": f"{n.source_id or ''} | {n.source_url_or_ref}".strip(" |"),
                    "EXERCISES_COUNT": str(ex_count[n.notion_id]), "QUIZ_COUNT": str(qz_count[n.notion_id]),
                    "QA_STATUS": qa,
                })
    return rows


def to_csv(rows: List[Dict[str, str]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_report(reg: Registry, rows: List[Dict[str, str]]) -> str:
    notion_rows = [r for r in rows if r["NOTION_ID"]]
    by_proof = Counter(r["PROOF_STATUS"] for r in notion_rows)
    by_qa = Counter(r["QA_STATUS"] for r in rows)
    proven = by_proof.get("PROVEN_OFFICIAL", 0)
    target_ex = proven * sum(BANK_TARGET.values())
    target_qz = proven * QUIZ_TARGET_PER_NOTION
    grid: Dict[Tuple[str, str], Counter] = defaultdict(Counter)
    for r in rows:
        grid[(r["SUBJECT"], r["LEVEL"])][r["QA_STATUS"] if not r["NOTION_ID"] else r["PROOF_STATUS"]] += 1

    L = ["# PEDAGOGY_COVERAGE_REPORT", "",
         "> Généré par `python -m pedagogy.coverage` (déterministe). Matrice détaillée : "
         "`PEDAGOGY_COVERAGE_MATRIX.csv`.", "",
         "## Synthèse", "",
         f"- Notions au registre : **{len(notion_rows)}**",
         f"- PROVEN_OFFICIAL : **{proven}** · UNPROVEN : **{by_proof.get('UNPROVEN', 0)}** · "
         f"CONFLICT : **{by_proof.get('CONFLICT', 0)}** · DEPRECATED : **{by_proof.get('DEPRECATED', 0)}** · "
         f"PROVEN_INTERNAL : **{by_proof.get('PROVEN_INTERNAL', 0)}**",
         f"- Exercices en banque : **{len(reg.exercises)}** (cible théorique : {target_ex} = "
         f"{proven} notion(s) prouvée(s) × {sum(BANK_TARGET.values())})",
         f"- Questions de quiz : **{len(reg.quizzes)}** (cible théorique : {target_qz})",
         f"- Sources officielles attendues : **{len(reg.sources)}** dont récupérées : "
         f"**{sum(1 for s in reg.sources.values() if s.retrieval.value != 'EXPECTED')}**",
         "",
         "Tant qu'aucune source officielle n'est récupérée, **toutes les notions sont UNPROVEN** et "
         "la banque d'exercices reste volontairement vide (règle : contenu uniquement sur notion "
         "PROVEN_OFFICIAL).", "",
         "## Matière × niveau", "",
         "| Matière | " + " | ".join(lv.value for lv in LEVEL_ORDER) + " |",
         "|---|" + "---|" * len(LEVEL_ORDER)]
    for s in REPORTED_SUBJECTS:
        cells = []
        for lv in LEVEL_ORDER:
            c = grid[(s.value, lv.value)]
            if c.get("NOT_APPLICABLE"):
                cells.append("n/a")
            elif c.get("NO_NOTION"):
                cells.append("0")
            else:
                cells.append(f"{sum(c.values())} ({c.get('PROVEN_OFFICIAL', 0)} prouvées)")
        L.append(f"| {s.value} | " + " | ".join(cells) + " |")
    L += ["", "## Statut QA des lignes", "", "| QA_STATUS | Lignes |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(by_qa.items())]
    L += ["", "## Sources officielles attendues", "", "| Source | Récupération | Référence vérifiée | Matières | Niveaux |",
          "|---|---|---|---|---|"]
    for sid, src in sorted(reg.sources.items()):
        L.append(f"| `{sid}` | {src.retrieval.value} | {'oui' if src.reference_verified else 'non'} | "
                 f"{', '.join(x.value for x in src.subjects)} | {', '.join(x.value for x in src.levels)} |")
    if reg.load_errors:
        L += ["", "## Fichiers invalides (non chargés)", ""] + [f"- `{p}` : {r}" for p, r in reg.load_errors]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT)
    a = ap.parse_args(argv)
    reg = load_registry(a.data_dir)
    rows = build_rows(reg)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    (a.out_dir / "PEDAGOGY_COVERAGE_MATRIX.csv").write_text(to_csv(rows), encoding="utf-8")
    (a.out_dir / "PEDAGOGY_COVERAGE_REPORT.md").write_text(to_report(reg, rows), encoding="utf-8")
    print(f"{sum(1 for r in rows if r['NOTION_ID'])} notions, {len(rows)} lignes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
