"""Matrice de couverture (Phase 2) et correspondance des notions historiques."""

import csv
import io
import json

from pedagogy.coverage import COLUMNS, build_rows, main as coverage_main, to_csv
from pedagogy.legacy import _incompatible, build_map
from pedagogy.models import SUBJECT_LEVELS, Level, Subject
from pedagogy.registry import load_registry

REQUIRED = ["SUBJECT", "LEVEL", "DOMAIN", "CHAPTER", "NOTION_ID", "NOTION_TITLE", "PROOF_STATUS", "SOURCE",
            "EXERCISES_COUNT", "QUIZ_COUNT", "QA_STATUS"]


def test_matrix_columns_and_rows():
    reg = load_registry()
    rows = build_rows(reg)
    assert all(c in COLUMNS for c in REQUIRED)
    parsed = list(csv.DictReader(io.StringIO(to_csv(rows))))
    assert len(parsed) == len(rows)
    ids = [r["NOTION_ID"] for r in parsed if r["NOTION_ID"]]
    assert len(ids) == len(set(ids)) == len(reg.notions)


def test_matrix_never_invents_a_6e_pc_or_svt():
    rows = build_rows(load_registry())
    for subj in (Subject.PHYSIQUE_CHIMIE, Subject.SVT):
        cell = [r for r in rows if r["SUBJECT"] == subj.value and r["LEVEL"] == Level.SIXIEME.value]
        assert len(cell) == 1 and cell[0]["QA_STATUS"] == "NOT_APPLICABLE" and not cell[0]["NOTION_ID"]
        assert "Sciences et technologie" in cell[0]["NOTION_TITLE"]
    na = {(r["SUBJECT"], r["LEVEL"]) for r in rows if r["QA_STATUS"] == "NOT_APPLICABLE"}
    for s, levels in SUBJECT_LEVELS.items():
        for lv in levels:
            assert (s.value, lv.value) not in na


def test_unproven_notions_are_blocked_and_have_no_content():
    for r in build_rows(load_registry()):
        if r["NOTION_ID"] and r["PROOF_STATUS"] != "PROVEN_OFFICIAL":
            assert r["QA_STATUS"].startswith("BLOCKED_")
            assert r["EXERCISES_COUNT"] == "0" and r["QUIZ_COUNT"] == "0"


def test_coverage_cli_is_deterministic(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert coverage_main(["--out-dir", str(a)]) == 0
    assert coverage_main(["--out-dir", str(b)]) == 0
    for f in ("PEDAGOGY_COVERAGE_MATRIX.csv", "PEDAGOGY_COVERAGE_REPORT.md"):
        assert (a / f).read_bytes() == (b / f).read_bytes()


def test_legacy_incompatible_words():
    assert _incompatible("Réciproque du théorème de Pythagore", "Réciproque du théorème de Thalès")
    assert _incompatible("Équations du 2nd degré", "Équations du premier degré")
    assert not _incompatible("Équations du 1er degré", "Équations du premier degré")


def test_legacy_map_covers_all_47_and_never_proves():
    reg = load_registry()
    entries = build_map(list(reg.notions.values()))
    assert len(entries) == 47
    assert len({e["legacy_id"] for e in entries}) == 47
    for e in entries:
        for c in e["candidates"]:
            assert c in reg.notions
        if e["legacy_level"] == "primaire":
            assert e["status"] == "LEVEL_AMBIGUOUS"


def test_committed_legacy_map_is_up_to_date():
    from pedagogy.registry import DATA_DIR
    doc = json.loads((DATA_DIR / "legacy" / "legacy_notions_map.json").read_text(encoding="utf-8"))
    assert doc["entries"] == json.loads(json.dumps(build_map(list(load_registry().notions.values())),
                                                   ensure_ascii=False))
