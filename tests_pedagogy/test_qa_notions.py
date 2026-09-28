"""Tests de pedagogy.validators.notions (données fictives)."""

from __future__ import annotations

import hashlib
import json

import pytest

from pedagogy.issues import Severity
from pedagogy.registry import load_registry
from pedagogy.validators.notions import validate_registry_notions

try:
    from tests_pedagogy.pdf_fixture import make_pdf
    from tests_pedagogy.qa_fixtures import notion, notion_dict, notion_file, registry, source_dict, write_data_dir
except ImportError:  # pragma: no cover — exécution depuis tests_pedagogy/
    from pdf_fixture import make_pdf
    from qa_fixtures import notion, notion_dict, notion_file, registry, source_dict, write_data_dir


def codes(issues):
    return {i.code for i in issues}


def by_code(issues, code):
    return [i for i in issues if i.code == code]


def test_clean_registry_only_expected_infos():
    reg = registry([notion("Fractions simples")])
    issues = validate_registry_notions(reg)
    assert codes(issues) == {"NOTION_UNPROVEN", "NOTIONS_UNPROVEN_SUMMARY", "SOURCE_NOT_RETRIEVED"}
    assert all(i.severity == Severity.INFO for i in issues)
    summary = by_code(issues, "NOTIONS_UNPROVEN_SUMMARY")[0]
    assert summary.detail == "unproven=1/total=1"


def test_empty_registry_no_issue():
    assert validate_registry_notions(registry([])) == []


def test_load_error(tmp_path):
    data = write_data_dir(tmp_path, {"maths/6e.json": "{pas du json"}, [source_dict()])
    reg = load_registry(data)
    issues = validate_registry_notions(reg)
    le = by_code(issues, "LOAD_ERROR")
    assert le and le[0].severity == Severity.BLOCKER and le[0].object_id.endswith("6e.json")


def test_load_error_duplicate_notion_id_across_files(tmp_path):
    nd = notion_dict("Fractions simples")
    data = write_data_dir(tmp_path, {"a.json": notion_file("MATHS", "6E", [nd]),
                                     "b.json": notion_file("MATHS", "6E", [nd])}, [source_dict()])
    issues = validate_registry_notions(load_registry(data))
    assert any("notion_id_duplique" in i.detail for i in by_code(issues, "LOAD_ERROR"))


def test_conflict_and_proven_internal():
    reg = registry([
        notion("Fractions simples", proof_status="CONFLICT"),
        notion("Aires", proof_status="PROVEN_INTERNAL", source_type="INTERNAL_VALIDATED"),
    ])
    issues = validate_registry_notions(reg)
    assert [i.severity for i in by_code(issues, "NOTION_CONFLICT")] == [Severity.ERROR]
    assert len(by_code(issues, "NOTION_UNPROVEN")) == 1


def test_deprecated_in_use():
    old = notion("Ancienne notion", proof_status="DEPRECATED")
    user = notion("Nouvelle notion", prerequisites=(old.notion_id,))
    dep_user = notion("Autre ancienne", proof_status="DEPRECATED", prerequisites=(old.notion_id,))
    issues = validate_registry_notions(registry([old, user, dep_user]))
    hits = by_code(issues, "NOTION_DEPRECATED_IN_USE")
    assert [i.object_id for i in hits] == [user.notion_id]
    assert hits[0].severity == Severity.ERROR


def test_without_source():
    a = notion("Fractions simples", source_id="SRC-INCONNUE")
    b = notion("Aires", source_url_or_ref="   ")
    c = notion("Volumes", source_id=None)
    d = notion("Legacy", source_id=None, source_type="LEGACY_MIKAMIKE")
    issues = validate_registry_notions(registry([a, b, c, d]))
    ids = {i.object_id for i in by_code(issues, "NOTION_WITHOUT_SOURCE")}
    assert ids == {a.notion_id, b.notion_id, c.notion_id}


def test_source_not_retrieved_only_for_expected(tmp_path):
    f = tmp_path / "prog.txt"
    f.write_text("texte", encoding="utf-8")
    sha = hashlib.sha256(f.read_bytes()).hexdigest()
    src = source_dict("SRC-OK", retrieval="RETRIEVED", local_path="prog.txt", sha256=sha)
    n_ok = notion("Fractions simples", source_id="SRC-OK")
    n_exp = notion("Aires")
    issues = validate_registry_notions(registry([n_ok, n_exp], sources=[source_dict(), src]), root=tmp_path)
    assert {i.object_id for i in by_code(issues, "SOURCE_NOT_RETRIEVED")} == {n_exp.notion_id}


def test_prerequisite_checks():
    base6 = notion("Fractions simples")
    high = notion("Calcul litteral", level="5E")
    pc = notion("Etats de la matiere", subject="PHYSIQUE_CHIMIE", level="5E")
    n = notion("Aires", prerequisites=("MATHS.6E.NC.inexistante", high.notion_id, base6.notion_id))
    n5 = notion("Proportionnalite", level="5E", prerequisites=(pc.notion_id, base6.notion_id))
    issues = validate_registry_notions(registry([base6, high, pc, n, n5],
                                                sources=[source_dict(levels=("6E", "5E"), subjects=("MATHS", "PHYSIQUE_CHIMIE"))]))
    assert [(i.object_id, i.detail) for i in by_code(issues, "PREREQUISITE_UNKNOWN")] == [(n.notion_id, "MATHS.6E.NC.inexistante")]
    assert [i.object_id for i in by_code(issues, "PREREQUISITE_HIGHER_LEVEL")] == [n.notion_id]
    cross = by_code(issues, "PREREQUISITE_CROSS_SUBJECT")
    assert [i.object_id for i in cross] == [n5.notion_id] and cross[0].severity == Severity.WARNING


def test_st_prerequisite_is_same_lineage_for_pc_svt():
    st = notion("Les etats de la matiere", subject="SCIENCES_TECHNOLOGIE", domain_code="MME")
    pc = notion("Changements d'etat", subject="PHYSIQUE_CHIMIE", level="5E", prerequisites=(st.notion_id,))
    m = notion("Proportionnalite", level="5E", prerequisites=(st.notion_id,))
    src = source_dict(subjects=("MATHS", "PHYSIQUE_CHIMIE", "SCIENCES_TECHNOLOGIE"), levels=("6E", "5E"))
    issues = validate_registry_notions(registry([st, pc, m], sources=[src]))
    assert [i.object_id for i in by_code(issues, "PREREQUISITE_CROSS_SUBJECT")] == [m.notion_id]


def test_cross_link_checks():
    m = notion("Proportionnalite", level="5E")
    m_high = notion("Fonctions lineaires", level="4E")
    pc = notion("Vitesse", subject="PHYSIQUE_CHIMIE", level="5E",
                cross_subject_links=(m.notion_id, m_high.notion_id, "MATHS.5E.NC.absente"))
    src = source_dict(subjects=("MATHS", "PHYSIQUE_CHIMIE"), levels=("5E", "4E"))
    issues = validate_registry_notions(registry([m, m_high, pc], sources=[src]))
    assert [i.detail for i in by_code(issues, "CROSS_LINK_UNKNOWN")] == ["MATHS.5E.NC.absente"]
    assert [i.object_id for i in by_code(issues, "CROSS_LINK_HIGHER_LEVEL")] == [pc.notion_id]
    assert not by_code(issues, "PREREQUISITE_CROSS_SUBJECT")


def test_duplicate_and_near_duplicate_titles():
    a = notion("Addition des fractions", domain_code="NC")
    b = notion("Addition des fractions", domain_code="GM")          # même titre, autre domaine
    c = notion("Addition des fractions décimales", domain_code="NC")  # proche ? 3/4 = 0.75 < 0.8
    d = notion("Addition de fractions simples positives", domain_code="NC")
    e = notion("Addition de fractions simples positives entières", domain_code="GM")  # 5/6 >= 0.8 avec d
    other_level = notion("Addition des fractions", level="5E")
    issues = validate_registry_notions(registry([a, b, c, d, e, other_level],
                                                sources=[source_dict(levels=("6E", "5E"))]))
    dup = by_code(issues, "DUPLICATE_TITLE_SAME_LEVEL")
    assert len(dup) == 1 and dup[0].severity == Severity.WARNING
    assert {dup[0].object_id} <= {a.notion_id, b.notion_id}
    near = by_code(issues, "NEAR_DUPLICATE_TITLE")
    pairs = {frozenset((i.object_id, i.detail.split(":")[1])) for i in near}
    assert pairs == {frozenset((d.notion_id, e.notion_id))}
    assert all(i.severity == Severity.INFO for i in near)


def test_school_year_outside_source():
    src = source_dict(school_year_start="2020-2021", school_year_end="2023-2024")
    before = notion("Aires", school_year="2019-2020")
    after = notion("Volumes", school_year="2025-2026")
    inside = notion("Durees", school_year="2022-2023")
    issues = validate_registry_notions(registry([before, after, inside], sources=[src]))
    assert {i.object_id for i in by_code(issues, "SCHOOL_YEAR_OUTSIDE_SOURCE")} == {before.notion_id, after.notion_id}


def test_source_subject_level_mismatch():
    src = source_dict(subjects=("MATHS",), levels=("6E",))
    bad = notion("Proportionnalite", level="5E")
    bad_subj = notion("Cellule", subject="SVT", level="5E")
    ok = notion("Aires")
    issues = validate_registry_notions(registry([bad, bad_subj, ok], sources=[src]))
    hits = by_code(issues, "SOURCE_SUBJECT_LEVEL_MISMATCH")
    assert {i.object_id for i in hits} == {bad.notion_id, bad_subj.notion_id}
    assert any("matiere:SVT" in i.detail for i in hits)


def test_empty_pedagogy():
    n = notion("Aires", learning_objectives=(), common_mistakes=())
    m = notion("Volumes", common_mistakes=())
    ok = notion("Durees")
    issues = validate_registry_notions(registry([n, m, ok]))
    hits = {i.object_id: i.detail for i in by_code(issues, "EMPTY_PEDAGOGY")}
    assert hits == {n.notion_id: "learning_objectives,common_mistakes", m.notion_id: "common_mistakes"}


# --------------------------------------------------------------------------- #
# Preuve officielle recalculée (PDF fictif)
# --------------------------------------------------------------------------- #
WORDING = "Comparer, ranger et encadrer des fractions simples"


def _proven_setup(tmp_path, wording=WORDING, page="2", tamper=False, notion_sha=None, retrieval="RETRIEVED"):
    pdf = make_pdf(["Page de garde du programme fictif", f"Nombres et calculs\n{WORDING}.\nAutre ligne"])
    (tmp_path / "src").mkdir()
    path = tmp_path / "src" / "prog.pdf"
    path.write_bytes(pdf)
    sha = hashlib.sha256(pdf).hexdigest()
    if tamper:
        path.write_bytes(pdf + b"\n% altere\n")
    src = source_dict("SRC-PDF", retrieval=retrieval, local_path="src/prog.pdf" if retrieval != "EXPECTED" else "",
                      sha256=sha if retrieval != "EXPECTED" else "")
    n = notion("Fractions simples", source_id="SRC-PDF", proof_status="PROVEN_OFFICIAL", official_wording=wording,
               source_page_or_section=page, source_sha256=notion_sha or sha)
    return registry([n], sources=[src]), n


def test_proof_verifiable_positive(tmp_path):
    reg, n = _proven_setup(tmp_path)
    issues = validate_registry_notions(reg, root=tmp_path)
    assert "PROOF_NOT_VERIFIABLE" not in codes(issues)
    assert "SOURCE_UNREADABLE" not in codes(issues)
    assert "NOTION_UNPROVEN" not in codes(issues)


@pytest.mark.parametrize("kw,expected_reason", [
    ({"page": "1"}, "CONFLICT"),                                   # libellé présent mais à une autre page
    ({"wording": "Libellé inventé absent du document"}, "UNPROVEN"),
    ({"notion_sha": "0" * 64}, "CONFLICT"),                        # empreinte de la notion différente
    ({"tamper": True}, "UNPROVEN"),                                # fichier modifié → source illisible
    ({"retrieval": "EXPECTED"}, "UNPROVEN"),                       # source non récupérée
])
def test_proof_not_verifiable(tmp_path, kw, expected_reason):
    reg, n = _proven_setup(tmp_path, **kw)
    issues = validate_registry_notions(reg, root=tmp_path)
    hits = by_code(issues, "PROOF_NOT_VERIFIABLE")
    assert [i.object_id for i in hits] == [n.notion_id]
    assert hits[0].severity == Severity.BLOCKER
    assert hits[0].detail.startswith(f"recalcul={expected_reason}")
    if kw.get("tamper"):
        su = by_code(issues, "SOURCE_UNREADABLE")
        assert su and "sha256_different" in su[0].detail


def test_published_forbidden():
    # PUBLISHED exige PROVEN_OFFICIAL + APPROVED côté modèle : notion construite puis ajoutée telle quelle.
    n = notion("Fractions simples", proof_status="PROVEN_OFFICIAL", official_wording="x" * 10,
               source_page_or_section="1", source_sha256="a" * 64, review_status="APPROVED",
               publication_status="PUBLISHED")
    reg = registry([n])
    issues = validate_registry_notions(reg)
    assert [i.severity for i in by_code(issues, "PUBLISHED_FORBIDDEN")] == [Severity.BLOCKER]
    ok = registry([notion("Aires")])
    assert "PUBLISHED_FORBIDDEN" not in codes(validate_registry_notions(ok))


def test_deterministic_order():
    ns = [notion(t, learning_objectives=()) for t in ("Zeta notion", "Alpha notion", "Mu notion")]
    a = validate_registry_notions(registry(ns))
    b = validate_registry_notions(registry(list(reversed(ns))))
    assert a == b
    assert json.dumps([i.as_dict() for i in a]) == json.dumps([i.as_dict() for i in b])
