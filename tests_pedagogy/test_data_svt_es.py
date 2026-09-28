"""
Registre candidat SVT (5e → Tle) et Enseignement scientifique (1re, Tle).
Vérifie la validité des fichiers, l'honnêteté de la provenance (aucune notion prouvée,
aucun libellé officiel), la cohérence des prérequis et des liens inter-matières, et les
plans pilotes (bloqués tant qu'aucune notion n'est PROVEN_OFFICIAL).
"""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from pedagogy.models import (  # noqa: E402
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
)
from pedagogy.registry import DATA_DIR, load_registry  # noqa: E402

NOTIONS = DATA_DIR / "notions"
PILOT = DATA_DIR / "pilot"

SVT_FILES = {
    "5E": ("SVT/5E.json", Course.COMMON),
    "4E": ("SVT/4E.json", Course.COMMON),
    "3E": ("SVT/3E.json", Course.COMMON),
    "2NDE": ("SVT/2NDE.json", Course.COMMON),
    "1RE": ("SVT/1RE_SPECIALITE.json", Course.SPECIALITE),
    "TLE": ("SVT/TLE_SPECIALITE.json", Course.SPECIALITE),
}
ES_FILES = {
    "1RE": ("ES/1RE_ENSEIGNEMENT_SCIENTIFIQUE.json", Course.ENSEIGNEMENT_SCIENTIFIQUE),
    "TLE": ("ES/TLE_ENSEIGNEMENT_SCIENTIFIQUE.json", Course.ENSEIGNEMENT_SCIENTIFIQUE),
}
ALL = [(Subject.SVT, lv, f, c) for lv, (f, c) in SVT_FILES.items()] + [
    (Subject.ENSEIGNEMENT_SCIENTIFIQUE, lv, f, c) for lv, (f, c) in ES_FILES.items()
]
COMPETENCIES = {
    "PRATIQUER_DEMARCHE_SCIENTIFIQUE", "CONCEVOIR_EXPERIENCE", "UTILISER_OUTILS", "PRATIQUER_LANGAGES",
    "ADOPTER_COMPORTEMENT_RESPONSABLE", "SE_SITUER_DANS_ESPACE_TEMPS", "COMMUNIQUER",
}
SUBJECT_OF_CODE = {"MATHS": "MATHS", "PC": "PHYSIQUE_CHIMIE", "SVT": "SVT", "ST": "SCIENCES_TECHNOLOGIE",
                   "ES": "ENSEIGNEMENT_SCIENTIFIQUE"}


def _load(rel):
    return NotionFile.model_validate(json.loads((NOTIONS / rel).read_text(encoding="utf-8")))


def _all_notions():
    for subj, lv, rel, course in ALL:
        for n in _load(rel).notions:
            yield n


@pytest.fixture(scope="module")
def registry():
    return load_registry()


@pytest.mark.parametrize("subject,level,rel,course", ALL, ids=[a[2] for a in ALL])
def test_file_validates(subject, level, rel, course):
    nf = _load(rel)
    assert nf.subject == subject and nf.level == Level(level) and nf.course == course
    lo, hi = (12, 20) if subject == Subject.SVT else (8, 15)
    assert lo <= len(nf.notions) <= hi


def test_no_svt_in_6e():
    assert not (NOTIONS / "SVT" / "6E.json").exists()
    assert not any(p.name.startswith("6E") for p in (NOTIONS / "SVT").glob("*.json"))


def test_es_only_1re_tle():
    names = sorted(p.name for p in (NOTIONS / "ES").glob("*.json"))
    assert names == ["1RE_ENSEIGNEMENT_SCIENTIFIQUE.json", "TLE_ENSEIGNEMENT_SCIENTIFIQUE.json"]


def test_all_candidates_unproven():
    for n in _all_notions():
        assert n.proof_status == ProofStatus.UNPROVEN
        assert n.source_type == SourceType.CANDIDATE_UNVERIFIED
        assert n.official_wording is None
        assert n.review_status == ReviewStatus.NOT_REVIEWED
        assert n.publication_status == PublicationStatus.DRAFT
        assert n.source_sha256 is None
        assert not n.eligible_for_content
        assert "non vérifié" in n.provenance_note and n.source_id in n.provenance_note
        assert "Aucun libellé officiel stocké" in n.provenance_note


def test_ids_stable_unique_and_fields(registry):
    seen = set()
    for n in _all_notions():
        assert n.notion_id == make_notion_id(n.subject, n.level, n.domain_code, n.title)
        assert n.notion_id not in seen
        seen.add(n.notion_id)
        assert n.school_year == "2025-2026"
        assert 1 <= n.difficulty <= 5
        assert n.learning_objectives and n.expected_skills and n.common_mistakes and n.competency_ids
        assert set(n.competency_ids) <= COMPETENCIES
        src = registry.sources[n.source_id]
        assert n.subject in src.subjects and n.level in src.levels
        assert n.source_title == src.title and n.source_url_or_ref == src.reference
    assert not [e for e in registry.load_errors if e[0].startswith(("notions/SVT", "notions/ES"))]


def test_prerequisites_exist_and_not_higher(registry):
    for n in _all_notions():
        for p in n.prerequisites:
            assert p in registry.notions, (n.notion_id, p)
            pre = registry.notions[p]
            assert pre.subject == n.subject, (n.notion_id, p)
            assert LEVEL_RANK[pre.level] <= LEVEL_RANK[n.level], (n.notion_id, p)


def test_cross_subject_links(registry):
    links = {(n.notion_id, x) for n in _all_notions() for x in n.cross_subject_links}
    needed_subjects = {SUBJECT_OF_CODE[x.split(".")[0]] for _, x in links}
    present = {n.subject.value for n in registry.notions.values()}
    missing = needed_subjects - present
    if missing:
        pytest.skip(f"Fichiers de notions absents pour {sorted(missing)} (rédigés en parallèle par d'autres agents) : "
                    "vérification des cross_subject_links reportée.")
    for nid, x in links:
        assert x in registry.notions, f"{nid} → lien inter-matières inexistant {x}"
        src_level = registry.notions[nid].level
        assert LEVEL_RANK[registry.notions[x].level] <= LEVEL_RANK[src_level], (nid, x)


def test_cross_subject_links_not_higher_level():
    for n in _all_notions():
        for x in n.cross_subject_links:
            assert LEVEL_RANK[Level(x.split(".")[1])] <= LEVEL_RANK[n.level], (n.notion_id, x)


@pytest.mark.parametrize("fname,subject,levels", [
    ("SVT_pilot_plan.json", "SVT", ["5E", "4E", "3E", "2NDE", "1RE", "TLE"]),
    ("ES_pilot_plan.json", "ENSEIGNEMENT_SCIENTIFIQUE", ["1RE", "TLE"]),
])
def test_pilot_plans(registry, fname, subject, levels):
    plan = json.loads((PILOT / fname).read_text(encoding="utf-8"))
    assert plan["subject"] == subject
    assert plan["status"] == "BLOCKED_NO_PROVEN_NOTION"
    assert plan["rule"] == "exercises only for PROVEN_OFFICIAL notions"
    assert sorted(plan["levels"]) == sorted(levels)
    valid_types = {t.value for t in ExerciseType}
    for lv, items in plan["levels"].items():
        assert len(items) == 3
        assert len({i["notion_id"] for i in items}) == 3
        for it in items:
            n = registry.notions[it["notion_id"]]
            assert n.subject.value == subject and n.level.value == lv
            types = it["planned_exercise_types"]
            assert 3 <= len(types) <= 4 and len(set(types)) == len(types)
            assert set(types) <= valid_types
            assert it["why"].strip()
            assert set(it) == {"notion_id", "planned_exercise_types", "why"}  # aucun contenu d'exercice
            assert not n.eligible_for_content  # d'où le statut BLOQUÉ
