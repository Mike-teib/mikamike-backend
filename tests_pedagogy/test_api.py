"""API pédagogique en lecture seule : filtres, pagination, règles de service."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pedagogy.api import build_router
from pedagogy.models import (
    AnswerKind,
    Cycle,
    DifficultyBand,
    Exercise,
    ExerciseType,
    ExpectedAnswer,
    GenerationOrigin,
    Level,
    Notion,
    ProofStatus,
    QAStatus,
    QuizItem,
    SourceType,
    Subject,
    make_notion_id,
    normalize_title,
)
from pedagogy.registry import Registry


def _notion(title, proven):
    extra = dict(source_type=SourceType.OFFICIAL_BO, source_id="SRC-FICTIF", source_page_or_section="2",
                 official_wording=f"[FICTIF] {title}", source_sha256="a" * 64,
                 proof_status=ProofStatus.PROVEN_OFFICIAL) if proven else {}
    base = dict(notion_id=make_notion_id(Subject.MATHS, Level.QUATRIEME, "NC", title), subject=Subject.MATHS,
                level=Level.QUATRIEME, cycle=Cycle.CYCLE_4, school_year="2025-2026",
                official_program_version="[FICTIF]", domain="Nombres et calculs", domain_code="NC",
                chapter="[FICTIF]", title=title, normalized_title=normalize_title(title), difficulty=2,
                source_type=SourceType.CANDIDATE_UNVERIFIED, source_title="[FICTIF]", source_url_or_ref="[FICTIF]")
    base.update(extra)
    return Notion(**base)


def _ex(ex_id, notion, origin=GenerationOrigin.MODEL_ASSISTED_DRAFT, qa=QAStatus.AUTO_PASSED):
    return Exercise(exercise_id=ex_id, notion_id=notion.notion_id, subject=notion.subject, level=notion.level,
                    difficulty=DifficultyBand.APPLICATION, exercise_type=ExerciseType.CALCULATION,
                    statement="[FICTIF] Calculer 10^2.", expected_answer=ExpectedAnswer(kind=AnswerKind.MATH_EXPR, value="100"),
                    solution="10^2 = 100", step_by_step_solution=("10^2 = 10 × 10 = 100",), hints=("Multiplie 10 par 10.",),
                    remediation="Revoir la définition d'une puissance.", estimated_time_min=2,
                    skills_tested=("CALCULER",), source_notions=(notion.notion_id,), generation_origin=origin, qa_status=qa)


@pytest.fixture()
def client():
    p, u = _notion("Puissances de 10", True), _notion("Calcul littéral", False)
    reg = Registry(notions={p.notion_id: p, u.notion_id: u})
    reg.exercises = {e.exercise_id: e for e in [
        _ex("EX.ok.1", p),
        _ex("EX.unproven.1", u),                                # notion non prouvée → jamais servi
        _ex("EX.fixture.1", p, origin=GenerationOrigin.FIXTURE_TEST),  # fixture → jamais servie
        _ex("EX.notqa.1", p, qa=QAStatus.NOT_CHECKED),           # QA non passée → jamais servi
    ]}
    reg.quizzes = {"QZ.ok.1": QuizItem(
        quiz_id="QZ.ok.1", notion_id=p.notion_id, subject=p.subject, level=p.level,
        question="[FICTIF] Que vaut 10^2 ?", choices=("100", "20", "12"), correct_answer=0, reference_answer="100",
        answer_kind=AnswerKind.MATH_EXPR, explanation="10^2 = 10 × 10 = 100.", difficulty=DifficultyBand.DISCOVERY,
        distractor_rationale={1: "10 × 2", 2: "10 + 2"}, generation_origin=GenerationOrigin.MODEL_ASSISTED_DRAFT,
        qa_status=QAStatus.AUTO_PASSED)}
    app = FastAPI()
    app.include_router(build_router(reg))
    return TestClient(app), p, u


def test_subjects_levels(client):
    c, _, _ = client
    subs = {s["subject"]: s["levels"] for s in c.get("/pedagogy/subjects").json()["items"]}
    assert "6E" not in subs["PHYSIQUE_CHIMIE"] and subs["SCIENCES_TECHNOLOGIE"] == ["6E"]
    assert c.get("/pedagogy/levels").json()["items"] == ["6E", "5E", "4E", "3E", "2NDE", "1RE", "TLE"]


def test_notions_prouvees_par_defaut(client):
    c, p, u = client
    ids = [n["notion_id"] for n in c.get("/pedagogy/notions").json()["items"]]
    assert ids == [p.notion_id]
    tous = c.get("/pedagogy/notions", params={"include_unproven": True}).json()
    assert tous["total"] == 2 and {n["proof_status"] for n in tous["items"]} == {"PROVEN_OFFICIAL", "UNPROVEN"}


def test_filtres_et_detail(client):
    c, p, _ = client
    assert c.get("/pedagogy/notions", params={"subject": "SVT"}).json()["total"] == 0
    assert c.get("/pedagogy/notions", params={"level": "4E", "difficulty": 2}).json()["total"] == 1
    assert c.get(f"/pedagogy/notions/{p.notion_id}").json()["title"] == "Puissances de 10"
    assert c.get("/pedagogy/notions/INCONNU").status_code == 404


def test_exercices_seulement_prouves_qa_et_non_fixture(client):
    c, p, _ = client
    r = c.get("/pedagogy/exercises").json()
    assert [e["exercise_id"] for e in r["items"]] == ["EX.ok.1"]
    assert c.get("/pedagogy/exercises", params={"difficulty": "ADVANCED"}).json()["total"] == 0
    assert c.get("/pedagogy/quiz", params={"notion_id": p.notion_id}).json()["total"] == 1


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 1000}, {"offset": -1}, {"level": "7E"}, {"subject": "HISTOIRE"}])
def test_entrees_bornees(client, params):
    c, _, _ = client
    assert c.get("/pedagogy/notions", params=params).status_code == 422


def test_aucune_route_d_ecriture(client):
    c, _, _ = client
    assert c.post("/pedagogy/notions", json={}).status_code == 405
    assert c.delete("/pedagogy/exercises").status_code == 405
