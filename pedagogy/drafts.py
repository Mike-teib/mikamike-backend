"""
drafts.py — Brouillons d'exercices et de quiz, en attente de revue humaine.

Règle MikaMike : aucun contenu n'est servi sur une notion qui n'est pas PROVEN_OFFICIAL ET
approuvée humainement (review_status=APPROVED), et chaque exercice est relu par un humain.
Les brouillons vivent donc HORS de la banque servie (pedagogy/data/bank) :

  pedagogy/data/drafts/exercises/*.json   {"exercises": [...]}
  pedagogy/data/drafts/quizzes/*.json     {"quizzes": [...]}

  python -m pedagogy.drafts check
      Valide tous les brouillons avec les validateurs de la banque (réponses vérifiées par
      SymPy / unités, QCM à bonne réponse unique, notation…). Seule l'anomalie attendue
      NOTION_NOT_APPROVED (notion prouvée mais pas encore relue) est tolérée. Code 1 sinon.
      Écrit reports/DRAFTS_QA_REPORT.json (déterministe, non versionné).

  python -m pedagogy.drafts review-plan
      Produit une file de relecture LECTURE SEULE : notion, niveau, titre, statuts,
      nombre d'exercices et de quiz encore dans les brouillons.

  python -m pedagogy.drafts approve --reviewer "Mike" --notion ID [...] --item ID [...]
      Outil de REVUE HUMAINE : passe les notions citées en review_status=APPROVED et les
      exercices/quiz cités en qa_status=HUMAN_APPROVED, puis les déplace vers la banque.
      N'est jamais appelé automatiquement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from pedagogy.issues import Issue, Severity
from pedagogy.models import (
    Exercise,
    GenerationOrigin,
    ProofStatus,
    PublicationStatus,
    QAStatus,
    QuizItem,
    ReviewStatus,
)
from pedagogy.registry import DATA_DIR, REPO_ROOT, Registry, load_registry

DRAFTS_DIR = DATA_DIR / "drafts"
EXPECTED_UNTIL_REVIEW = {"NOTION_NOT_APPROVED"}
ALLOWED_ORIGINS = {GenerationOrigin.MODEL_ASSISTED_DRAFT, GenerationOrigin.IMPORTED_LEGACY,
                   GenerationOrigin.HUMAN_AUTHORED}


def _load(kind: str, drafts_dir: Path) -> Tuple[List[Tuple[Path, object]], List[Tuple[str, str]]]:
    model = Exercise if kind == "exercises" else QuizItem
    items: List[Tuple[Path, object]] = []
    errors: List[Tuple[str, str]] = []
    for f in sorted((drafts_dir / kind).glob("*.json")):
        try:
            raw = json.loads(f.read_text(encoding="utf-8"))
            for obj in raw[kind]:
                try:
                    items.append((f, model.model_validate(obj)))
                except Exception as exc:  # noqa: BLE001 — on rapporte tout
                    oid = obj.get("exercise_id") or obj.get("quiz_id") or "?"
                    errors.append((f"{f.name}:{oid}", str(exc).splitlines()[0][:300]))
        except Exception as exc:  # noqa: BLE001
            errors.append((f.name, f"fichier_illisible:{exc}"[:300]))
    return items, errors


def _policy_issues(item, reg: Registry) -> List[Issue]:
    oid = getattr(item, "exercise_id", None) or getattr(item, "quiz_id")
    out: List[Issue] = []
    if item.generation_origin not in ALLOWED_ORIGINS:
        out.append(Issue("DRAFT_ORIGIN_FORBIDDEN", Severity.BLOCKER, oid, item.generation_origin.value))
    if item.qa_status not in (QAStatus.NOT_CHECKED, QAStatus.AUTO_PASSED):
        out.append(Issue("DRAFT_SELF_APPROVED", Severity.BLOCKER, oid, item.qa_status.value))
    if item.publication_status not in (PublicationStatus.DRAFT, PublicationStatus.READY_FOR_REVIEW):
        out.append(Issue("DRAFT_PUBLICATION_FORBIDDEN", Severity.BLOCKER, oid, item.publication_status.value))
    n = reg.notions.get(item.notion_id)
    if n is not None and n.proof_status != ProofStatus.PROVEN_OFFICIAL:
        out.append(Issue("DRAFT_ON_UNPROVEN_NOTION", Severity.BLOCKER, oid, n.proof_status.value))
    return out


def check(reg: Optional[Registry] = None, drafts_dir: Path = DRAFTS_DIR) -> Dict[str, object]:
    from pedagogy.validators.exercise import validate_exercise
    from pedagogy.validators.quiz import validate_quiz

    reg = reg or load_registry()
    ex, ex_err = _load("exercises", drafts_dir)
    qz, qz_err = _load("quizzes", drafts_dir)
    issues: List[Issue] = []
    for _, e in ex:
        issues += _policy_issues(e, reg) + list(validate_exercise(e, reg))
    for _, q in qz:
        issues += _policy_issues(q, reg) + list(validate_quiz(q, reg))
    ids = [e.exercise_id for _, e in ex] + [q.quiz_id for _, q in qz]
    for oid, c in Counter(ids).items():
        if c > 1:
            issues.append(Issue("DRAFT_DUPLICATE_ID", Severity.BLOCKER, oid, str(c)))
    blocking = [i for i in issues if i.code not in EXPECTED_UNTIL_REVIEW
                and i.severity in (Severity.BLOCKER, Severity.ERROR)]
    load_errors = ex_err + qz_err
    per_notion = Counter(e.notion_id for _, e in ex)
    per_notion_q = Counter(q.notion_id for _, q in qz)
    report = {
        "generated_by": "pedagogy.drafts check",
        "verdict": "PASS" if not blocking and not load_errors else "FAIL",
        "exercises": len(ex), "quizzes": len(qz),
        "notions_covered": len(set(per_notion) | set(per_notion_q)),
        "load_errors": [list(x) for x in sorted(load_errors)],
        "blocking": sorted([i.as_dict() for i in blocking], key=lambda d: (d["object_id"], d["code"])),
        "warnings": sorted([i.as_dict() for i in issues if i.severity == Severity.WARNING],
                           key=lambda d: (d["object_id"], d["code"])),
        "expected_until_review": sum(1 for i in issues if i.code in EXPECTED_UNTIL_REVIEW),
        "by_subject_level": {f"{k[0]}.{k[1]}": v for k, v in sorted(Counter(
            (e.subject.value, e.level.value) for _, e in ex).items())},
    }
    return report


def review_plan(reg: Optional[Registry] = None, drafts_dir: Path = DRAFTS_DIR) -> Dict[str, object]:
    """Construit une file de relecture déterministe sans modifier les brouillons."""
    reg = reg or load_registry()
    ex, ex_err = _load("exercises", drafts_dir)
    qz, qz_err = _load("quizzes", drafts_dir)
    ex_count = Counter(e.notion_id for _, e in ex)
    qz_count = Counter(q.notion_id for _, q in qz)
    meta: Dict[str, Tuple[str, str]] = {}
    for _, item in [*ex, *qz]:
        meta.setdefault(item.notion_id, (item.subject.value, item.level.value))

    rows: List[Dict[str, object]] = []
    for notion_id in sorted(set(ex_count) | set(qz_count), key=lambda nid: (*meta.get(nid, ("", "")), nid)):
        notion = reg.notions.get(notion_id)
        subject, level = meta.get(notion_id, ("", ""))
        proof = notion.proof_status.value if notion is not None else "UNKNOWN"
        review = notion.review_status.value if notion is not None else "UNKNOWN"
        exercises = ex_count[notion_id]
        quizzes = qz_count[notion_id]
        rows.append({
            "notion_id": notion_id,
            "subject": subject,
            "level": level,
            "title": notion.title if notion is not None else None,
            "proof_status": proof,
            "review_status": review,
            "exercises": exercises,
            "quizzes": quizzes,
            "items": exercises + quizzes,
            "ready_for_human_review": bool(
                notion is not None
                and notion.proof_status == ProofStatus.PROVEN_OFFICIAL
                and notion.review_status != ReviewStatus.APPROVED
            ),
        })

    by_subject_level = Counter((r["subject"], r["level"]) for r in rows)
    return {
        "generated_by": "pedagogy.drafts review-plan",
        "notions": len(rows),
        "exercises": len(ex),
        "quizzes": len(qz),
        "items": len(ex) + len(qz),
        "load_errors": [list(x) for x in sorted(ex_err + qz_err)],
        "ready_for_human_review": sum(1 for r in rows if r["ready_for_human_review"]),
        "by_subject_level": {
            f"{subject}.{level}": count
            for (subject, level), count in sorted(by_subject_level.items())
        },
        "queue": rows,
    }


def _permute_quiz_for_bank(obj: Dict[str, object]) -> Dict[str, object]:
    """Permutation déterministe des choix, avec remappage de tous les index associés."""
    choices = list(obj.get("choices") or [])
    if len(choices) < 2:
        return obj
    quiz_id = str(obj.get("quiz_id") or "")
    order = sorted(
        range(len(choices)),
        key=lambda i: hashlib.sha256(f"{quiz_id}|{i}".encode("utf-8")).digest(),
    )
    old_to_new = {old: new for new, old in enumerate(order)}
    out = dict(obj)
    out["choices"] = [choices[i] for i in order]
    out["correct_answer"] = old_to_new[int(obj["correct_answer"])]
    for field in ("distractor_rationale", "common_error_target"):
        raw = obj.get(field) or {}
        if isinstance(raw, dict):
            out[field] = {str(old_to_new[int(k)]): v for k, v in raw.items()}
    return out


def approve(reviewer: str, notion_ids: Sequence[str], item_ids: Sequence[str],
            data_dir: Path = DATA_DIR) -> Dict[str, int]:
    """Revue humaine explicite. Ne jamais appeler depuis un pipeline automatique."""
    if not reviewer.strip():
        raise ValueError("relecteur_obligatoire")
    done = {"notions": 0, "exercises": 0, "quizzes": 0}
    wanted = set(notion_ids)
    for f in sorted((data_dir / "notions").rglob("*.json")):
        raw = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for n in raw["notions"]:
            if n["notion_id"] in wanted:
                if n["proof_status"] != "PROVEN_OFFICIAL":
                    raise ValueError(f"approbation_refusee_notion_non_prouvee:{n['notion_id']}")
                n["review_status"] = "APPROVED"
                n["provenance_note"] = (n.get("provenance_note", "") + f" Revue humaine : APPROVED par {reviewer}.")[:2000]
                done["notions"] += 1
                changed = True
        if changed:
            f.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wanted_items = set(item_ids)
    for kind, key in (("exercises", "exercise_id"), ("quizzes", "quiz_id")):
        bank = data_dir / "bank" / kind
        bank.mkdir(parents=True, exist_ok=True)
        for f in sorted((data_dir / "drafts" / kind).glob("*.json")):
            raw = json.loads(f.read_text(encoding="utf-8"))
            keep, moved = [], []
            for obj in raw[kind]:
                (moved if obj[key] in wanted_items else keep).append(obj)
            if not moved:
                continue
            for i, obj in enumerate(moved):
                if kind == "quizzes":
                    obj = _permute_quiz_for_bank(obj)
                    moved[i] = obj
                obj["qa_status"] = "HUMAN_APPROVED"
                obj["publication_status"] = "APPROVED"
            target = bank / f.name
            existing = json.loads(target.read_text(encoding="utf-8"))[kind] if target.exists() else []
            target.write_text(json.dumps({kind: existing + moved}, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
            f.write_text(json.dumps({kind: keep}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            done[kind] += len(moved)
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pedagogy.drafts")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--out", type=Path, default=REPO_ROOT / "reports" / "DRAFTS_QA_REPORT.json")
    p = sub.add_parser("review-plan")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "reports" / "DRAFTS_REVIEW_PLAN.json")
    a = sub.add_parser("approve")
    a.add_argument("--reviewer", required=True)
    a.add_argument("--notion", nargs="*", default=[])
    a.add_argument("--item", nargs="*", default=[])
    args = ap.parse_args(argv)
    if args.cmd == "check":
        rep = check()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{rep['verdict']} exercices={rep['exercises']} quiz={rep['quizzes']} "
              f"notions={rep['notions_covered']} bloquants={len(rep['blocking'])} "
              f"erreurs_chargement={len(rep['load_errors'])} avertissements={len(rep['warnings'])}")
        for d in rep["blocking"][:30]:
            print(f"  {d['severity']} {d['code']} {d['object_id']} {d['detail'][:120]}")
        for d in rep["load_errors"][:10]:
            print(f"  LOAD {d[0]} {d[1][:160]}")
        return 0 if rep["verdict"] == "PASS" else 1
    if args.cmd == "review-plan":
        rep = review_plan()
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"REVIEW_PLAN notions={rep['notions']} exercices={rep['exercises']} "
            f"quiz={rep['quizzes']} prêts={rep['ready_for_human_review']}"
        )
        if rep["load_errors"]:
            for row in rep["load_errors"][:10]:
                print(f"  LOAD {row[0]} {row[1][:160]}")
            return 1
        return 0
    print(approve(args.reviewer, args.notion, args.item))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
