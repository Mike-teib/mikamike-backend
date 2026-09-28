"""
Registre MATHS (agent A) : fichiers candidats valides, honnêtes (UNPROVEN, aucun libellé
officiel), identifiants cohérents, prérequis existants et jamais d'un niveau supérieur,
ancres présentes, plan de pilote cohérent.
"""

import json
from pathlib import Path

import pytest

from pedagogy.models import (
    CYCLE_OF_LEVEL,
    LEVEL_RANK,
    Course,
    ExerciseType,
    Level,
    NotionFile,
    ProofStatus,
    PublicationStatus,
    ReviewStatus,
    SourceType,
    Subject,
    make_notion_id,
    normalize_title,
)
from pedagogy.registry import DATA_DIR, load_registry

MATHS_DIR = DATA_DIR / "notions" / "MATHS"
PILOT = DATA_DIR / "pilot" / "MATHS_pilot_plan.json"

EXPECTED_FILES = {
    "6E.json": (Level.SIXIEME, Course.COMMON),
    "5E.json": (Level.CINQUIEME, Course.COMMON),
    "4E.json": (Level.QUATRIEME, Course.COMMON),
    "3E.json": (Level.TROISIEME, Course.COMMON),
    "2NDE.json": (Level.SECONDE, Course.COMMON),
    "1RE_SPECIALITE.json": (Level.PREMIERE, Course.SPECIALITE),
    "TLE_SPECIALITE.json": (Level.TERMINALE, Course.SPECIALITE),
    "TLE_MATHS_EXPERTES.json": (Level.TERMINALE, Course.MATHS_EXPERTES),
    "TLE_MATHS_COMPLEMENTAIRES.json": (Level.TERMINALE, Course.MATHS_COMPLEMENTAIRES),
}

ANCHORS = {
    "MATHS.6E.NC.nombres-decimaux": ("6E", "NC", "Nombres décimaux", Course.COMMON),
    "MATHS.6E.NC.fractions": ("6E", "NC", "Fractions", Course.COMMON),
    "MATHS.5E.NC.nombres-relatifs": ("5E", "NC", "Nombres relatifs", Course.COMMON),
    "MATHS.5E.OGD.proportionnalite": ("5E", "OGD", "Proportionnalité", Course.COMMON),
    "MATHS.4E.NC.puissances": ("4E", "NC", "Puissances", Course.COMMON),
    "MATHS.4E.NC.calcul-litteral": ("4E", "NC", "Calcul littéral", Course.COMMON),
    "MATHS.4E.NC.equations-du-premier-degre": ("4E", "NC", "Équations du premier degré", Course.COMMON),
    "MATHS.4E.EG.theoreme-de-pythagore": ("4E", "EG", "Théorème de Pythagore", Course.COMMON),
    "MATHS.3E.OGD.fonctions-lineaires-et-affines": ("3E", "OGD", "Fonctions linéaires et affines", Course.COMMON),
    "MATHS.3E.EG.trigonometrie-dans-le-triangle-rectangle": (
        "3E", "EG", "Trigonométrie dans le triangle rectangle", Course.COMMON),
    "MATHS.2NDE.GEO.vecteurs": ("2NDE", "GEO", "Vecteurs", Course.COMMON),
    "MATHS.2NDE.FON.fonctions-de-reference": ("2NDE", "FON", "Fonctions de référence", Course.COMMON),
    "MATHS.1RE.AN.derivation": ("1RE", "AN", "Dérivation", Course.SPECIALITE),
    "MATHS.1RE.AN.suites-numeriques": ("1RE", "AN", "Suites numériques", Course.SPECIALITE),
    "MATHS.1RE.AN.fonction-exponentielle": ("1RE", "AN", "Fonction exponentielle", Course.SPECIALITE),
    "MATHS.TLE.AN.fonction-logarithme-neperien": ("TLE", "AN", "Fonction logarithme népérien", Course.SPECIALITE),
    "MATHS.TLE.AN.raisonnement-par-recurrence": ("TLE", "AN", "Raisonnement par récurrence", Course.SPECIALITE),
    "MATHS.TLE.AN.primitives-et-equations-differentielles": (
        "TLE", "AN", "Primitives et équations différentielles", Course.SPECIALITE),
}

COMPETENCIES = {"CHERCHER", "MODELISER", "REPRESENTER", "RAISONNER", "CALCULER", "COMMUNIQUER"}


def _maths_files():
    return sorted(MATHS_DIR.glob("*.json"))


@pytest.fixture(scope="module")
def maths_files():
    out = {}
    for path in _maths_files():
        out[path.name] = NotionFile.model_validate(json.loads(path.read_text(encoding="utf-8")))
    return out


@pytest.fixture(scope="module")
def maths_notions(maths_files):
    return [n for nf in maths_files.values() for n in nf.notions]


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_expected_files_present_and_homogeneous(maths_files):
    for fname, (level, course) in EXPECTED_FILES.items():
        assert fname in maths_files, fname
        nf = maths_files[fname]
        assert nf.subject == Subject.MATHS
        assert nf.level == level and nf.course == course
        assert nf.schema_version == "1.0"
        assert nf.generated_by == "agent-A-maths-candidates"
        assert "UNPROVEN" in nf.disclaimer


def test_notion_counts_per_main_level(maths_files):
    for fname in ("6E.json", "5E.json", "4E.json", "3E.json", "2NDE.json",
                  "1RE_SPECIALITE.json", "TLE_SPECIALITE.json"):
        assert 15 <= len(maths_files[fname].notions) <= 25, fname
    for fname in ("TLE_MATHS_EXPERTES.json", "TLE_MATHS_COMPLEMENTAIRES.json"):
        assert len(maths_files[fname].notions) >= 5, fname


def test_all_candidates_are_honest(maths_notions, registry):
    assert maths_notions
    for n in maths_notions:
        assert n.proof_status == ProofStatus.UNPROVEN, n.notion_id
        assert n.source_type == SourceType.CANDIDATE_UNVERIFIED, n.notion_id
        assert n.official_wording is None, n.notion_id
        assert n.review_status == ReviewStatus.NOT_REVIEWED
        assert n.publication_status == PublicationStatus.DRAFT
        assert n.source_sha256 is None and n.source_page_or_section is None
        assert not n.eligible_for_content
        assert n.source_id in registry.sources, n.source_id
        src = registry.sources[n.source_id]
        assert n.source_title == src.title
        assert n.source_url_or_ref == src.reference
        assert Subject.MATHS in src.subjects and n.level in src.levels and n.course in src.courses
        assert n.source_id in n.provenance_note
        assert "non vérifié" in n.provenance_note and "Aucun libellé officiel stocké" in n.provenance_note


def test_ids_titles_and_fields_consistent(maths_notions):
    ids = [n.notion_id for n in maths_notions]
    assert len(ids) == len(set(ids))
    for n in maths_notions:
        assert n.notion_id == make_notion_id(Subject.MATHS, n.level, n.domain_code, n.title)
        assert n.normalized_title == normalize_title(n.title)
        assert n.cycle == CYCLE_OF_LEVEL[n.level]
        assert n.school_year == "2025-2026"
        assert 1 <= len(n.learning_objectives) <= 3
        assert 1 <= len(n.expected_skills) <= 3
        assert 1 <= len(n.common_mistakes) <= 3
        assert n.competency_ids and set(n.competency_ids) <= COMPETENCIES


def test_prerequisites_exist_and_never_point_higher(maths_notions, registry):
    for n in maths_notions:
        for p in n.prerequisites:
            assert p in registry.notions, (n.notion_id, p)
            pre = registry.notions[p]
            assert LEVEL_RANK[pre.level] <= LEVEL_RANK[n.level], (n.notion_id, p)
        for r in n.related_notions:
            assert r in registry.notions, (n.notion_id, r)


def test_prerequisite_graph_is_acyclic(maths_notions):
    graph = {n.notion_id: list(n.prerequisites) for n in maths_notions}
    state = {}

    def visit(u):
        state[u] = 1
        for v in graph.get(u, ()):
            assert state.get(v) != 1, f"cycle:{u}->{v}"
            if v not in state:
                visit(v)
        state[u] = 2

    for u in graph:
        if u not in state:
            visit(u)


def test_anchors_present(maths_notions):
    by_id = {n.notion_id: n for n in maths_notions}
    for anchor_id, (level, dom, title, course) in ANCHORS.items():
        assert anchor_id == make_notion_id(Subject.MATHS, Level(level), dom, title)
        assert anchor_id in by_id, anchor_id
        n = by_id[anchor_id]
        assert n.title == title and n.domain_code == dom and n.course == course


def test_registry_loads_maths_without_errors(registry):
    maths_errors = [e for e in registry.load_errors if "MATHS" in e[0]]
    assert not maths_errors, maths_errors


def test_pilot_plan(maths_notions):
    plan = json.loads(PILOT.read_text(encoding="utf-8"))
    assert plan["subject"] == "MATHS"
    assert plan["status"] == "BLOCKED_NO_PROVEN_NOTION"
    assert plan["rule"] == "exercises only for PROVEN_OFFICIAL notions"
    by_id = {n.notion_id: n for n in maths_notions}
    assert set(plan["levels"]) == {lv.value for lv in Level}
    valid_types = {t.value for t in ExerciseType}
    used = set()
    for level, entries in plan["levels"].items():
        assert len(entries) == 3, level
        assert len({e["notion_id"] for e in entries}) == 3
        for e in entries:
            n = by_id.get(e["notion_id"])
            assert n is not None, e["notion_id"]
            assert n.level.value == level
            if level in ("1RE", "TLE"):
                assert n.course == Course.SPECIALITE
            types = e["planned_exercise_types"]
            assert 3 <= len(types) <= 4 and len(set(types)) == len(types)
            assert set(types) <= valid_types
            assert e["why"].strip()
            assert set(e) == {"notion_id", "planned_exercise_types", "why"}
            used |= set(types)
            # Aucune notion du pilote n'est éligible : production bloquée.
            assert not n.eligible_for_content
    assert len(used) >= 8
