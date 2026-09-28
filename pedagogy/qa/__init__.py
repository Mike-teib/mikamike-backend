"""
pedagogy.qa — QA de tout le registre pédagogique et rapport reproductible.

Usage : ``python -m pedagogy.qa [--data-dir DIR] [--out-dir DIR] [--source-root DIR]``

Étapes : chargement du registre, contrôles de notions (pedagogy.validators.notions),
validate_exercise / validate_quiz par objet, hors-programme, lexique de niveau
(heuristique), doublons. Écrit PEDAGOGY_QA_REPORT.json (déterministe : aucun horodatage,
issues triées) et PEDAGOGY_QA_REPORT.md.

Codes propres au runner :
  VALIDATOR_NOT_IMPLEMENTED  INFO     [validate_exercise|validate_quiz]  validateur encore stub.
  VALIDATOR_CRASH            ERROR    [objet]   exception inattendue d'un validateur.
  EXERCISE_OUT_OF_PROGRAM    ERROR    [exercise_id]  notion_id absente du registre.
  QUIZ_OUT_OF_PROGRAM        ERROR    [quiz_id]      notion_id absente du registre.
  EXERCISE_TOO_ADVANCED / QUIZ_TOO_ADVANCED  WARNING  terme du lexique au-dessus du niveau (heuristique).
  EXERCISE_TOO_SIMPLE / QUIZ_TOO_SIMPLE      WARNING  DISCOVERY lycée à chiffres isolés (heuristique).
  + codes de pedagogy.validators.notions et pedagogy.qa.duplicates.

RÈGLE DE CODE DE SORTIE (EXIT_CODE_RULE) :
  verdict = "FAIL" s'il existe au moins une issue BLOCKER ou ERROR, sinon "PASS".
  exit 0 si verdict PASS, exit 1 sinon. L'absence de preuve officielle attendue
  (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est de sévérité INFO et
  ne fait donc jamais échouer ; les WARNING (heuristiques) non plus. En revanche une notion
  qui SE DÉCLARE PROVEN_OFFICIAL sans preuve recalculable (PROOF_NOT_VERIFIABLE, BLOCKER)
  fait échouer. bank_ready (aucune notion PROVEN_OFFICIAL → False) n'influe pas sur le code.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import pedagogy
from pedagogy.issues import Issue, Severity
from pedagogy.models import ProofStatus, SourceRetrieval
from pedagogy.qa import duplicates, level_lexicon
from pedagogy.registry import DATA_DIR, REPO_ROOT, Registry, load_registry
from pedagogy.validators import exercise as exercise_validators
from pedagogy.validators import quiz as quiz_validators
from pedagogy.validators.notions import sort_issues, validate_registry_notions

GENERATED_BY = f"pedagogy.qa v{pedagogy.__version__}"
JSON_NAME = "PEDAGOGY_QA_REPORT.json"
MD_NAME = "PEDAGOGY_QA_REPORT.md"
EXIT_CODE_RULE = (
    "exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). "
    "L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) "
    "est INFO et ne fait jamais échouer ; les WARNING non plus."
)
UNPROVEN_CODES = frozenset({"NOTION_UNPROVEN", "NOTIONS_UNPROVEN_SUMMARY", "SOURCE_NOT_RETRIEVED"})
FAILING = frozenset({Severity.BLOCKER, Severity.ERROR})


def _sev(i: Issue) -> Severity:
    return Severity(i.severity)


def _run_validator(fn: Callable, obj, reg: Registry, obj_id: str, name: str, state: Dict[str, bool]) -> List[Issue]:
    if state.get(name):
        return []
    try:
        res = fn(obj, reg) or []
        return [Issue(i.code, Severity(i.severity), i.object_id, i.detail) for i in res]
    except NotImplementedError:
        state[name] = True
        return [Issue("VALIDATOR_NOT_IMPLEMENTED", Severity.INFO, name, "stub: controles non executes")]
    except Exception as exc:  # noqa: BLE001 — consigné en ERROR
        return [Issue("VALIDATOR_CRASH", Severity.ERROR, obj_id, f"{name}:{type(exc).__name__}:{str(exc)[:200]}")]


def collect_issues(reg: Registry, source_root: Optional[Path] = None) -> List[Issue]:
    issues: List[Issue] = list(validate_registry_notions(reg, root=source_root))
    state: Dict[str, bool] = {}

    for ex_id, ex in sorted(reg.exercises.items()):
        issues += _run_validator(exercise_validators.validate_exercise, ex, reg, ex_id, "validate_exercise", state)
        if ex.notion_id not in reg.notions:
            issues.append(Issue("EXERCISE_OUT_OF_PROGRAM", Severity.ERROR, ex_id, f"notion_inconnue:{ex.notion_id}"))
        text = " ".join([ex.statement, *ex.choices, ex.solution, *ex.step_by_step_solution, *ex.hints])
        for term, lv in level_lexicon.check_text_level(text, ex.subject, ex.level):
            issues.append(Issue("EXERCISE_TOO_ADVANCED", Severity.WARNING, ex_id,
                                f"terme:{term}:min={lv.value}:niveau={ex.level.value}:heuristique"))
        if level_lexicon.is_too_simple(ex.statement, ex.level, ex.difficulty):
            issues.append(Issue("EXERCISE_TOO_SIMPLE", Severity.WARNING, ex_id,
                                f"discovery_chiffres_isoles:niveau={ex.level.value}:heuristique"))

    for q_id, q in sorted(reg.quizzes.items()):
        issues += _run_validator(quiz_validators.validate_quiz, q, reg, q_id, "validate_quiz", state)
        if q.notion_id not in reg.notions:
            issues.append(Issue("QUIZ_OUT_OF_PROGRAM", Severity.ERROR, q_id, f"notion_inconnue:{q.notion_id}"))
        text = " ".join([q.question, *q.choices, q.explanation])
        for term, lv in level_lexicon.check_text_level(text, q.subject, q.level):
            issues.append(Issue("QUIZ_TOO_ADVANCED", Severity.WARNING, q_id,
                                f"terme:{term}:min={lv.value}:niveau={q.level.value}:heuristique"))
        if level_lexicon.is_too_simple(q.question, q.level, q.difficulty):
            issues.append(Issue("QUIZ_TOO_SIMPLE", Severity.WARNING, q_id,
                                f"discovery_chiffres_isoles:niveau={q.level.value}:heuristique"))

    issues += duplicates.find_exercise_duplicates(reg.exercises.values())
    issues += duplicates.find_quiz_duplicates(reg.quizzes.values())
    return sort_issues(issues)


def _locate(reg: Registry, object_id: str) -> Tuple[str, str]:
    for table in (reg.notions, reg.exercises, reg.quizzes):
        obj = table.get(object_id)
        if obj is not None:
            return obj.subject.value, obj.level.value
    return "-", "-"


def _rel(path: Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return str(p)


def _counter(values) -> Dict[str, int]:
    return dict(sorted(Counter(values).items()))


def build_report(reg: Registry, issues: List[Issue], data_dir: Path) -> Dict:
    rows = []
    for i in issues:
        subject, level = _locate(reg, i.object_id)
        rows.append({**i.as_dict(), "subject": subject, "level": level})
    notions = list(reg.notions.values())
    proven = sum(1 for n in notions if n.proof_status == ProofStatus.PROVEN_OFFICIAL)
    retrieved = sorted(s.source_id for s in reg.sources.values() if s.retrieval != SourceRetrieval.EXPECTED)
    sev = Counter(_sev(i).value for i in issues)
    failing = [i for i in issues if _sev(i) in FAILING]
    verdict = "FAIL" if failing else "PASS"
    codes = {i.code for i in issues}

    not_checked: List[str] = []
    if not retrieved:
        not_checked.append(
            "Aucune source officielle récupérée (toutes EXPECTED) : aucune provenance officielle n'a pu être "
            "vérifiée, ni la conformité des notions, niveaux et libellés aux programmes.")
    if proven == 0:
        not_checked.append("Aucune notion PROVEN_OFFICIAL : la banque d'exercices/quiz ne peut pas être alimentée (bank_ready=false).")
    if "VALIDATOR_NOT_IMPLEMENTED" in codes:
        stubs = sorted(i.object_id for i in issues if i.code == "VALIDATOR_NOT_IMPLEMENTED")
        not_checked.append(f"Validateurs non implémentés, contrôles par objet non exécutés : {', '.join(stubs)}.")
    if not reg.exercises:
        not_checked.append("Aucun exercice dans la banque : contrôles d'exercices non exercés.")
    if not reg.quizzes:
        not_checked.append("Aucune question de quiz dans la banque : contrôles de quiz non exercés.")
    if not notions:
        not_checked.append("Aucune notion chargée : contrôles du registre de notions non exercés.")
    not_checked.append(
        "Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; "
        "l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.")

    return {
        "schema_version": "1.0",
        "generated_by": GENERATED_BY,
        "data_dir": _rel(data_dir),
        "verdict": verdict,
        "bank_ready": proven > 0,
        "exit_code": 0 if verdict == "PASS" else 1,
        "exit_code_rule": EXIT_CODE_RULE,
        "totals": {
            "notions": {
                "total": len(notions),
                "by_proof_status": _counter(n.proof_status.value for n in notions),
                "by_subject": _counter(n.subject.value for n in notions),
                "by_level": _counter(n.level.value for n in notions),
                "by_publication_status": _counter(n.publication_status.value for n in notions),
            },
            "notion_files": len(reg.notion_files),
            "sources": {
                "total": len(reg.sources),
                "by_retrieval": _counter(s.retrieval.value for s in reg.sources.values()),
                "retrieved": retrieved,
            },
            "exercises": len(reg.exercises),
            "quizzes": len(reg.quizzes),
            "load_errors": len(reg.load_errors),
            "issues": len(issues),
            "blockers": sev.get("BLOCKER", 0),
            "errors": sev.get("ERROR", 0),
            "warnings": sev.get("WARNING", 0),
            "infos": sev.get("INFO", 0),
        },
        "counts": {
            "by_code": _counter(i.code for i in issues),
            "by_severity": _counter(_sev(i).value for i in issues),
            "by_subject": _counter(r["subject"] for r in rows),
            "by_level": _counter(r["level"] for r in rows),
        },
        "not_checked": not_checked,
        "issues": rows,
    }


def _table(header: Tuple[str, str], data: Dict[str, int]) -> List[str]:
    lines = [f"| {header[0]} | {header[1]} |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in data.items()] or ["| (aucun) | 0 |"]
    return lines


def render_markdown(report: Dict, top: int = 60) -> str:
    t = report["totals"]
    n = t["notions"]
    L: List[str] = [
        "# Rapport QA pédagogique MikaMike",
        "",
        f"Généré par `{report['generated_by']}` — données : `{report['data_dir']}`.",
        "",
        f"**Verdict : {report['verdict']}** (code de sortie {report['exit_code']}) — "
        f"bank_ready : **{str(report['bank_ready']).lower()}**",
        "",
        f"Règle : {report['exit_code_rule']}",
        "",
        "## Totaux",
        "",
        "| Élément | Nombre |",
        "|---|---:|",
        f"| Notions | {n['total']} |",
        f"| Fichiers de notions | {t['notion_files']} |",
        f"| Sources officielles déclarées | {t['sources']['total']} |",
        f"| Sources récupérées | {len(t['sources']['retrieved'])} |",
        f"| Exercices | {t['exercises']} |",
        f"| Quiz | {t['quizzes']} |",
        f"| Erreurs de chargement | {t['load_errors']} |",
        f"| Issues | {t['issues']} (BLOCKER {t['blockers']}, ERROR {t['errors']}, WARNING {t['warnings']}, INFO {t['infos']}) |",
        "",
        "### Notions par statut de preuve", "", *_table(("Statut", "Notions"), n["by_proof_status"]), "",
        "### Notions par matière", "", *_table(("Matière", "Notions"), n["by_subject"]), "",
        "### Notions par niveau", "", *_table(("Niveau", "Notions"), n["by_level"]), "",
        "## Issues", "",
        "### Par sévérité", "", *_table(("Sévérité", "Issues"), report["counts"]["by_severity"]), "",
        "### Par code", "", *_table(("Code", "Issues"), report["counts"]["by_code"]), "",
        "### Par matière", "", *_table(("Matière", "Issues"), report["counts"]["by_subject"]), "",
        "### Par niveau", "", *_table(("Niveau", "Issues"), report["counts"]["by_level"]), "",
        f"## Principales anomalies (BLOCKER / ERROR / WARNING, {top} premières)", "",
    ]
    serious = [r for r in report["issues"] if r["severity"] != "INFO"][:top]
    if serious:
        L += ["| Sévérité | Code | Objet | Détail |", "|---|---|---|---|"]
        L += [f"| {r['severity']} | {r['code']} | `{r['object_id']}` | {r['detail'].replace('|', '/')} |" for r in serious]
    else:
        L.append("Aucune anomalie BLOCKER, ERROR ou WARNING.")
    L += ["", "## Ce qui n'a PAS pu être vérifié", ""]
    L += [f"- {x}" for x in report["not_checked"]]
    L.append("")
    return "\n".join(L)


def run_qa(data_dir: Path = DATA_DIR, out_dir: Path = REPO_ROOT, source_root: Optional[Path] = None) -> Dict:
    data_dir = Path(data_dir)
    reg = load_registry(data_dir)
    issues = collect_issues(reg, source_root=source_root)
    report = build_report(reg, issues, data_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / JSON_NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / MD_NAME).write_text(render_markdown(report), encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m pedagogy.qa", description="QA du registre pédagogique MikaMike.")
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT)
    ap.add_argument("--source-root", type=Path, default=REPO_ROOT,
                    help="racine contre laquelle les local_path des sources sont résolus")
    args = ap.parse_args(argv)
    report = run_qa(args.data_dir, args.out_dir, args.source_root)
    t = report["totals"]
    print(f"{report['verdict']} bank_ready={str(report['bank_ready']).lower()} notions={t['notions']['total']} "
          f"exercises={t['exercises']} quizzes={t['quizzes']} blockers={t['blockers']} errors={t['errors']} "
          f"warnings={t['warnings']} infos={t['infos']} -> {Path(args.out_dir) / JSON_NAME}")
    return report["exit_code"]
