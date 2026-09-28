"""
Mathématiques lycée général (2NDE, 1RE spécialité / maths intégrées à l'ES, TLE spécialité /
complémentaires / expertes) : notions PROUVÉES extraites verbatim des PDF officiels
(pedagogy.ingest.maths_lycee). Fichiers valides, preuve recalculée, déterminisme.
"""

import json

import pytest

from pedagogy.ingest import maths_lycee
from pedagogy.models import Course, Level, NotionFile, ProofStatus, ReviewStatus, Subject
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import load_source_text, verify_notion_against_source

MATHS_DIR = DATA_DIR / "notions" / "MATHS"

EXPECTED = {
    "2NDE.json": ("SRC-2NDE-MATHS-2026", Level.SECONDE, Course.COMMON, 3, 15),
    "1RE_SPECIALITE.json": ("SRC-1RE-MATHS-SPE-2026", Level.PREMIERE, Course.SPECIALITE, 4, 15),
    "1RE_MATHS_SPECIFIQUES_1RE.json": ("SRC-1RE-MATHS-ES-2026", Level.PREMIERE, Course.MATHS_SPECIFIQUES_1RE, 4, 15),
    "TLE_SPECIALITE.json": ("SRC-TLE-MATHS-SPE-2019", Level.TERMINALE, Course.SPECIALITE, 4, 15),
    "TLE_MATHS_COMPLEMENTAIRES.json": ("SRC-TLE-MATHS-COMP-2019", Level.TERMINALE, Course.MATHS_COMPLEMENTAIRES, 4, 5),
    "TLE_MATHS_EXPERTES.json": ("SRC-TLE-MATHS-EXP-2019", Level.TERMINALE, Course.MATHS_EXPERTES, 5, 5),
}


def _load(name: str) -> NotionFile:
    return NotionFile.model_validate(json.loads((MATHS_DIR / name).read_text(encoding="utf-8")))


@pytest.fixture(scope="module")
def registry():
    return load_registry()


@pytest.fixture(scope="module")
def texts(registry):
    return {sid: load_source_text(registry.sources[sid], REPO_ROOT) for sid, *_ in EXPECTED.values()}


def test_specs_cover_expected_files():
    assert {s.filename: s.source_id for s in maths_lycee.SPECS} == {k: v[0] for k, v in EXPECTED.items()}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_file_valid_and_proven(name, registry):
    sid, level, course, difficulty, minimum = EXPECTED[name]
    nf = _load(name)
    assert nf.subject == Subject.MATHS and nf.level == level and nf.course == course
    assert nf.generated_by == "pedagogy.ingest.maths_lycee"
    assert len(nf.notions) > minimum
    src = registry.sources[sid]
    for n in nf.notions:
        assert n.proof_status == ProofStatus.PROVEN_OFFICIAL
        assert n.review_status == ReviewStatus.NOT_REVIEWED
        assert n.source_id == sid
        assert n.source_sha256 == src.sha256
        assert n.course == course and n.level == level
        assert n.school_year == "2026-2027"
        assert n.difficulty == difficulty
        assert n.official_wording and n.source_page_or_section
        assert n.notion_id.startswith(f"MATHS.{level.value}.{n.domain_code}.")
        assert not any("" <= ch <= "" for ch in n.official_wording), n.notion_id


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_reverification_against_source(name, texts):
    for n in _load(name).notions:
        res = verify_notion_against_source(n, texts)
        assert res.status == ProofStatus.PROVEN_OFFICIAL, (n.notion_id, res.reasons)


def test_unique_ids_and_prerequisites_within_file():
    for name in EXPECTED:
        notions = _load(name).notions
        ids = [n.notion_id for n in notions]
        assert len(ids) == len(set(ids)), name
        local = set(ids)
        for n in notions:
            assert all(p in local for p in n.prerequisites), n.notion_id


def test_structure_and_kinds():
    nf = {name: _load(name) for name in EXPECTED}
    codes = {name: {n.domain_code for n in f.notions} for name, f in nf.items()}
    assert {"ALGO", "AUTO", "NCA", "GEO", "FON", "SP"} <= codes["2NDE.json"]
    assert {"ALGO", "AUTO", "ALG", "AN", "GEO", "PS"} <= codes["1RE_SPECIALITE.json"]
    assert {"EAUTO", "EAIC", "EALEA", "EEVOL"} <= codes["1RE_MATHS_SPECIFIQUES_1RE.json"]
    assert {"AG", "AN", "PROBA", "ALGO"} <= codes["TLE_SPECIALITE.json"]
    assert {"CAN", "CPS"} <= codes["TLE_MATHS_COMPLEMENTAIRES.json"]
    assert {"CPLX", "ARITH", "GM"} <= codes["TLE_MATHS_EXPERTES.json"]
    for f in nf.values():
        for n in f.notions:
            if n.domain_code == "AUTO":
                assert n.chapter == "Automatismes"
    # approfondissements possibles : optionnels
    wordings = {n.official_wording: n for n in nf["2NDE.json"].notions}
    assert wordings["Développement de (a + b)³."].optional_in_program is True
    assert wordings["Le nombre réel √2 est irrationnel."].optional_in_program is False
    notes = [n.provenance_note for n in nf["TLE_SPECIALITE.json"].notions]
    assert any("(contenu)" in x for x in notes) and any("(capacite)" in x for x in notes)
    assert any("(demonstration)" in x for x in notes)
    # exemples d'algorithme ignorés
    assert not any(n.official_wording.startswith("Méthode de dichotomie") for n in nf["TLE_SPECIALITE.json"].notions)


def test_known_items_present():
    w2 = {n.official_wording for n in _load("2NDE.json").notions}
    assert "Boucle bornée (for), boucle non bornée (while)." in w2
    assert "Tableau croisé d’effectifs." in w2
    we = {n.official_wording for n in _load("TLE_MATHS_EXPERTES.json").notions}
    assert "Petit théorème de Fermat." in we
    wt = {n.official_wording for n in _load("TLE_SPECIALITE.json").notions}
    assert "Point d’inflexion." in wt


def test_excerpt_builder_truncates_unreadable_formulas():
    ok, note = maths_lycee.build_excerpt(["Relation de Chasles."])
    assert ok == "Relation de Chasles." and note is None
    cut, note = maths_lycee.build_excerpt(["Formule de Moivre : cos(n ) + i"])
    assert cut == "Formule de Moivre :" and note == "tronque_pua"
    none, note = maths_lycee.build_excerpt(["Développement de", "2", "vu  , formules."])
    assert none is None and note.startswith("illisible")
    hyph, note = maths_lycee.build_excerpt(["Décrire des séries, en s’appuyant sur des couples (moyenne-",
                                             "écart type)."])
    assert hyph == "Décrire des séries, en s’appuyant sur des couples" and note == "tronque_cesure"


def test_bullet_detection():
    assert maths_lycee.is_bullet(" Vecteurs de l’espace.")
    assert maths_lycee.is_bullet("− Affectation.")
    assert not maths_lycee.is_bullet(" .")
    assert not maths_lycee.is_bullet("Contenus")


def test_deterministic_and_matches_files():
    runs = []
    for _ in range(2):
        out = {}
        for spec, b, _parsed in maths_lycee.build_all():
            notions = maths_lycee.link_sequential_prerequisites(b.notions)
            out[spec.filename] = [n.model_dump(mode="json") for n in notions]
            assert not b.rejected, spec.source_id
        runs.append(out)
    assert runs[0] == runs[1]
    for name, notions in runs[0].items():
        on_disk = json.loads((MATHS_DIR / name).read_text(encoding="utf-8"))["notions"]
        assert on_disk == notions, name
