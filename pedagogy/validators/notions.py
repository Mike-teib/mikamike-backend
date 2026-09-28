"""
notions.py — Contrôles de cohérence du registre de notions (niveau registre entier).

Point d'entrée : ``validate_registry_notions(reg, root=REPO_ROOT) -> List[Issue]``.
Déterministe (issues triées), pur (lecture seule), sans réseau ni LLM.

Codes stables (object_id entre crochets) :

  LOAD_ERROR                  BLOCKER  [chemin]      fichier du registre illisible / invalide (reg.load_errors),
                                                     y compris identifiants dupliqués détectés au chargement.
  NOTION_UNPROVEN             INFO     [notion_id]   notion non prouvée officiellement (UNPROVEN ou
                                                     PROVEN_INTERNAL) : attendu tant qu'aucune source n'est
                                                     récupérée ; la notion n'alimente pas la banque.
  NOTIONS_UNPROVEN_SUMMARY    INFO     [REGISTRY]    agrégat : nombre de notions non prouvées / total.
  NOTION_CONFLICT             ERROR    [notion_id]   proof_status == CONFLICT (sources contradictoires).
  NOTION_DEPRECATED_IN_USE    ERROR    [notion_id]   notion non DEPRECATED qui cite une notion DEPRECATED en
                                                     prérequis ou en lien inter-matières.
  NOTION_WITHOUT_SOURCE       ERROR    [notion_id]   source_title ou source_url_or_ref vide, ou source_id
                                                     renseigné mais absent de reg.sources, ou source_type
                                                     officiel sans source_id.
  SOURCE_NOT_RETRIEVED        INFO     [notion_id]   la source déclarée est encore EXPECTED (PDF non déposé).
  SOURCE_UNREADABLE           ERROR    [source_id]   source marquée récupérée mais fichier absent, empreinte
                                                     SHA-256 différente ou PDF illisible (ExtractionError).
                                                     Contrôlé seulement pour les sources citées par une
                                                     notion PROVEN_OFFICIAL.
  PROOF_NOT_VERIFIABLE        BLOCKER  [notion_id]   notion déclarée PROVEN_OFFICIAL dont la preuve,
                                                     RECALCULÉE par verify_notion_against_source sur les
                                                     documents locaux, n'aboutit pas à PROVEN_OFFICIAL.
  PREREQUISITE_UNKNOWN        ERROR    [notion_id]   prérequis absent du registre.
  PREREQUISITE_HIGHER_LEVEL   ERROR    [notion_id]   prérequis d'un niveau strictement supérieur.
  PREREQUISITE_CROSS_SUBJECT  WARNING  [notion_id]   prérequis d'une autre matière : devrait figurer dans
                                                     cross_subject_links. Exception : SCIENCES_TECHNOLOGIE
                                                     (6e) est la filiation de cycle 3 de PHYSIQUE_CHIMIE et
                                                     de SVT ; un prérequis ST d'une notion PC/SVT n'est pas
                                                     considéré comme inter-matières.
  CROSS_LINK_UNKNOWN          ERROR    [notion_id]   lien inter-matières absent du registre.
  CROSS_LINK_HIGHER_LEVEL     ERROR    [notion_id]   lien inter-matières d'un niveau strictement supérieur.
  DUPLICATE_TITLE_SAME_LEVEL  WARNING  [notion_id]   même normalized_title, même matière, même niveau
                                                     (signalé sur chaque notion après la première, triée).
  NEAR_DUPLICATE_TITLE        INFO     [notion_id]   Jaccard des ensembles de mots >= 0.8 (titres non
                                                     identiques), même matière et niveau.
  SCHOOL_YEAR_OUTSIDE_SOURCE  ERROR    [notion_id]   school_year antérieure à school_year_start ou
                                                     postérieure à school_year_end de la source.
  SOURCE_SUBJECT_LEVEL_MISMATCH ERROR  [notion_id]   matière ou niveau de la notion non couverts par la source.
  PUBLISHED_FORBIDDEN         BLOCKER  [notion_id]   aucune notion ne doit être PUBLISHED dans ce chantier.
  EMPTY_PEDAGOGY              WARNING  [notion_id]   ni learning_objectives, ou ni common_mistakes.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pedagogy.issues import Issue, Severity
from pedagogy.models import (
    LEVEL_RANK,
    OFFICIAL_SOURCE_TYPES,
    Notion,
    ProofStatus,
    PublicationStatus,
    SourceRetrieval,
    Subject,
)
from pedagogy.registry import REPO_ROOT, Registry
from pedagogy.sources import ExtractionError, SourceText, load_source_text, verify_notion_against_source

NEAR_DUPLICATE_THRESHOLD = 0.8

# Matières d'une même filiation disciplinaire (prérequis admis sans cross_subject_links).
SAME_LINEAGE = frozenset({
    (Subject.PHYSIQUE_CHIMIE, Subject.SCIENCES_TECHNOLOGIE),
    (Subject.SVT, Subject.SCIENCES_TECHNOLOGIE),
})


def same_lineage(subject, prereq_subject) -> bool:
    return subject == prereq_subject or (subject, prereq_subject) in SAME_LINEAGE

SEVERITY_RANK = {Severity.BLOCKER: 0, Severity.ERROR: 1, Severity.WARNING: 2, Severity.INFO: 3}


def sort_issues(issues: List[Issue]) -> List[Issue]:
    """Tri stable et dédoublonnage : sévérité, code, objet, détail."""
    uniq = {(i.code, i.severity, i.object_id, i.detail): i for i in issues}
    return sorted(uniq.values(), key=lambda i: (SEVERITY_RANK[Severity(i.severity)], i.code, i.object_id, i.detail))


def title_words(text: str) -> Set[str]:
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii").casefold()
    return {w for w in re.split(r"[^a-z0-9]+", t) if w}


def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _year_start(school_year: str) -> int:
    return int(school_year[:4])


def _load_texts(reg: Registry, root: Path, needed: Set[str]) -> Tuple[Dict[str, SourceText], List[Issue]]:
    texts: Dict[str, SourceText] = {}
    issues: List[Issue] = []
    for sid in sorted(needed):
        src = reg.sources.get(sid)
        if src is None or src.retrieval == SourceRetrieval.EXPECTED:
            continue
        try:
            texts[sid] = load_source_text(src, root)
        except ExtractionError as exc:
            issues.append(Issue("SOURCE_UNREADABLE", Severity.ERROR, sid, str(exc)))
    return texts, issues


def validate_registry_notions(reg: Registry, root: Optional[Path] = None) -> List[Issue]:
    root = REPO_ROOT if root is None else Path(root)
    out: List[Issue] = []
    add = out.append

    for path, reason in reg.load_errors:
        add(Issue("LOAD_ERROR", Severity.BLOCKER, path, reason))

    notions: List[Notion] = [n for _, n in sorted(reg.notions.items())]

    # -- Preuve ---------------------------------------------------------------
    unproven = 0
    for n in notions:
        if n.proof_status in (ProofStatus.UNPROVEN, ProofStatus.PROVEN_INTERNAL):
            unproven += 1
            add(Issue("NOTION_UNPROVEN", Severity.INFO, n.notion_id, f"proof_status={n.proof_status.value}"))
        elif n.proof_status == ProofStatus.CONFLICT:
            add(Issue("NOTION_CONFLICT", Severity.ERROR, n.notion_id, n.provenance_note[:200]))
    if unproven:
        add(Issue("NOTIONS_UNPROVEN_SUMMARY", Severity.INFO, "REGISTRY", f"unproven={unproven}/total={len(notions)}"))

    proven = [n for n in notions if n.proof_status == ProofStatus.PROVEN_OFFICIAL]
    if proven:
        texts, src_issues = _load_texts(reg, root, {n.source_id for n in proven if n.source_id})
        out.extend(src_issues)
        for n in proven:
            res = verify_notion_against_source(n, texts)
            if res.status != ProofStatus.PROVEN_OFFICIAL:
                add(Issue("PROOF_NOT_VERIFIABLE", Severity.BLOCKER, n.notion_id,
                          f"recalcul={res.status.value}:{','.join(res.reasons)}"))

    # -- Sources --------------------------------------------------------------
    for n in notions:
        missing: List[str] = []
        if not n.source_title.strip():
            missing.append("source_title_vide")
        if not n.source_url_or_ref.strip():
            missing.append("source_url_or_ref_vide")
        src = reg.sources.get(n.source_id) if n.source_id else None
        if n.source_id and src is None:
            missing.append(f"source_id_inconnu:{n.source_id}")
        if not n.source_id and n.source_type in OFFICIAL_SOURCE_TYPES:
            missing.append("source_officielle_sans_source_id")
        if missing:
            add(Issue("NOTION_WITHOUT_SOURCE", Severity.ERROR, n.notion_id, ",".join(missing)))
        if src is None:
            continue
        if src.retrieval == SourceRetrieval.EXPECTED:
            add(Issue("SOURCE_NOT_RETRIEVED", Severity.INFO, n.notion_id, src.source_id))
        y = _year_start(n.school_year)
        if y < _year_start(src.school_year_start):
            add(Issue("SCHOOL_YEAR_OUTSIDE_SOURCE", Severity.ERROR, n.notion_id,
                      f"{n.school_year}<debut:{src.school_year_start}:{src.source_id}"))
        elif src.school_year_end and y > _year_start(src.school_year_end):
            add(Issue("SCHOOL_YEAR_OUTSIDE_SOURCE", Severity.ERROR, n.notion_id,
                      f"{n.school_year}>fin:{src.school_year_end}:{src.source_id}"))
        bad = []
        if n.subject not in src.subjects:
            bad.append(f"matiere:{n.subject.value}")
        if n.level not in src.levels:
            bad.append(f"niveau:{n.level.value}")
        if bad:
            add(Issue("SOURCE_SUBJECT_LEVEL_MISMATCH", Severity.ERROR, n.notion_id, f"{src.source_id}:{','.join(bad)}"))

    # -- Graphe (prérequis, liens) -------------------------------------------
    for n in notions:
        rank = LEVEL_RANK[n.level]
        for pid in n.prerequisites:
            p = reg.notions.get(pid)
            if p is None:
                add(Issue("PREREQUISITE_UNKNOWN", Severity.ERROR, n.notion_id, pid))
                continue
            if LEVEL_RANK[p.level] > rank:
                add(Issue("PREREQUISITE_HIGHER_LEVEL", Severity.ERROR, n.notion_id, f"{pid}:{p.level.value}>{n.level.value}"))
            if not same_lineage(n.subject, p.subject):
                add(Issue("PREREQUISITE_CROSS_SUBJECT", Severity.WARNING, n.notion_id,
                          f"{pid}:deplacer_dans_cross_subject_links"))
        for lid in n.cross_subject_links:
            p = reg.notions.get(lid)
            if p is None:
                add(Issue("CROSS_LINK_UNKNOWN", Severity.ERROR, n.notion_id, lid))
            elif LEVEL_RANK[p.level] > rank:
                add(Issue("CROSS_LINK_HIGHER_LEVEL", Severity.ERROR, n.notion_id, f"{lid}:{p.level.value}>{n.level.value}"))
        if n.proof_status != ProofStatus.DEPRECATED:
            for field_name, refs in (("prerequisites", n.prerequisites), ("cross_subject_links", n.cross_subject_links)):
                for rid in refs:
                    r = reg.notions.get(rid)
                    if r is not None and r.proof_status == ProofStatus.DEPRECATED:
                        add(Issue("NOTION_DEPRECATED_IN_USE", Severity.ERROR, n.notion_id, f"{field_name}:{rid}"))

    # -- Doublons de titres ---------------------------------------------------
    groups: Dict[Tuple[str, str], List[Notion]] = defaultdict(list)
    for n in notions:
        groups[(n.subject.value, n.level.value)].append(n)
    for key in sorted(groups):
        members = groups[key]
        by_title: Dict[str, List[Notion]] = defaultdict(list)
        for n in members:
            by_title[n.normalized_title].append(n)
        for title in sorted(by_title):
            same = by_title[title]
            for n in same[1:]:
                add(Issue("DUPLICATE_TITLE_SAME_LEVEL", Severity.WARNING, n.notion_id,
                          f"meme_titre_que:{same[0].notion_id}(course={same[0].course.value}/{n.course.value})"))
        words = [(n, title_words(n.normalized_title)) for n in members]
        for i in range(len(words)):
            a, wa = words[i]
            for j in range(i + 1, len(words)):
                b, wb = words[j]
                if a.normalized_title == b.normalized_title:
                    continue
                score = jaccard(wa, wb)
                if score >= NEAR_DUPLICATE_THRESHOLD:
                    add(Issue("NEAR_DUPLICATE_TITLE", Severity.INFO, b.notion_id,
                              f"proche_de:{a.notion_id}:jaccard={score:.2f}"))

    # -- Statuts et pédagogie -------------------------------------------------
    for n in notions:
        if n.publication_status == PublicationStatus.PUBLISHED:
            add(Issue("PUBLISHED_FORBIDDEN", Severity.BLOCKER, n.notion_id, "aucune_publication_dans_ce_chantier"))
        empty = [name for name, v in (("learning_objectives", n.learning_objectives),
                                      ("common_mistakes", n.common_mistakes)) if not v]
        if empty:
            add(Issue("EMPTY_PEDAGOGY", Severity.WARNING, n.notion_id, ",".join(empty)))

    return sort_issues(out)
