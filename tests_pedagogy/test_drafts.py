"""Circuit des brouillons : validation stricte, jamais d'auto-approbation, revue humaine explicite."""

import json
import shutil

import pytest

from pedagogy.drafts import DRAFTS_DIR, approve, check
from pedagogy.registry import DATA_DIR, load_registry

EX = DRAFTS_DIR / "exercises" / "_EXEMPLE_MATHS_CE1.json"
QZ = DRAFTS_DIR / "quizzes" / "_EXEMPLE_MATHS_CE1.json"


@pytest.fixture()
def drafts(tmp_path):
    d = tmp_path / "drafts"
    (d / "exercises").mkdir(parents=True)
    (d / "quizzes").mkdir(parents=True)
    shutil.copy(EX, d / "exercises" / EX.name)
    shutil.copy(QZ, d / "quizzes" / QZ.name)
    return d


def _edit(path, kind, **changes):
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw[kind][0].update(changes)
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")


def test_repository_drafts_pass():
    rep = check()
    assert rep["verdict"] == "PASS", rep["blocking"][:5]
    assert rep["exercises"] >= 1 and rep["quizzes"] >= 1


def test_reference_example_passes_with_only_expected_issue(drafts):
    rep = check(load_registry(), drafts)
    assert rep["verdict"] == "PASS"
    assert rep["expected_until_review"] == 2 and not rep["warnings"]


def test_wrong_answers_are_blocking(drafts):
    _edit(drafts / "quizzes" / QZ.name, "quizzes", reference_answer="37")
    _edit(drafts / "exercises" / EX.name, "exercises", expected_answer={"kind": "MATH_EXPR", "value": "27"})
    rep = check(load_registry(), drafts)
    codes = {d["code"] for d in rep["blocking"]}
    assert rep["verdict"] == "FAIL" and {"CORRECT_ANSWER_WRONG", "SOLUTION_INCONSISTENT"} <= codes


@pytest.mark.parametrize("field,value,code", [
    ("qa_status", "HUMAN_APPROVED", "DRAFT_SELF_APPROVED"),
    ("publication_status", "APPROVED", "DRAFT_PUBLICATION_FORBIDDEN"),
])
def test_drafts_cannot_self_approve(drafts, field, value, code):
    _edit(drafts / "exercises" / EX.name, "exercises", **{field: value})
    rep = check(load_registry(), drafts)
    assert code in {d["code"] for d in rep["blocking"]}


def test_duplicate_ids_blocked(drafts):
    raw = json.loads((drafts / "exercises" / EX.name).read_text(encoding="utf-8"))
    raw["exercises"].append(raw["exercises"][0])
    (drafts / "exercises" / EX.name).write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    assert "DRAFT_DUPLICATE_ID" in {d["code"] for d in check(load_registry(), drafts)["blocking"]}


def test_approve_is_explicit_and_moves_to_bank(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "notions" / "MATHS", data / "notions" / "MATHS")
    (data / "drafts" / "exercises").mkdir(parents=True)
    (data / "drafts" / "quizzes").mkdir(parents=True)
    shutil.copy(EX, data / "drafts" / "exercises" / EX.name)
    shutil.copy(QZ, data / "drafts" / "quizzes" / QZ.name)
    ex = json.loads(EX.read_text(encoding="utf-8"))["exercises"][0]
    with pytest.raises(ValueError):
        approve("  ", [ex["notion_id"]], [], data)
    done = approve("Mike", [ex["notion_id"]], [ex["exercise_id"]], data)
    assert done == {"notions": 1, "exercises": 1, "quizzes": 0}
    bank = json.loads((data / "bank" / "exercises" / EX.name).read_text(encoding="utf-8"))["exercises"]
    assert bank[0]["qa_status"] == "HUMAN_APPROVED" and bank[0]["publication_status"] == "APPROVED"
    left = json.loads((data / "drafts" / "exercises" / EX.name).read_text(encoding="utf-8"))["exercises"]
    assert left == []
    notions = json.loads((data / "notions" / "MATHS" / "CE1.json").read_text(encoding="utf-8"))["notions"]
    n = next(x for x in notions if x["notion_id"] == ex["notion_id"])
    assert n["review_status"] == "APPROVED" and "Mike" in n["provenance_note"]
