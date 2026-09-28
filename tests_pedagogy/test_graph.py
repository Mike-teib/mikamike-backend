"""Tests du graphe pédagogique des prérequis (pedagogy.graph + CLI)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pedagogy.graph import (
    ancestors,
    build_graph,
    learning_path,
    topological_levels,
    validate_graph,
)
from pedagogy.issues import Severity
from pedagogy.models import (
    CYCLE_OF_LEVEL,
    LEVEL_RANK,
    Level,
    Notion,
    NotionFile,
    ProofStatus,
    SourceType,
    Subject,
    normalize_title,
)
from pedagogy.registry import Registry

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "prerequisite_graph_validator.py"

CODE_SUBJECT = {
    "MATHS": Subject.MATHS,
    "PC": Subject.PHYSIQUE_CHIMIE,
    "SVT": Subject.SVT,
    "ST": Subject.SCIENCES_TECHNOLOGIE,
    "ES": Subject.ENSEIGNEMENT_SCIENTIFIQUE,
}


def mk(nid: str, *, prereq=(), cross=(), child=(), related=(), proven=False) -> Notion:
    code, lv, dom, slug = nid.split(".")
    level = Level(lv)
    title = slug.replace("-", " ")
    kw = {}
    if proven:
        kw = dict(
            proof_status=ProofStatus.PROVEN_OFFICIAL,
            source_type=SourceType.OFFICIAL_BO,
            source_id="BO_TEST",
            source_page_or_section="p. 1",
            official_wording=title,
            source_sha256="0" * 64,
        )
    else:
        kw = dict(source_type=SourceType.CANDIDATE_UNVERIFIED)
    return Notion(
        notion_id=nid,
        subject=CODE_SUBJECT[code],
        level=level,
        cycle=CYCLE_OF_LEVEL[level],
        school_year="2026-2027",
        official_program_version="test",
        domain="Domaine test",
        domain_code=dom,
        chapter="Chapitre test",
        title=title,
        normalized_title=normalize_title(title),
        prerequisites=tuple(prereq),
        cross_subject_links=tuple(cross),
        child_notions=tuple(child),
        related_notions=tuple(related),
        difficulty=2,
        source_title="Source de test",
        source_url_or_ref="test",
        **kw,
    )


def reg_of(*notions: Notion) -> Registry:
    return Registry(notions={n.notion_id: n for n in notions})


def graph_of(*notions: Notion):
    return build_graph(reg_of(*notions))


def codes(issues, code=None, severity=None):
    return [i for i in issues if (code is None or i.code == code) and (severity is None or i.severity == severity)]


A6 = "MATHS.6E.NC.fractions"
A5 = "MATHS.5E.NC.fractions-operations"
A4 = "MATHS.4E.NC.puissances"
A3 = "MATHS.3E.NC.racines"
A2 = "MATHS.2NDE.NC.intervalles"
A1 = "MATHS.1RE.AN.derivation"


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #
def test_empty_registry():
    g = build_graph(Registry())
    assert g["nodes"] == [] and g["edges"] == []
    assert g["schema_version"] == "1.0" and g["generated_by"] == "pedagogy.graph"
    assert validate_graph(g) == []
    assert topological_levels(g) == []


def test_edges_types_and_direction():
    pc = "PC.4E.EL.loi-d-ohm"
    g = graph_of(
        mk(A6),
        mk(A5, prereq=[A6], related=["MATHS.5E.NC.proportionnalite"]),
        mk("MATHS.5E.NC.proportionnalite", related=[A5]),
        mk(A4, prereq=[A5], child=["MATHS.4E.NC.puissances-de-dix"]),
        mk("MATHS.4E.NC.puissances-de-dix"),
        mk(pc, cross=[A4]),
    )
    edges = {(e["from"], e["to"], e["type"]): e["level_gap"] for e in g["edges"]}
    assert edges[(A6, A5, "PREREQUISITE")] == 1
    assert edges[(A5, A4, "PREREQUISITE")] == 1
    assert edges[(A4, pc, "CROSS_SUBJECT")] == 0
    assert edges[(A4, "MATHS.4E.NC.puissances-de-dix", "CHILD")] == 0
    related = [k for k in edges if k[2] == "RELATED"]
    assert related == [(A5, "MATHS.5E.NC.proportionnalite", "RELATED")]  # une seule fois, trié
    assert g["stats"]["edges_by_type"] == {"PREREQUISITE": 2, "CROSS_SUBJECT": 1, "CHILD": 1, "RELATED": 1}
    assert [n["id"] for n in g["nodes"]] == sorted(n["id"] for n in g["nodes"])
    node = {n["id"]: n for n in g["nodes"]}[A4]
    assert set(node) == {"id", "subject", "level", "level_rank", "domain_code", "chapter", "title",
                         "proof_status", "course"}
    assert node["level_rank"] == LEVEL_RANK[Level.QUATRIEME]
    json.dumps(g)  # sérialisable


def test_determinism():
    notions = [mk(A6), mk(A5, prereq=[A6]), mk(A4, prereq=[A5], related=[A6]), mk("PC.4E.EL.tension", cross=[A4])]
    g1 = build_graph(reg_of(*notions))
    g2 = build_graph(reg_of(*reversed(notions)))
    assert json.dumps(g1, sort_keys=True) == json.dumps(g2, sort_keys=True)
    assert validate_graph(g1) == validate_graph(g2)


# --------------------------------------------------------------------------- #
# Codes d'anomalie : positifs et négatifs
# --------------------------------------------------------------------------- #
def test_graph_cycle():
    g = graph_of(
        mk("MATHS.5E.NC.aaa", prereq=["MATHS.5E.NC.ccc"]),
        mk("MATHS.5E.NC.bbb", prereq=["MATHS.5E.NC.aaa"]),
        mk("MATHS.5E.NC.ccc", prereq=["MATHS.5E.NC.bbb"]),
        mk("MATHS.5E.NC.ddd", prereq=["MATHS.5E.NC.ccc"]),
    )
    cyc = codes(validate_graph(g), "GRAPH_CYCLE")
    assert len(cyc) == 1 and cyc[0].severity == Severity.BLOCKER
    assert cyc[0].object_id == "MATHS.5E.NC.aaa"
    assert cyc[0].detail == "cycle:MATHS.5E.NC.aaa -> MATHS.5E.NC.bbb -> MATHS.5E.NC.ccc"
    with pytest.raises(ValueError):
        topological_levels(g)


def test_graph_cycle_via_child_and_negative():
    g = graph_of(mk("MATHS.5E.NC.parent", child=["MATHS.5E.NC.enfant"]),
                 mk("MATHS.5E.NC.enfant", child=["MATHS.5E.NC.parent"]))
    assert codes(validate_graph(g), "GRAPH_CYCLE")
    # RELATED ne crée pas de cycle
    g = graph_of(mk(A6, related=[A5]), mk(A5, prereq=[A6], related=[A6]))
    assert not codes(validate_graph(g), "GRAPH_CYCLE")


def test_missing_prerequisite():
    g = graph_of(mk(A5, prereq=["MATHS.6E.NC.inexistante"]), mk(A4, cross=["PC.4E.EL.absente"]))
    miss = codes(validate_graph(g), "MISSING_PREREQUISITE")
    assert {i.object_id for i in miss} == {A5, A4}
    assert all(i.severity == Severity.ERROR for i in miss)
    assert not codes(validate_graph(graph_of(mk(A6), mk(A5, prereq=[A6]))), "MISSING_PREREQUISITE")


def test_orphan_notion():
    g = graph_of(mk(A6), mk(A5, prereq=[A6]), mk("MATHS.5E.NC.seule", related=[A5]))
    orphans = codes(validate_graph(g), "ORPHAN_NOTION")
    assert [i.object_id for i in orphans] == ["MATHS.5E.NC.seule"]
    assert orphans[0].severity == Severity.INFO
    # notion du premier niveau avec arêtes sortantes : pas orpheline
    assert A6 not in {i.object_id for i in orphans}


def test_abnormal_level_jump():
    g = graph_of(mk(A6), mk(A1, prereq=[A6]))
    jumps = codes(validate_graph(g), "ABNORMAL_LEVEL_JUMP")
    assert len(jumps) == 1 and jumps[0].severity == Severity.WARNING and jumps[0].object_id == A1
    # prérequis de niveau supérieur → ERROR
    g = graph_of(mk(A4), mk(A5, prereq=[A4]))
    jumps = codes(validate_graph(g), "ABNORMAL_LEVEL_JUMP")
    assert len(jumps) == 1 and jumps[0].severity == Severity.ERROR
    # écart de 2 : normal ; CROSS_SUBJECT exclu
    g = graph_of(mk(A6), mk(A4, prereq=[A6]), mk("PC.1RE.EL.energie", cross=[A6]))
    assert not codes(validate_graph(g), "ABNORMAL_LEVEL_JUMP")


def test_cross_subject_not_lower_or_equal():
    g = graph_of(mk(A1), mk("PC.2NDE.MV.vitesse", cross=[A1]))
    errs = codes(validate_graph(g), "CROSS_SUBJECT_NOT_LOWER_OR_EQUAL")
    assert len(errs) == 1 and errs[0].severity == Severity.ERROR and errs[0].object_id == "PC.2NDE.MV.vitesse"
    g = graph_of(mk(A2), mk("PC.2NDE.MV.vitesse", cross=[A2]))
    assert not codes(validate_graph(g), "CROSS_SUBJECT_NOT_LOWER_OR_EQUAL")


def test_dependency_on_unproven():
    g = graph_of(mk(A6), mk("MATHS.6E.NC.decimaux"), mk(A5, prereq=[A6, "MATHS.6E.NC.decimaux"], proven=True))
    dep = codes(validate_graph(g), "DEPENDENCY_ON_UNPROVEN")
    assert len(dep) == 1 and dep[0].object_id == A5 and dep[0].severity == Severity.INFO
    assert A6 in dep[0].detail and "MATHS.6E.NC.decimaux" in dep[0].detail  # agrégé
    g = graph_of(mk(A6, proven=True), mk(A5, prereq=[A6], proven=True), mk(A4, prereq=[A5]))
    assert not codes(validate_graph(g), "DEPENDENCY_ON_UNPROVEN")


def test_disconnected_subject_level():
    g = graph_of(mk(A6), mk("MATHS.6E.NC.decimaux", prereq=[A6]),
                 mk(A5), mk("MATHS.5E.NC.relatifs", prereq=[A5]))
    dis = codes(validate_graph(g), "DISCONNECTED_SUBJECT_LEVEL")
    assert [i.object_id for i in dis] == ["MATHS.5E"] and dis[0].severity == Severity.WARNING
    # connecté → rien ; niveau précédent absent → rien
    g = graph_of(mk(A6), mk(A5, prereq=[A6]), mk(A3))
    assert not codes(validate_graph(g), "DISCONNECTED_SUBJECT_LEVEL")
    # un lien d'une autre matière ne compte pas pour la même matière
    g = graph_of(mk("PC.5E.MA.etats"), mk("PC.4E.MA.atomes"), mk(A5), mk("PC.4E.EL.circuit", cross=[A5]))
    assert [i.object_id for i in codes(validate_graph(g), "DISCONNECTED_SUBJECT_LEVEL")] == ["PC.4E"]


def test_clean_graph_has_no_error():
    g = graph_of(mk(A6), mk(A5, prereq=[A6]), mk(A4, prereq=[A5]), mk("PC.4E.EL.circuit", cross=[A4]))
    issues = validate_graph(g)
    assert not [i for i in issues if i.severity in (Severity.BLOCKER, Severity.ERROR, Severity.WARNING)]


# --------------------------------------------------------------------------- #
# Parcours
# --------------------------------------------------------------------------- #
def test_learning_path_across_levels_and_subjects():
    pc = "PC.4E.EL.loi-d-ohm"
    g = graph_of(
        mk(A6), mk(A5, prereq=[A6]), mk(A4, prereq=[A5]),
        mk(pc, cross=[A4], prereq=["PC.5E.EL.circuit"]), mk("PC.5E.EL.circuit"),
        mk("MATHS.6E.NC.sans-rapport"),
    )
    assert ancestors(g, A4) == sorted([A6, A5])
    assert ancestors(g, pc) == sorted([A6, A5, A4, "PC.5E.EL.circuit"])
    assert learning_path(g, A4, set()) == [A6, A5, A4]
    path = learning_path(g, pc, set())
    assert path[-1] == pc and set(path[:-1]) == {A6, A5, A4, "PC.5E.EL.circuit"}
    assert path.index(A6) < path.index(A5) < path.index(A4)
    # maîtrise de la 5E : on ne remonte pas à la 6E
    assert learning_path(g, pc, {A5, "PC.5E.EL.circuit"}) == [A4, pc]
    assert learning_path(g, A4, {A6}) == [A5, A4]
    with pytest.raises(KeyError):
        learning_path(g, "MATHS.6E.NC.inconnue", set())


def test_topological_levels():
    g = graph_of(mk(A6), mk(A5, prereq=[A6]), mk(A4, prereq=[A5]), mk("PC.4E.EL.circuit", cross=[A4]))
    assert topological_levels(g) == [[A6], [A5], [A4], ["PC.4E.EL.circuit"]]


def test_long_chain_5000_nodes():
    n = 5000
    ids = [f"MATHS.5E.NC.n{i:05d}" for i in range(n)]
    notions = [mk(ids[0])] + [mk(ids[i], prereq=[ids[i - 1]]) for i in range(1, n)]
    t0 = time.perf_counter()
    g = build_graph(reg_of(*notions))
    issues = validate_graph(g)
    layers = topological_levels(g)
    anc = ancestors(g, ids[-1])
    path = learning_path(g, ids[-1], set())
    elapsed = time.perf_counter() - t0
    assert not codes(issues, "GRAPH_CYCLE")
    assert len(layers) == n and len(anc) == n - 1 and path == ids
    assert elapsed < 20
    # un cycle long est détecté sans RecursionError
    looped = notions[:]
    looped[0] = mk(ids[0], prereq=[ids[-1]])
    cyc = codes(validate_graph(build_graph(reg_of(*looped))), "GRAPH_CYCLE")
    assert len(cyc) == 1 and cyc[0].detail.count("->") == n - 1


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def write_data(data_dir: Path, notions):
    by_file = {}
    for n in notions:
        by_file.setdefault((n.subject, n.level), []).append(n)
    for (subject, level), ns in by_file.items():
        nf = NotionFile(subject=subject, level=level, generated_by="tests", disclaimer="fichier de test fictif",
                        notions=tuple(ns))
        path = data_dir / "notions" / subject.value.lower() / f"{level.value.lower()}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(nf.model_dump_json(), encoding="utf-8")


def run_cli(*args):
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, cwd="/", timeout=120)


def test_cli_ok_and_graph_out(tmp_path):
    data = tmp_path / "data"
    write_data(data, [mk(A6), mk(A5, prereq=[A6]), mk("PC.5E.EL.circuit", cross=[A5])])
    r = run_cli("--data-dir", str(data), "--check-only")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "noeuds : 3" in r.stdout
    out = tmp_path / "g.json"
    r = run_cli("--data-dir", str(data), "--graph-out", str(out))
    assert r.returncode == 0
    g = json.loads(out.read_text(encoding="utf-8"))
    assert len(g["nodes"]) == 3 and len(g["edges"]) == 2


def test_cli_fails_on_cycle_and_error(tmp_path):
    data = tmp_path / "cyc"
    write_data(data, [mk("MATHS.5E.NC.aaa", prereq=["MATHS.5E.NC.bbb"]), mk("MATHS.5E.NC.bbb", prereq=["MATHS.5E.NC.aaa"])])
    r = run_cli("--data-dir", str(data), "--check-only")
    assert r.returncode == 1 and "GRAPH_CYCLE" in r.stdout
    data = tmp_path / "miss"
    write_data(data, [mk(A5, prereq=["MATHS.6E.NC.absente"])])
    out = tmp_path / "none.json"
    r = run_cli("--data-dir", str(data), "--check-only", "--graph-out", str(out))
    assert r.returncode == 1 and "MISSING_PREREQUISITE" in r.stdout
    assert not out.exists()


def test_cli_empty_data_dir(tmp_path):
    r = run_cli("--data-dir", str(tmp_path), "--check-only")
    assert r.returncode == 0 and "noeuds : 0" in r.stdout
