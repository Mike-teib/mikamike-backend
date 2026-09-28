"""Tests du runner `python -m pedagogy.qa` (données fictives, validateurs d'objets simulés)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys

import pytest

import pedagogy.qa as qa
from pedagogy.issues import Issue, Severity
from pedagogy.registry import REPO_ROOT

try:
    from tests_pedagogy.pdf_fixture import make_pdf
    from tests_pedagogy.qa_fixtures import exercise_dict, notion_dict, notion_file, quiz_dict, source_dict, write_data_dir
except ImportError:  # pragma: no cover
    from pdf_fixture import make_pdf
    from qa_fixtures import exercise_dict, notion_dict, notion_file, quiz_dict, source_dict, write_data_dir


def _stub(*_a, **_k):
    raise NotImplementedError


@pytest.fixture
def stub_validators(monkeypatch):
    """Validateurs d'objets (agent D) remplacés par des stubs : tests indépendants de leur état."""
    monkeypatch.setattr(qa.exercise_validators, "validate_exercise", _stub)
    monkeypatch.setattr(qa.quiz_validators, "validate_quiz", _stub)


def _codes(report):
    return report["counts"]["by_code"]


def _issues(report, code):
    return [r for r in report["issues"] if r["code"] == code]


def _unproven_data(tmp_path):
    nf = notion_file("MATHS", "6E", [notion_dict("Fractions simples"), notion_dict("Aires")])
    return write_data_dir(tmp_path, {"maths/6e.json": nf}, [source_dict()])


def test_empty_data_dir(tmp_path, stub_validators):
    data = tmp_path / "vide"
    data.mkdir()
    report = qa.run_qa(data, tmp_path / "out")
    assert report["verdict"] == "PASS" and report["exit_code"] == 0
    assert report["bank_ready"] is False
    assert report["issues"] == []
    assert any("Aucune notion chargée" in x for x in report["not_checked"])


def test_unproven_only_passes_with_exit_0(tmp_path, stub_validators):
    data = _unproven_data(tmp_path)
    out = tmp_path / "out"
    assert qa.main(["--data-dir", str(data), "--out-dir", str(out)]) == 0
    report = json.loads((out / qa.JSON_NAME).read_text(encoding="utf-8"))
    assert report["verdict"] == "PASS" and report["bank_ready"] is False
    assert _codes(report) == {"NOTIONS_UNPROVEN_SUMMARY": 1, "NOTION_UNPROVEN": 2, "SOURCE_NOT_RETRIEVED": 2}
    t = report["totals"]
    assert t["notions"]["total"] == 2
    assert t["notions"]["by_proof_status"] == {"UNPROVEN": 2}
    assert t["notions"]["by_subject"] == {"MATHS": 2} and t["notions"]["by_level"] == {"6E": 2}
    assert t["sources"]["by_retrieval"] == {"EXPECTED": 1}
    assert report["counts"]["by_subject"] == {"-": 1, "MATHS": 4}
    assert any("Aucune source officielle récupérée" in x for x in report["not_checked"])
    md = (out / qa.MD_NAME).read_text(encoding="utf-8")
    assert "**Verdict : PASS**" in md and "Ce qui n'a PAS pu être vérifié" in md
    assert "generated_by" in report and "timestamp" not in json.dumps(report).lower()


def test_report_is_byte_deterministic(tmp_path, stub_validators):
    nd = [notion_dict("Fractions simples", learning_objectives=()), notion_dict("Aires", prerequisites=("MATHS.6E.NC.x-y",))]
    data = write_data_dir(
        tmp_path, {"maths/6e.json": notion_file("MATHS", "6E", nd)}, [source_dict()],
        exercises=[exercise_dict("EX.b.1", nd[0]["notion_id"], "Calculer la dérivée de 3/4."),
                   exercise_dict("EX.b.2", nd[0]["notion_id"], "Calculer la dérivée de 3/4 !")],
        quizzes=[quiz_dict("QZ.b.1", nd[1]["notion_id"], "Quelle est l'aire d'un carré de côté 2 ?")])
    qa.run_qa(data, tmp_path / "o1")
    qa.run_qa(data, tmp_path / "o2")
    for name in (qa.JSON_NAME, qa.MD_NAME):
        assert (tmp_path / "o1" / name).read_bytes() == (tmp_path / "o2" / name).read_bytes()


def test_bank_items_checks(tmp_path, stub_validators):
    n6 = notion_dict("Fractions simples")
    n2 = notion_dict("Fonctions affines", level="2NDE")
    src = source_dict(levels=("6E", "2NDE"))
    data = write_data_dir(
        tmp_path,
        {"maths/6e.json": notion_file("MATHS", "6E", [n6]), "maths/2nde.json": notion_file("MATHS", "2NDE", [n2])},
        [src],
        exercises=[
            exercise_dict("EX.r.1", n6["notion_id"], "Calculer la dérivée de la fonction f."),          # trop avancé
            exercise_dict("EX.r.2", "MATHS.6E.NC.hors-programme", "Tracer une droite graduée."),      # hors programme
            exercise_dict("EX.r.3", n2["notion_id"], "Calculer 3 + 4.", level="2NDE", difficulty="DISCOVERY"),  # trop simple
            exercise_dict("EX.r.4", n6["notion_id"], "Calculer la dérivée de la fonction f !"),        # doublon exact de r.1
        ],
        quizzes=[
            quiz_dict("QZ.r.1", n6["notion_id"], "Quel est le discriminant de x² + 1 ?"),              # trop avancé
            quiz_dict("QZ.r.2", "MATHS.6E.NC.absente", "Combien de côtés a un carré ?"),              # hors programme
            quiz_dict("QZ.r.3", n2["notion_id"], "Combien font 2 + 5 ?", level="2NDE", difficulty="DISCOVERY"),
        ],
    )
    report = qa.run_qa(data, tmp_path / "out")
    assert [r["object_id"] for r in _issues(report, "EXERCISE_OUT_OF_PROGRAM")] == ["EX.r.2"]
    assert [r["object_id"] for r in _issues(report, "QUIZ_OUT_OF_PROGRAM")] == ["QZ.r.2"]
    assert {r["object_id"] for r in _issues(report, "EXERCISE_TOO_ADVANCED")} == {"EX.r.1", "EX.r.4"}
    assert [r["object_id"] for r in _issues(report, "EXERCISE_TOO_SIMPLE")] == ["EX.r.3"]
    assert [r["object_id"] for r in _issues(report, "QUIZ_TOO_ADVANCED")] == ["QZ.r.1"]
    assert [r["object_id"] for r in _issues(report, "QUIZ_TOO_SIMPLE")] == ["QZ.r.3"]
    assert [r["object_id"] for r in _issues(report, "EXERCISE_DUPLICATE_EXACT")] == ["EX.r.4"]
    for code in ("EXERCISE_TOO_ADVANCED", "EXERCISE_TOO_SIMPLE", "QUIZ_TOO_ADVANCED", "QUIZ_TOO_SIMPLE"):
        assert all(r["severity"] == "WARNING" for r in _issues(report, code))
    # un seul VALIDATOR_NOT_IMPLEMENTED par validateur, en INFO
    vni = _issues(report, "VALIDATOR_NOT_IMPLEMENTED")
    assert sorted(r["object_id"] for r in vni) == ["validate_exercise", "validate_quiz"]
    assert all(r["severity"] == "INFO" for r in vni)
    assert report["verdict"] == "FAIL" and report["exit_code"] == 1
    tr = _issues(report, "EXERCISE_TOO_SIMPLE")[0]
    assert (tr["subject"], tr["level"]) == ("MATHS", "2NDE")
    # tri : BLOCKER, ERROR, WARNING, INFO
    order = {"BLOCKER": 0, "ERROR": 1, "WARNING": 2, "INFO": 3}
    ranks = [order[r["severity"]] for r in report["issues"]]
    assert ranks == sorted(ranks)


def test_validator_results_and_crash(tmp_path, monkeypatch):
    n6 = notion_dict("Fractions simples")
    data = write_data_dir(tmp_path, {"m.json": notion_file("MATHS", "6E", [n6])}, [source_dict()],
                          exercises=[exercise_dict("EX.v.1", n6["notion_id"], "Comparer deux fractions simples.")],
                          quizzes=[quiz_dict("QZ.v.1", n6["notion_id"], "Quelle fraction est la plus grande ?")])

    def fake_ex(ex, reg):
        return [Issue("NOTION_NOT_PROVEN", Severity.BLOCKER, ex.exercise_id, "test")]

    def crash(q, reg):
        raise ValueError("boum")

    monkeypatch.setattr(qa.exercise_validators, "validate_exercise", fake_ex)
    monkeypatch.setattr(qa.quiz_validators, "validate_quiz", crash)
    report = qa.run_qa(data, tmp_path / "out")
    assert _issues(report, "NOTION_NOT_PROVEN")[0]["severity"] == "BLOCKER"
    crash_rows = _issues(report, "VALIDATOR_CRASH")
    assert [r["object_id"] for r in crash_rows] == ["QZ.v.1"] and crash_rows[0]["severity"] == "ERROR"
    assert "VALIDATOR_NOT_IMPLEMENTED" not in _codes(report)
    assert report["totals"]["blockers"] == 1 and report["exit_code"] == 1


def test_load_error_fails(tmp_path, stub_validators):
    data = write_data_dir(tmp_path, {"maths/6e.json": "{cassé"}, [source_dict()])
    report = qa.run_qa(data, tmp_path / "out")
    assert _codes(report).get("LOAD_ERROR") == 1
    assert report["verdict"] == "FAIL" and report["exit_code"] == 1


def test_bank_ready_with_verified_proof(tmp_path, stub_validators):
    wording = "Comparer, ranger et encadrer des fractions simples"
    pdf = make_pdf(["Garde", f"Nombres\n{wording}."])
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "p.pdf").write_bytes(pdf)
    sha = hashlib.sha256(pdf).hexdigest()
    src = source_dict("SRC-PDF", retrieval="RETRIEVED", local_path="src/p.pdf", sha256=sha)
    nd = notion_dict("Fractions simples", source_id="SRC-PDF", proof_status="PROVEN_OFFICIAL",
                     official_wording=wording, source_page_or_section="2", source_sha256=sha)
    data = write_data_dir(tmp_path, {"m.json": notion_file("MATHS", "6E", [nd])}, [src])
    report = qa.run_qa(data, tmp_path / "out", source_root=tmp_path)
    assert report["bank_ready"] is True
    assert report["verdict"] == "PASS" and report["issues"] == []
    assert report["totals"]["sources"]["retrieved"] == ["SRC-PDF"]
    # même registre, mais racine des sources erronée → preuve non vérifiable
    report2 = qa.run_qa(data, tmp_path / "out2", source_root=tmp_path / "ailleurs")
    assert "PROOF_NOT_VERIFIABLE" in _codes(report2) and report2["exit_code"] == 1


def test_cli_module_entrypoint(tmp_path):
    data = _unproven_data(tmp_path)
    out = tmp_path / "cli"
    proc = subprocess.run([sys.executable, "-m", "pedagogy.qa", "--data-dir", str(data), "--out-dir", str(out)],
                          cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
    # Pas d'exercice ni de quiz : les validateurs d'objets ne sont pas sollicités.
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert proc.stdout.startswith("PASS")
    assert (out / qa.JSON_NAME).is_file() and (out / qa.MD_NAME).is_file()
