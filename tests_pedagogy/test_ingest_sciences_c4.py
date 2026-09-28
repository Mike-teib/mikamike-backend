"""
Physique-chimie et SVT cycle 4 (SRC-C4-2020) : notions PROUVÉES, verbatim, re-vérifiées contre
le PDF enregistré, identifiants uniques, fichiers non vides, génération déterministe.
"""

import json

import pytest

from pedagogy.ingest import sciences_c4_2020 as mod
from pedagogy.ingest.core import link_sequential_prerequisites
from pedagogy.models import Course, Level, NotionFile, ProofStatus, ReviewStatus, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, verify_notion_against_source

FILES = {
    (sub, lv): DATA_DIR / "notions" / code / f"{lv.value}.json"
    for sub, code in ((Subject.PHYSIQUE_CHIMIE, "PC"), (Subject.SVT, "SVT"))
    for lv in (Level.CINQUIEME, Level.QUATRIEME, Level.TROISIEME)
}


@pytest.fixture(scope="module")
def files():
    return {k: NotionFile.model_validate(json.loads(p.read_text(encoding="utf-8"))) for k, p in FILES.items()}


@pytest.fixture(scope="module")
def source():
    src = load_registry().sources[mod.SOURCE_ID]
    return src, load_source_text(src, REPO_ROOT)


@pytest.fixture(scope="module")
def built():
    return mod.build()


def _all(files):
    return [n for nf in files.values() for n in nf.notions]


def test_files_valid_and_non_empty(files):
    for (sub, lv), nf in files.items():
        assert nf.subject == sub and nf.level == lv and nf.course == Course.COMMON
        assert len(nf.notions) > 5, (sub, lv)
        for n in nf.notions:
            assert n.subject == sub and n.level == lv
            assert n.school_year == "2026-2027"
            assert n.official_program_version == mod.PROGRAM_VERSION
            assert n.difficulty == mod.DIFFICULTY[lv]
            assert n.domain_code in mod.DOMAINS and mod.DOMAINS[n.domain_code][0] == sub


def test_proven_not_reviewed_and_sourced(files, source):
    src, _ = source
    for n in _all(files):
        assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
        assert n.review_status == ReviewStatus.NOT_REVIEWED
        assert n.source_id == "SRC-C4-2020"
        assert n.source_sha256 == src.sha256
        assert n.official_wording and n.source_page_or_section


def test_reverification_against_pdf(files, source):
    _, st = source
    for n in _all(files):
        res = verify_notion_against_source(n, {st.source.source_id: st})
        assert res.status == ProofStatus.PROVEN_OFFICIAL, (n.notion_id, res.reasons)


def test_unique_ids_and_prerequisites_exist(files):
    notions = _all(files)
    ids = [n.notion_id for n in notions]
    assert len(ids) == len(set(ids))
    known = set(ids)
    for n in notions:
        assert set(n.prerequisites) <= known


def test_rules_quotes_verbatim_and_no_rejection(built):
    builders, attributions, skipped, problems = built
    assert problems == []
    assert all(not b.rejected for b in builders.values())
    assert {p.skip_reason for p in skipped} <= {
        "cesure_fin_de_ligne_non_prouvable", "item_a_cheval_sur_deux_pages", "glyphe_police_symbol_non_unicode"}
    assert any(a.explicit for a in attributions) and any(not a.explicit for a in attributions)


def test_deterministic_regeneration(files, built):
    builders, _, _, _ = built
    for sub, b in builders.items():
        for lv, notions in b.by_level().items():
            regenerated = [n.model_dump(mode="json") for n in link_sequential_prerequisites(notions)]
            on_disk = [n.model_dump(mode="json") for n in files[(sub, lv)].notions]
            assert regenerated == on_disk, (sub, lv)
