"""Circuit des brouillons : validation stricte, jamais d'auto-approbation, revue humaine explicite."""

import json
import shutil

import pytest

from pedagogy.drafts import DRAFTS_DIR, _permute_quiz_for_bank, approve, check, review_plan
from pedagogy.registry import DATA_DIR, load_registry

EX = DRAFTS_DIR / "exercises" / "_EXEMPLE_MATHS_CE1.json"
QZ = DRAFTS_DIR / "quizzes" / "_EXEMPLE_MATHS_CE1.json"
EX_NAME = "TEST_MATHS_CE1.json"
QZ_NAME = "TEST_MATHS_CE1.json"


@pytest.fixture()
def drafts(tmp_path):
    d = tmp_path / "drafts"
    (d / "exercises").mkdir(parents=True)
    (d / "quizzes").mkdir(parents=True)
    shutil.copy(EX, d / "exercises" / EX_NAME)
    shutil.copy(QZ, d / "quizzes" / QZ_NAME)
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
    _edit(drafts / "quizzes" / QZ_NAME, "quizzes", reference_answer="37")
    _edit(drafts / "exercises" / EX_NAME, "exercises", expected_answer={"kind": "MATH_EXPR", "value": "27"})
    rep = check(load_registry(), drafts)
    codes = {d["code"] for d in rep["blocking"]}
    assert rep["verdict"] == "FAIL" and {"CORRECT_ANSWER_WRONG", "SOLUTION_INCONSISTENT"} <= codes


@pytest.mark.parametrize("field,value,code", [
    ("qa_status", "HUMAN_APPROVED", "DRAFT_SELF_APPROVED"),
    ("publication_status", "APPROVED", "DRAFT_PUBLICATION_FORBIDDEN"),
])
def test_drafts_cannot_self_approve(drafts, field, value, code):
    _edit(drafts / "exercises" / EX_NAME, "exercises", **{field: value})
    rep = check(load_registry(), drafts)
    assert code in {d["code"] for d in rep["blocking"]}


def test_duplicate_ids_blocked(drafts):
    raw = json.loads((drafts / "exercises" / EX_NAME).read_text(encoding="utf-8"))
    raw["exercises"].append(raw["exercises"][0])
    (drafts / "exercises" / EX_NAME).write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    assert "DRAFT_DUPLICATE_ID" in {d["code"] for d in check(load_registry(), drafts)["blocking"]}


def test_approve_is_explicit_and_moves_to_bank(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "notions" / "MATHS", data / "notions" / "MATHS")
    (data / "drafts" / "exercises").mkdir(parents=True)
    (data / "drafts" / "quizzes").mkdir(parents=True)
    shutil.copy(EX, data / "drafts" / "exercises" / EX_NAME)
    shutil.copy(QZ, data / "drafts" / "quizzes" / QZ_NAME)
    ex = json.loads(EX.read_text(encoding="utf-8"))["exercises"][0]
    with pytest.raises(ValueError):
        approve("  ", [ex["notion_id"]], [], data)
    done = approve("Mike", [ex["notion_id"]], [ex["exercise_id"]], data)
    assert done == {"notions": 1, "exercises": 1, "quizzes": 0}
    bank = json.loads((data / "bank" / "exercises" / EX_NAME).read_text(encoding="utf-8"))["exercises"]
    assert bank[0]["qa_status"] == "HUMAN_APPROVED" and bank[0]["publication_status"] == "APPROVED"
    left = json.loads((data / "drafts" / "exercises" / EX_NAME).read_text(encoding="utf-8"))["exercises"]
    assert left == []
    notions = json.loads((data / "notions" / "MATHS" / "CE1.json").read_text(encoding="utf-8"))["notions"]
    n = next(x for x in notions if x["notion_id"] == ex["notion_id"])
    assert n["review_status"] == "APPROVED" and "Mike" in n["provenance_note"]


def test_quiz_approval_permutes_choices_without_breaking_key(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "notions" / "MATHS", data / "notions" / "MATHS")
    (data / "drafts" / "exercises").mkdir(parents=True)
    (data / "drafts" / "quizzes").mkdir(parents=True)
    shutil.copy(QZ, data / "drafts" / "quizzes" / QZ_NAME)
    q = json.loads(QZ.read_text(encoding="utf-8"))["quizzes"][0]

    done = approve("Mike", [q["notion_id"]], [q["quiz_id"]], data)
    assert done == {"notions": 1, "exercises": 0, "quizzes": 1}

    bank = json.loads((data / "bank" / "quizzes" / QZ_NAME).read_text(encoding="utf-8"))["quizzes"][0]
    assert set(bank["choices"]) == set(q["choices"])
    assert bank["choices"][bank["correct_answer"]] == q["reference_answer"]
    assert str(bank["correct_answer"]) not in bank.get("distractor_rationale", {})
    assert bank["qa_status"] == "HUMAN_APPROVED"
    assert bank["publication_status"] == "APPROVED"


def test_quiz_permutation_is_deterministic_and_not_fixed_to_one_position():
    positions = set()
    for i in range(20):
        obj = {
            "quiz_id": f"QZ.TEST.demo.q{i:02d}",
            "choices": ["bonne", "d1", "d2", "d3"],
            "correct_answer": 0,
            "distractor_rationale": {"1": "d1", "2": "d2", "3": "d3"},
            "common_error_target": {},
        }
        first = _permute_quiz_for_bank(obj)
        second = _permute_quiz_for_bank(obj)
        assert first == second
        assert first["choices"][first["correct_answer"]] == "bonne"
        positions.add(first["correct_answer"])
    assert len(positions) >= 3


def test_review_plan_is_read_only_and_counts_example(drafts):
    before_ex = (drafts / "exercises" / EX_NAME).read_bytes()
    before_qz = (drafts / "quizzes" / QZ_NAME).read_bytes()

    rep = review_plan(load_registry(), drafts)

    assert rep["notions"] == 1
    assert rep["exercises"] == 1
    assert rep["quizzes"] == 1
    assert rep["items"] == 2
    assert not rep["load_errors"]
    row = rep["queue"][0]
    assert row["exercises"] == 1 and row["quizzes"] == 1
    assert row["proof_status"] == "PROVEN_OFFICIAL"
    assert row["review_status"] == "NOT_REVIEWED"
    assert row["ready_for_human_review"] is True

    assert (drafts / "exercises" / EX_NAME).read_bytes() == before_ex
    assert (drafts / "quizzes" / QZ_NAME).read_bytes() == before_qz


def test_repository_review_plan_covers_all_current_drafts():
    rep = review_plan()
    assert rep["exercises"] >= 1814
    assert rep["quizzes"] >= 960
    assert rep["notions"] >= 108
    assert rep["items"] == rep["exercises"] + rep["quizzes"]
    assert not rep["load_errors"]


def test_repository_example_fixtures_are_excluded_from_real_drafts(tmp_path):
    d = tmp_path / "drafts"
    (d / "exercises").mkdir(parents=True)
    (d / "quizzes").mkdir(parents=True)
    shutil.copy(EX, d / "exercises" / EX.name)
    shutil.copy(QZ, d / "quizzes" / QZ.name)

    rep = check(load_registry(), d)
    plan = review_plan(load_registry(), d)
    assert rep["exercises"] == 0 and rep["quizzes"] == 0
    assert plan["exercises"] == 0 and plan["quizzes"] == 0
    assert plan["queue"] == []


def test_approve_missing_item_does_not_mutate_notion(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "notions" / "MATHS", data / "notions" / "MATHS")
    (data / "drafts" / "exercises").mkdir(parents=True)
    (data / "drafts" / "quizzes").mkdir(parents=True)
    shutil.copy(EX, data / "drafts" / "exercises" / EX_NAME)
    ex = json.loads(EX.read_text(encoding="utf-8"))["exercises"][0]
    notion_file = data / "notions" / "MATHS" / "CE1.json"
    before = notion_file.read_bytes()

    with pytest.raises(ValueError, match="item_inconnu"):
        approve("Mike", [ex["notion_id"]], ["EX.INEXISTANT"], data)

    assert notion_file.read_bytes() == before
    assert not (data / "bank").exists()


def test_approve_item_requires_notion_approval_in_same_batch(tmp_path):
    data = tmp_path / "data"
    shutil.copytree(DATA_DIR / "notions" / "MATHS", data / "notions" / "MATHS")
    (data / "drafts" / "exercises").mkdir(parents=True)
    (data / "drafts" / "quizzes").mkdir(parents=True)
    shutil.copy(EX, data / "drafts" / "exercises" / EX_NAME)
    ex = json.loads(EX.read_text(encoding="utf-8"))["exercises"][0]
    draft_file = data / "drafts" / "exercises" / EX_NAME
    before = draft_file.read_bytes()

    with pytest.raises(ValueError, match="item_sur_notion_non_approuvee"):
        approve("Mike", [], [ex["exercise_id"]], data)

    assert draft_file.read_bytes() == before
    assert not (data / "bank").exists()
