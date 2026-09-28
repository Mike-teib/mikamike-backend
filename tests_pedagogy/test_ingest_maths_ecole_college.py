"""Notions PROUVÉES de mathématiques école/collège (CP → 6e, 5e) extraites des PDF officiels."""

from __future__ import annotations

import json

import pytest

from pedagogy.ingest import maths_c3_2025, maths_c4_2026
from pedagogy.models import NotionFile, ProofStatus, ReviewStatus
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, verify_notion_against_source

EXPECTED_SOURCE = {
    "CP": "SRC-C2-MATHS-2025",
    "CE1": "SRC-C2-MATHS-2025",
    "CE2": "SRC-C2-MATHS-2025",
    "CM1": "SRC-C3-MATHS-NOUVEAU",
    "CM2": "SRC-C3-MATHS-NOUVEAU",
    "6E": "SRC-C3-MATHS-NOUVEAU",
    "5E": "SRC-C4-MATHS-2026",
}
LEVELS = list(EXPECTED_SOURCE)


def _load(level: str) -> NotionFile:
    path = DATA_DIR / "notions" / "MATHS" / f"{level}.json"
    return NotionFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def registry():
    return load_registry()


@pytest.fixture(scope="module")
def texts(registry):
    return {sid: load_source_text(registry.sources[sid], REPO_ROOT) for sid in set(EXPECTED_SOURCE.values())}


@pytest.mark.parametrize("level", LEVELS)
def test_file_loads_and_is_proven(level, registry):
    nf = _load(level)
    assert nf.level.value == level
    assert len(nf.notions) > 20
    src = registry.sources[EXPECTED_SOURCE[level]]
    for n in nf.notions:
        assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
        assert n.review_status == ReviewStatus.NOT_REVIEWED
        assert n.source_id == src.source_id
        assert n.source_sha256 == src.sha256
        assert n.official_wording
        assert n.school_year == "2026-2027"


@pytest.mark.parametrize("level", LEVELS)
def test_every_notion_reverifies_against_pdf(level, texts):
    for n in _load(level).notions:
        res = verify_notion_against_source(n, texts)
        assert res.status == ProofStatus.PROVEN_OFFICIAL, (n.notion_id, res.reasons)


def test_ids_unique_across_levels():
    ids = [n.notion_id for lv in LEVELS for n in _load(lv).notions]
    assert len(ids) == len(set(ids))


def test_prerequisites_stay_within_chapter():
    for lv in LEVELS:
        by_id = {n.notion_id: n for n in _load(lv).notions}
        for n in by_id.values():
            for pre in n.prerequisites:
                p = by_id[pre]
                assert (p.domain_code, p.chapter) == (n.domain_code, n.chapter)


def test_expected_counts_and_domains():
    counts = {lv: len(_load(lv).notions) for lv in ("CM1", "CM2", "6E", "5E")}
    assert counts == {"CM1": 129, "CM2": 115, "6E": 95, "5E": 105}
    assert {n.domain_code for n in _load("6E").notions} == {"NCRP", "GM", "EG", "OGDP", "PROP", "INFO"}
    assert {n.domain_code for n in _load("5E").notions} == {"NC", "EG", "OGDP", "PROPF", "INFO"}


@pytest.mark.parametrize("module", [maths_c3_2025, maths_c4_2026])
def test_builders_are_deterministic_and_match_files(module):
    b1, b2 = module.build(), module.build()
    assert not b1.rejected and not b1.orphans
    ids1 = [n.notion_id for n in b1.notions]
    assert ids1 == [n.notion_id for n in b2.notions]
    on_disk = [n.notion_id for lv in sorted({n.level.value for n in b1.notions}) for n in _load(lv).notions]
    assert sorted(ids1) == sorted(on_disk)
