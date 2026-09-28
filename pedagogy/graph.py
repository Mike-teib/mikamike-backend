"""
graph.py — Graphe pédagogique des prérequis (6e → Terminale, toutes matières).

Sens des arêtes : prérequis → notion dépendante.
  - PREREQUISITE  : n.prerequisites          (p → n)
  - CROSS_SUBJECT : n.cross_subject_links    (notion liée d'une autre matière → n)
  - CHILD         : n.child_notions          (parent n → enfant)
  - RELATED       : n.related_notions        (non orienté, stocké une fois, extrémités triées)

Tout est déterministe (nœuds et arêtes triés) et sérialisable en JSON. Aucun parcours
récursif : les algorithmes (Tarjan, Kahn, BFS) sont itératifs, donc sans limite de
profondeur de pile.
"""

from __future__ import annotations

import heapq
import re
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

from pedagogy.issues import Issue, Severity
from pedagogy.models import LEVEL_ORDER, LEVEL_RANK, Level, Notion, ProofStatus, SUBJECT_CODE

SCHEMA_VERSION = "1.0"
GENERATED_BY = "pedagogy.graph"

PREREQUISITE = "PREREQUISITE"
CROSS_SUBJECT = "CROSS_SUBJECT"
CHILD = "CHILD"
RELATED = "RELATED"
EDGE_TYPES: Tuple[str, ...] = (PREREQUISITE, CROSS_SUBJECT, CHILD, RELATED)

#: arêtes qui imposent un ordre d'apprentissage (détection de cycles, ordre topologique)
ORDER_TYPES = frozenset({PREREQUISITE, CROSS_SUBJECT, CHILD})
#: arêtes de dépendance au sens « il faut maîtriser A avant B » (remontée aux prérequis)
DEPENDENCY_TYPES = frozenset({PREREQUISITE, CROSS_SUBJECT})

MAX_NORMAL_LEVEL_GAP = 2

_LEVEL_BY_VALUE = {lv.value: lv for lv in Level}
_ID_LEVEL_RE = re.compile(r"^[A-Z]+\.(6E|5E|4E|3E|2NDE|1RE|TLE)\.")


def _rank_from_id(notion_id: str) -> Optional[int]:
    m = _ID_LEVEL_RE.match(notion_id or "")
    return LEVEL_RANK[_LEVEL_BY_VALUE[m.group(1)]] if m else None


def _enum_value(x: Any) -> Any:
    return getattr(x, "value", x)


# --------------------------------------------------------------------------- #
# Construction
# --------------------------------------------------------------------------- #
def _notions_of(reg: Any) -> List[Notion]:
    if hasattr(reg, "notions"):
        notions = reg.notions
    else:
        notions = reg
    if isinstance(notions, Mapping):
        items = list(notions.values())
    else:
        items = list(notions)
    return sorted(items, key=lambda n: n.notion_id)


def build_graph(reg: Any) -> Dict[str, Any]:
    """Construit le graphe à partir d'un Registry (ou d'un dict/itérable de Notion)."""
    notions = _notions_of(reg)
    nodes: List[Dict[str, Any]] = []
    rank: Dict[str, int] = {}
    for n in notions:
        r = LEVEL_RANK[n.level]
        rank[n.notion_id] = r
        nodes.append({
            "id": n.notion_id,
            "subject": _enum_value(n.subject),
            "level": _enum_value(n.level),
            "level_rank": r,
            "domain_code": n.domain_code,
            "chapter": n.chapter,
            "title": n.title,
            "proof_status": _enum_value(n.proof_status),
            "course": _enum_value(n.course),
        })

    def gap(src: str, dst: str) -> int:
        a = rank.get(src, _rank_from_id(src))
        b = rank.get(dst, _rank_from_id(dst))
        return 0 if a is None or b is None else b - a

    edge_keys: Set[Tuple[str, str, str]] = set()
    for n in notions:
        nid = n.notion_id
        for p in n.prerequisites:
            edge_keys.add((p, nid, PREREQUISITE))
        for c in n.cross_subject_links:
            if c != nid:
                edge_keys.add((c, nid, CROSS_SUBJECT))
        for c in n.child_notions:
            if c != nid:
                edge_keys.add((nid, c, CHILD))
        for r in n.related_notions:
            if r != nid:
                a, b = sorted((nid, r))
                edge_keys.add((a, b, RELATED))

    edges = [
        {"from": f, "to": t, "type": ty, "level_gap": gap(f, t)}
        for f, t, ty in sorted(edge_keys, key=lambda k: (k[0], k[1], EDGE_TYPES.index(k[2])))
    ]

    edges_by_type = {t: 0 for t in EDGE_TYPES}
    for e in edges:
        edges_by_type[e["type"]] += 1
    by_subject_level: Dict[str, int] = defaultdict(int)
    by_proof: Dict[str, int] = defaultdict(int)
    for nd in nodes:
        by_subject_level[f"{nd['subject']}|{nd['level']}"] += 1
        by_proof[nd["proof_status"]] += 1
    node_ids = set(rank)
    stats = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "edges_by_type": edges_by_type,
        "nodes_by_subject_level": dict(sorted(by_subject_level.items())),
        "nodes_by_proof_status": dict(sorted(by_proof.items())),
        "dangling_edge_count": sum(1 for e in edges if e["from"] not in node_ids or e["to"] not in node_ids),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
    }


# --------------------------------------------------------------------------- #
# Outils internes
# --------------------------------------------------------------------------- #
def _node_map(graph: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {nd["id"]: nd for nd in graph.get("nodes", [])}


def _adjacency(graph: Mapping[str, Any], types: Iterable[str], nodes: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Successeurs (arêtes aux deux extrémités existantes), listes triées."""
    types = frozenset(types)
    adj: Dict[str, Set[str]] = {nid: set() for nid in nodes}
    for e in graph.get("edges", []):
        if e["type"] in types and e["from"] in nodes and e["to"] in nodes:
            adj[e["from"]].add(e["to"])
    return {k: sorted(v) for k, v in adj.items()}


def _reverse(adj: Mapping[str, List[str]]) -> Dict[str, List[str]]:
    rev: Dict[str, List[str]] = {k: [] for k in adj}
    for u in sorted(adj):
        for v in adj[u]:
            rev[v].append(u)
    return rev


def _strongly_connected_components(adj: Mapping[str, List[str]]) -> List[List[str]]:
    """Tarjan itératif. Renvoie les composantes (triées) dans un ordre déterministe."""
    index: Dict[str, int] = {}
    low: Dict[str, int] = {}
    on_stack: Set[str] = set()
    stack: List[str] = []
    comps: List[List[str]] = []
    counter = 0
    for root in sorted(adj):
        if root in index:
            continue
        work: List[Tuple[str, int]] = [(root, 0)]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            v, i = work[-1]
            succ = adj[v]
            if i < len(succ):
                work[-1] = (v, i + 1)
                w = succ[i]
                if w not in index:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, 0))
                elif w in on_stack:
                    low[v] = min(low[v], index[w])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[v])
                if low[v] == index[v]:
                    comp: List[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.discard(w)
                        comp.append(w)
                        if w == v:
                            break
                    comps.append(sorted(comp))
    return sorted(comps)


def _cycles(graph: Mapping[str, Any], nodes: Mapping[str, Any]) -> List[List[str]]:
    adj = _adjacency(graph, ORDER_TYPES, nodes)
    out = []
    for comp in _strongly_connected_components(adj):
        if len(comp) > 1 or comp[0] in adj[comp[0]]:
            out.append(comp)
    return out


def _sort_key(nodes: Mapping[str, Dict[str, Any]]):
    return lambda nid: (nodes[nid]["level_rank"], nid)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_graph(graph: Mapping[str, Any]) -> List[Issue]:
    nodes = _node_map(graph)
    edges = list(graph.get("edges", []))
    issues: List[Issue] = []

    # GRAPH_CYCLE
    for comp in _cycles(graph, nodes):
        issues.append(Issue("GRAPH_CYCLE", Severity.BLOCKER, comp[0], "cycle:" + " -> ".join(comp)))

    # MISSING_PREREQUISITE
    for e in edges:
        for end, other in (("from", "to"), ("to", "from")):
            if e[end] not in nodes:
                owner = e[other] if e[other] in nodes else e[end]
                issues.append(Issue(
                    "MISSING_PREREQUISITE", Severity.ERROR, owner,
                    f"{e['type']}:{end}={e[end]} (notion inexistante)",
                ))

    # ORPHAN_NOTION
    linked: Set[str] = set()
    for e in edges:
        if e["type"] in DEPENDENCY_TYPES and e["from"] in nodes and e["to"] in nodes:
            linked.add(e["from"])
            linked.add(e["to"])
    for nid in sorted(nodes):
        if nid not in linked:
            issues.append(Issue(
                "ORPHAN_NOTION", Severity.INFO, nid,
                "aucun prérequis ni notion dépendante (PREREQUISITE/CROSS_SUBJECT)",
            ))

    # ABNORMAL_LEVEL_JUMP / CROSS_SUBJECT_NOT_LOWER_OR_EQUAL
    for e in edges:
        if e["from"] not in nodes or e["to"] not in nodes:
            continue
        src, dst = nodes[e["from"]], nodes[e["to"]]
        g = dst["level_rank"] - src["level_rank"]
        if e["type"] == PREREQUISITE:
            if g < 0:
                issues.append(Issue(
                    "ABNORMAL_LEVEL_JUMP", Severity.ERROR, dst["id"],
                    f"prérequis {src['id']} ({src['level']}) de niveau supérieur à {dst['level']}",
                ))
            elif g > MAX_NORMAL_LEVEL_GAP:
                issues.append(Issue(
                    "ABNORMAL_LEVEL_JUMP", Severity.WARNING, dst["id"],
                    f"prérequis {src['id']} ({src['level']}) {g} niveaux sous {dst['level']}",
                ))
        elif e["type"] == CROSS_SUBJECT and g < 0:
            issues.append(Issue(
                "CROSS_SUBJECT_NOT_LOWER_OR_EQUAL", Severity.ERROR, dst["id"],
                f"lien {src['id']} ({src['level']}) de niveau supérieur à {dst['level']}",
            ))

    # DEPENDENCY_ON_UNPROVEN (agrégé par notion dépendante)
    unproven_deps: Dict[str, Set[str]] = defaultdict(set)
    for e in edges:
        if e["type"] not in DEPENDENCY_TYPES or e["from"] not in nodes or e["to"] not in nodes:
            continue
        if (nodes[e["to"]]["proof_status"] == ProofStatus.PROVEN_OFFICIAL.value
                and nodes[e["from"]]["proof_status"] == ProofStatus.UNPROVEN.value):
            unproven_deps[e["to"]].add(e["from"])
    for nid in sorted(unproven_deps):
        deps = sorted(unproven_deps[nid])
        issues.append(Issue(
            "DEPENDENCY_ON_UNPROVEN", Severity.INFO, nid,
            f"{len(deps)} prérequis non prouvé(s): " + ", ".join(deps),
        ))

    # DISCONNECTED_SUBJECT_LEVEL
    groups: Dict[Tuple[str, int], Set[str]] = defaultdict(set)
    for nid, nd in nodes.items():
        groups[(nd["subject"], nd["level_rank"])].add(nid)
    connected_pairs: Set[Tuple[str, int, int]] = set()
    for e in edges:
        if e["from"] not in nodes or e["to"] not in nodes:
            continue
        a, b = nodes[e["from"]], nodes[e["to"]]
        if a["subject"] == b["subject"] and a["level_rank"] != b["level_rank"]:
            lo, hi = sorted((a["level_rank"], b["level_rank"]))
            connected_pairs.add((a["subject"], lo, hi))
    for (subject, r) in sorted(groups):
        if r == 0 or (subject, r - 1) not in groups:
            continue
        if (subject, r - 1, r) not in connected_pairs:
            code = _subject_code(subject)
            issues.append(Issue(
                "DISCONNECTED_SUBJECT_LEVEL", Severity.WARNING, f"{code}.{LEVEL_ORDER[r].value}",
                f"aucun lien entre {subject} {LEVEL_ORDER[r].value} et {LEVEL_ORDER[r - 1].value}",
            ))

    return sorted(issues, key=lambda i: (i.code, i.object_id, i.detail, i.severity.value))


def _subject_code(subject: str) -> str:
    for s, code in SUBJECT_CODE.items():
        if s.value == subject:
            return code
    return subject


# --------------------------------------------------------------------------- #
# Parcours (tuteur)
# --------------------------------------------------------------------------- #
def topological_levels(graph: Mapping[str, Any]) -> List[List[str]]:
    """Couches d'apprentissage (Kahn) sur PREREQUISITE+CROSS_SUBJECT+CHILD. ValueError si cycle."""
    nodes = _node_map(graph)
    adj = _adjacency(graph, ORDER_TYPES, nodes)
    indeg = {nid: 0 for nid in nodes}
    for u in adj:
        for v in adj[u]:
            indeg[v] += 1
    layer = sorted(nid for nid, d in indeg.items() if d == 0)
    out: List[List[str]] = []
    seen = 0
    while layer:
        out.append(layer)
        seen += len(layer)
        nxt = []
        for u in layer:
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    nxt.append(v)
        layer = sorted(nxt)
    if seen != len(nodes):
        raise ValueError("graphe_cyclique")
    return out


def ancestors(graph: Mapping[str, Any], notion_id: str) -> List[str]:
    """Tous les prérequis transitifs (PREREQUISITE + CROSS_SUBJECT) d'une notion, triés."""
    nodes = _node_map(graph)
    if notion_id not in nodes:
        raise KeyError(notion_id)
    rev = _reverse(_adjacency(graph, DEPENDENCY_TYPES, nodes))
    return sorted(_collect_ancestors(rev, notion_id, frozenset()))


def _collect_ancestors(rev: Mapping[str, List[str]], start: str, stop: Union[Set[str], frozenset]) -> Set[str]:
    seen: Set[str] = set()
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for p in rev.get(u, ()):
            if p in seen or p == start or p in stop:
                continue
            seen.add(p)
            queue.append(p)
    return seen


def learning_path(graph: Mapping[str, Any], target_id: str, mastered: Optional[Set[str]] = None) -> List[str]:
    """
    Parcours ordonné : prérequis non maîtrisés (du plus élémentaire au plus avancé), puis la
    cible. Une notion maîtrisée est supposée acquise avec ses propres prérequis (on ne remonte
    pas au-delà). ValueError si les prérequis concernés forment un cycle.
    """
    mastered = set(mastered or ())
    nodes = _node_map(graph)
    if target_id not in nodes:
        raise KeyError(target_id)
    adj = _adjacency(graph, DEPENDENCY_TYPES, nodes)
    rev = _reverse(adj)
    needed = _collect_ancestors(rev, target_id, mastered)
    needed.discard(target_id)
    # Kahn restreint, départage (niveau, id) pour un ordre pédagogique stable.
    key = _sort_key(nodes)
    indeg = {n: 0 for n in needed}
    for u in needed:
        for v in adj[u]:
            if v in indeg:
                indeg[v] += 1
    heap = [(key(n), n) for n, d in indeg.items() if d == 0]
    heapq.heapify(heap)
    order: List[str] = []
    while heap:
        _, u = heapq.heappop(heap)
        order.append(u)
        for v in adj[u]:
            if v in indeg:
                indeg[v] -= 1
                if indeg[v] == 0:
                    heapq.heappush(heap, (key(v), v))
    if len(order) != len(needed):
        raise ValueError("graphe_cyclique")
    return order + [target_id]
