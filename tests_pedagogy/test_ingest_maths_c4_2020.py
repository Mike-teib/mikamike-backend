"""Tests de l'extraction des notions de mathématiques 4e / 3e (cycle 4, programme 2020 + repères annuels)."""

from __future__ import annotations

import json

import pytest

from pedagogy.ingest import maths_c4_2020 as ingest
from pedagogy.models import Level, NotionFile, ProofStatus, ReviewStatus
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, sha256_file, verify_notion_against_source

ALLOWED_SOURCES = {"SRC-C4-REPERES-MATHS-2019", "SRC-C4-2020"}
FILES = {Level.QUATRIEME: DATA_DIR / "notions" / "MATHS" / "4E.json",
         Level.TROISIEME: DATA_DIR / "notions" / "MATHS" / "3E.json"}


@pytest.fixture(scope="module")
def files():
    return {lv: NotionFile.model_validate(json.loads(p.read_text(encoding="utf-8"))) for lv, p in FILES.items()}


@pytest.fixture(scope="module")
def texts():
    reg = load_registry()
    return {sid: load_source_text(reg.sources[sid], REPO_ROOT) for sid in ALLOWED_SOURCES}


def test_files_validate_and_counts(files):
    for level, nf in files.items():
        assert nf.level == level
        assert nf.course.value == "COMMON"
        assert len(nf.notions) > 15
        assert all(n.level == level and n.school_year == "2026-2027" and n.difficulty == 3 for n in nf.notions)


def test_all_proven_not_reviewed_with_allowed_sources(files):
    reg = load_registry()
    for nf in files.values():
        for n in nf.notions:
            assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
            assert n.review_status == ReviewStatus.NOT_REVIEWED
            assert n.source_id in ALLOWED_SOURCES
            src = reg.sources[n.source_id]
            assert n.source_sha256 == src.sha256 == sha256_file(REPO_ROOT / src.local_path)
            assert n.official_wording


def test_reverification_against_source(files, texts):
    for nf in files.values():
        for n in nf.notions:
            assert verify_notion_against_source(n, texts).status == ProofStatus.PROVEN_OFFICIAL, n.notion_id


def test_unique_ids_and_prerequisites_resolve(files):
    ids = [n.notion_id for nf in files.values() for n in nf.notions]
    assert len(ids) == len(set(ids))
    known = set(ids)
    for nf in files.values():
        for n in nf.notions:
            assert set(n.prerequisites) <= known


def test_year_attribution_samples(files):
    """Quelques repères dont l'année est connue par la colonne du tableau officiel."""
    w4 = " ".join(n.official_wording for n in files[Level.QUATRIEME].notions)
    w3 = " ".join(n.official_wording for n in files[Level.TROISIEME].notions)
    assert "Un nouvel indicateur de position est introduit : la médiane." in w4
    assert "Un indicateur de dispersion est introduit : l’étendue." in w3
    assert "configuration des triangles emboîtés" in w4 and "configuration du papillon" in w3
    assert "médiane" not in w3 and "l’étendue" not in w4
    # Limites et possibilités ne sont pas des notions.
    assert "Aucune connaissance" not in w3 + w4


def test_no_algorithmique_notions_without_year(files):
    assert not any(n.domain_code == "AP" for nf in files.values() for n in nf.notions)


def test_build_is_deterministic_and_matches_files(files, tmp_path):
    a, b = ingest.build(), ingest.build()
    assert not a.rejected
    assert [n.model_dump() for n in a.notions] == [n.model_dump() for n in b.notions]
    on_disk = [n.notion_id for lv in (Level.QUATRIEME, Level.TROISIEME) for n in files[lv].notions]
    assert sorted(n.notion_id for n in a.notions) == sorted(on_disk)
