"""Tests des registres candidats Physique-chimie (5E→TLE) et Sciences et technologie (6E)."""

import json
from pathlib import Path

import pytest

from pedagogy.models import (
    LEVEL_RANK,
    ExerciseType,
    Level,
    NotionFile,
    ProofStatus,
    SourceType,
    Subject,
)
from pedagogy.registry import DATA_DIR, load_registry

NOTIONS_DIR = DATA_DIR / "notions"
PILOT_DIR = DATA_DIR / "pilot"

PC_FILES = ["5E.json", "4E.json", "3E.json", "2NDE.json", "1RE_SPECIALITE.json", "TLE_SPECIALITE.json"]
EXPECTED = [NOTIONS_DIR / "PC" / f for f in PC_FILES] + [NOTIONS_DIR / "ST" / "6E.json"]


def _load(path: Path) -> NotionFile:
    return NotionFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def files():
    return {p: _load(p) for p in EXPECTED}


@pytest.fixture(scope="module")
def notions(files):
    return [n for nf in files.values() for n in nf.notions]


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_all_files_present_and_valid(files):
    assert set(files) == set(EXPECTED)
    for path, nf in files.items():
        assert nf.notions, path
        if path.parent.name == "ST":
            assert nf.subject == Subject.SCIENCES_TECHNOLOGIE and nf.level == Level.SIXIEME
        else:
            assert nf.subject == Subject.PHYSIQUE_CHIMIE and nf.level != Level.SIXIEME


def test_counts_per_level(files):
    for path, nf in files.items():
        lo, hi = (15, 25) if path.parent.name == "ST" else (12, 22)
        assert lo <= len(nf.notions) <= hi, (path, len(nf.notions))


def test_no_pc_6e_file():
    assert not (NOTIONS_DIR / "PC" / "6E.json").exists()


def test_all_candidates_unproven(notions):
    for n in notions:
        assert n.proof_status == ProofStatus.UNPROVEN, n.notion_id
        assert n.source_type == SourceType.CANDIDATE_UNVERIFIED, n.notion_id
        assert n.official_wording is None, n.notion_id
        assert not n.eligible_for_content
        assert n.source_id and n.provenance_note.startswith("Candidat reconstitué de mémoire")


def test_source_ids_exist(notions, registry):
    for n in notions:
        assert n.source_id in registry.sources, n.notion_id
        src = registry.sources[n.source_id]
        assert n.subject in src.subjects and n.level in src.levels, n.notion_id


def test_ids_unique(notions):
    ids = [n.notion_id for n in notions]
    assert len(ids) == len(set(ids))


def test_registry_loads_our_files_without_errors(registry, notions):
    ours = {str(p.relative_to(DATA_DIR)) for p in EXPECTED}
    assert not [e for e in registry.load_errors if e[0] in ours]
    for n in notions:
        assert n.notion_id in registry.notions


def test_prerequisites_exist_and_not_higher(notions, registry):
    for n in notions:
        for p in n.prerequisites:
            assert p in registry.notions, (n.notion_id, p)
            pre = registry.notions[p]
            assert LEVEL_RANK[pre.level] <= LEVEL_RANK[n.level], (n.notion_id, p)
            assert pre.subject in (Subject.PHYSIQUE_CHIMIE, Subject.SCIENCES_TECHNOLOGIE), (n.notion_id, p)


def test_cross_subject_links_to_maths(notions, registry):
    links = {link for n in notions for link in n.cross_subject_links}
    assert links and all(link.startswith("MATHS.") for link in links)
    for n in notions:
        for link in n.cross_subject_links:
            lv = Level(link.split(".")[1])
            assert LEVEL_RANK[lv] <= LEVEL_RANK[n.level], (n.notion_id, link)
    if not any(n.subject == Subject.MATHS for n in registry.notions.values()):
        pytest.skip("Fichiers de notions MATHS absents (rédigés en parallèle) : existence des liens non vérifiée.")
    missing = sorted({link for link in links if link not in registry.notions})
    assert not missing, missing


@pytest.mark.parametrize("name,subject,levels", [
    ("PC_pilot_plan.json", "PHYSIQUE_CHIMIE", ["5E", "4E", "3E", "2NDE", "1RE", "TLE"]),
    ("ST_pilot_plan.json", "SCIENCES_TECHNOLOGIE", ["6E"]),
])
def test_pilot_plans(name, subject, levels, registry):
    plan = json.loads((PILOT_DIR / name).read_text(encoding="utf-8"))
    assert plan["subject"] == subject
    assert plan["status"] == "BLOCKED_NO_PROVEN_NOTION"
    assert plan["rule"] == "exercises only for PROVEN_OFFICIAL notions"
    assert sorted(plan["levels"]) == sorted(levels)
    for lv, entries in plan["levels"].items():
        assert len(entries) == 3, lv
        assert len({e["notion_id"] for e in entries}) == 3
        for e in entries:
            n = registry.notions[e["notion_id"]]
            assert n.level.value == lv and n.subject.value == subject
            types = e["planned_exercise_types"]
            assert 3 <= len(types) <= 4 and len(set(types)) == len(types)
            for t in types:
                ExerciseType(t)
            assert e["why"]
            assert set(e) == {"notion_id", "planned_exercise_types", "why"}  # aucun contenu d'exercice
