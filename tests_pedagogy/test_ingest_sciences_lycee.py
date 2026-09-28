"""
Sciences au lycée général (PC 2nde/1re/Tle, SVT 2nde/1re/Tle, enseignement scientifique 1re/Tle) :
notions PROUVÉES, verbatim, re-vérifiées contre les PDF enregistrés, identifiants uniques,
extraits complets (>= 4 mots), génération déterministe.
"""

import json

import pytest

from pedagogy.ingest import sciences_lycee as mod
from pedagogy.ingest.core import link_sequential_prerequisites
from pedagogy.models import Course, Level, NotionFile, ProofStatus, ReviewStatus, Subject
from pedagogy.registry import REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, verify_notion_against_source

EXPECTED = {
    "SRC-2NDE-PC-2019": (Subject.PHYSIQUE_CHIMIE, Level.SECONDE, Course.COMMON, "PC/2NDE.json", 3),
    "SRC-1RE-PC-2019": (Subject.PHYSIQUE_CHIMIE, Level.PREMIERE, Course.SPECIALITE, "PC/1RE_SPECIALITE.json", 4),
    "SRC-TLE-PC-2019": (Subject.PHYSIQUE_CHIMIE, Level.TERMINALE, Course.SPECIALITE, "PC/TLE_SPECIALITE.json", 4),
    "SRC-2NDE-SVT-2019": (Subject.SVT, Level.SECONDE, Course.COMMON, "SVT/2NDE.json", 3),
    "SRC-1RE-SVT-2019": (Subject.SVT, Level.PREMIERE, Course.SPECIALITE, "SVT/1RE_SPECIALITE.json", 4),
    "SRC-TLE-SVT-2019": (Subject.SVT, Level.TERMINALE, Course.SPECIALITE, "SVT/TLE_SPECIALITE.json", 4),
    "SRC-1RE-ES-2023": (Subject.ENSEIGNEMENT_SCIENTIFIQUE, Level.PREMIERE, Course.ENSEIGNEMENT_SCIENTIFIQUE,
                        "ES/1RE_ENSEIGNEMENT_SCIENTIFIQUE.json", 4),
    "SRC-TLE-ES-2023": (Subject.ENSEIGNEMENT_SCIENTIFIQUE, Level.TERMINALE, Course.ENSEIGNEMENT_SCIENTIFIQUE,
                        "ES/TLE_ENSEIGNEMENT_SCIENTIFIQUE.json", 4),
}
SPECS = {s.source_id: s for s in mod.SPECS}


@pytest.fixture(scope="module")
def files():
    return {sid: NotionFile.model_validate(json.loads(mod.output_path(spec).read_text(encoding="utf-8")))
            for sid, spec in SPECS.items()}


@pytest.fixture(scope="module")
def sources():
    reg = load_registry()
    return {sid: (reg.sources[sid], load_source_text(reg.sources[sid], REPO_ROOT)) for sid in EXPECTED}


@pytest.fixture(scope="module")
def built():
    return {sid: mod.build(spec) for sid, spec in SPECS.items()}


def test_specs_cover_expected_sources():
    assert set(SPECS) == set(EXPECTED)
    for sid, (sub, lv, course, out, diff) in EXPECTED.items():
        spec = SPECS[sid]
        assert (spec.subject, spec.level, spec.course, spec.out, spec.difficulty) == (sub, lv, course, out, diff)


def test_files_valid_and_plausible(files):
    for sid, nf in files.items():
        sub, lv, course, _, diff = EXPECTED[sid]
        assert (nf.subject, nf.level, nf.course) == (sub, lv, course)
        assert len(nf.notions) > 15, sid
        codes = {code for _, code, _ in SPECS[sid].domains}
        for n in nf.notions:
            assert n.school_year == "2026-2027"
            assert n.difficulty == diff
            assert n.domain_code in codes
            assert 2 <= len(n.chapter) <= 200
        # chaque fichier couvre plusieurs grandes parties du programme
        assert len({n.domain_code for n in nf.notions}) >= 3, sid


def test_proven_not_reviewed_and_sourced(files, sources):
    for sid, nf in files.items():
        src, _ = sources[sid]
        for n in nf.notions:
            assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
            assert n.review_status == ReviewStatus.NOT_REVIEWED
            assert n.source_id == sid
            assert n.source_sha256 == src.sha256
            assert n.official_wording and n.source_page_or_section


def test_reverification_against_pdf(files, sources):
    for sid, nf in files.items():
        _, st = sources[sid]
        for n in nf.notions:
            res = verify_notion_against_source(n, {sid: st})
            assert res.status == ProofStatus.PROVEN_OFFICIAL, (n.notion_id, res.reasons)


def test_excerpts_complete(files):
    for nf in files.values():
        for n in nf.notions:
            w = n.official_wording
            assert len(w.split()) >= 4, w
            assert not w.startswith("↔"), w                  # renvois mathématiques ES exclus
            assert w[0].isupper() or w[0] in "«(" or w.startswith("pH"), w
            assert "\n" not in w


def test_kinds_present(files):
    """Les deux colonnes sont représentées : contenus / connaissances / savoirs ET capacités."""
    for sid, nf in files.items():
        spec = SPECS[sid]
        notes = [n.provenance_note for n in nf.notions]
        assert any(f"({spec.left_kind})" in p for p in notes), sid
        assert any(f"({spec.right_kind})" in p for p in notes), sid


def test_unique_ids_and_prerequisites_exist(files):
    notions = [n for nf in files.values() for n in nf.notions]
    ids = [n.notion_id for n in notions]
    assert len(ids) == len(set(ids))
    known = set(ids)
    for n in notions:
        assert set(n.prerequisites) <= known


def test_no_builder_rejection(built):
    for sid, (b, skipped) in built.items():
        assert b.rejected == [], sid
        assert {s.reason for s in skipped} <= {
            "trop_court", "absent_du_texte_brut", "fragment_sans_majuscule", "phrase_inachevee",
            "cesure_fin_de_ligne", "symboles_non_textuels", "suite_sur_page_suivante",
            "suite_de_page_precedente", "renvoi_mathematique", "doublon_dans_le_chapitre"}, sid


def test_deterministic_regeneration(files, built):
    for sid, (b, _) in built.items():
        regenerated = [n.model_dump(mode="json") for n in link_sequential_prerequisites(b.notions)]
        on_disk = [n.model_dump(mode="json") for n in files[sid].notions]
        assert regenerated == on_disk, sid
