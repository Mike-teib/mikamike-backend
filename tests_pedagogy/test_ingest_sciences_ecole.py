"""Tests de l'extraction des notions de sciences et technologie CP → 6e (année 2026-2027)."""

from __future__ import annotations

import json

import pytest

from pedagogy.ingest import sciences_ecole as ingest
from pedagogy.models import Course, Level, NotionFile, ProofStatus, ReviewStatus, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, normalize_for_match, sha256_file, verify_notion_against_source

EXPECTED_SOURCE = {
    Level.CP: "SRC-C2-ST-2026", Level.CE1: "SRC-C2-ST-2026", Level.CE2: "SRC-C2-ST-2026",
    Level.CM1: "SRC-C3-ST-2026",
    Level.CM2: "SRC-C3-2020", Level.SIXIEME: "SRC-C3-2020",
}
EXPECTED_DIFFICULTY = {Level.CP: 1, Level.CE1: 1, Level.CE2: 1, Level.CM1: 2, Level.CM2: 2, Level.SIXIEME: 2}
FILES = {lv: DATA_DIR / "notions" / "ST" / f"{lv.value}.json" for lv in EXPECTED_SOURCE}


@pytest.fixture(scope="module")
def files():
    return {lv: NotionFile.model_validate(json.loads(p.read_text(encoding="utf-8"))) for lv, p in FILES.items()}


@pytest.fixture(scope="module")
def texts():
    reg = load_registry()
    return {sid: load_source_text(reg.sources[sid], REPO_ROOT) for sid in set(EXPECTED_SOURCE.values())}


@pytest.fixture(scope="module")
def built():
    return ingest.build()


def test_files_validate_and_counts(files):
    for level, nf in files.items():
        assert nf.level == level and nf.subject == Subject.SCIENCES_TECHNOLOGIE
        assert nf.course == Course.COMMON
        assert len(nf.notions) > 8, level
        for n in nf.notions:
            assert n.level == level and n.school_year == "2026-2027"
            assert n.difficulty == EXPECTED_DIFFICULTY[level]
            assert n.notion_id.startswith(f"ST.{level.value}.")


def test_all_proven_not_reviewed_with_expected_source(files):
    reg = load_registry()
    for level, nf in files.items():
        for n in nf.notions:
            assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
            assert n.review_status == ReviewStatus.NOT_REVIEWED
            assert n.source_id == EXPECTED_SOURCE[level], n.notion_id
            src = reg.sources[n.source_id]
            assert n.source_sha256 == src.sha256 == sha256_file(REPO_ROOT / src.local_path)
            assert n.official_wording and n.source_page_or_section.isdigit()


def test_reverification_against_source(files, texts):
    for nf in files.values():
        for n in nf.notions:
            assert verify_notion_against_source(n, texts).status == ProofStatus.PROVEN_OFFICIAL, n.notion_id


def test_excerpt_on_single_declared_page(files, texts):
    for nf in files.values():
        for n in nf.notions:
            st = texts[n.source_id]
            assert normalize_for_match(n.official_wording) in st.pages[int(n.source_page_or_section)]


def test_unique_ids_and_prerequisites_resolve(files):
    ids = [n.notion_id for nf in files.values() for n in nf.notions]
    assert len(ids) == len(set(ids))
    for nf in files.values():
        local = {n.notion_id for n in nf.notions}
        for n in nf.notions:
            assert set(n.prerequisites) <= local


def test_no_activity_proposals_in_2026_levels(files):
    for level in (Level.CP, Level.CE1, Level.CE2, Level.CM1):
        for n in files[level].notions:
            assert not n.official_wording.startswith(("L’élève", "À partir", "Pour ", "Lors ")), n.official_wording


def test_2020_year_attribution_explicit(built, files):
    rep = built.report_2020
    six_ids = {n.notion_id for n in files[Level.SIXIEME].notions}
    cm2_ids = {n.notion_id for n in files[Level.CM2].notions}
    # tout ce qui n'a pas d'année explicite est en 6E et listé
    assert rep.unspecified and set(rep.unspecified) <= six_ids
    # chaque notion CM2 est justifiée par un repère de progressivité cité
    justified = {nid for nid, lvl, why in rep.decisions if lvl == "CM2" and why}
    assert cm2_ids == justified
    # pas de doublon de libellé entre CM2 et 6E
    w_cm2 = {normalize_for_match(n.official_wording) for n in files[Level.CM2].notions}
    w_6e = {normalize_for_match(n.official_wording) for n in files[Level.SIXIEME].notions}
    assert not (w_cm2 & w_6e)


def test_cm1_only_from_2026_programme(built):
    levels_c3_2026 = {n.level for n in built.builders[1].notions}
    assert levels_c3_2026 == {Level.CM1}


def test_deterministic(built, files):
    again = ingest.build()
    assert [n.notion_id for n in again.notions] == [n.notion_id for n in built.notions]
    assert [n.official_wording for n in again.notions] == [n.official_wording for n in built.notions]
    on_disk = [n.notion_id for lv in ingest.LEVELS_OUT for n in files[lv].notions]
    assert sorted(on_disk) == sorted(n.notion_id for n in built.notions)
