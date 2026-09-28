"""
ingest/core.py — Noyau commun d'extraction de notions PROUVÉES depuis les PDF officiels.

Principe : chaque notion est un item du programme (objectif d'apprentissage, contenu,
capacité attendue, connaissance) recopié MOT POUR MOT depuis une page du PDF officiel
enregistré (SHA-256 vérifié). La promotion passe par pedagogy.sources.promote_notion :
si l'extrait n'est pas retrouvé tel quel sur la page déclarée, la notion est refusée.

Aucune notion n'est approuvée ici : review_status reste NOT_REVIEWED (revue humaine
obligatoire avant toute génération de contenu servi aux élèves).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from pypdf import PdfReader

from pedagogy.models import (
    CYCLE_OF_LEVEL,
    Course,
    Level,
    Notion,
    NotionFile,
    SourceType,
    Subject,
    make_notion_id,
    normalize_title,
)
from pedagogy.registry import DATA_DIR, REPO_ROOT, load_registry
from pedagogy.sources import SourceText, load_source_text, normalize_for_match, promote_notion

# Puces : tiret, moins, demi-cadratin, point médian, et glyphes privés des PDF (U+F02D, U+F0B7).
BULLET_RE = re.compile("^\\s*(?:[-\u2212\u2013\u2022\uf02d\uf0b7])\\s+")
TITLE_MAX = 160


_LINES_CACHE: Dict[Tuple[str, str], Dict[int, List[str]]] = {}


def raw_pages(source_id: str, root: Path = REPO_ROOT) -> Tuple[SourceText, Dict[int, List[str]]]:
    """Texte normalisé (pour la preuve) + lignes brutes par page (1-based, pour l'analyse)."""
    reg = load_registry()
    src = reg.sources[source_id]
    st = load_source_text(src, root)
    path = root / src.local_path
    key = (str(path.resolve()), src.sha256)
    if key not in _LINES_CACHE:
        reader = PdfReader(str(path))
        _LINES_CACHE[key] = {i + 1: (p.extract_text() or "").splitlines() for i, p in enumerate(reader.pages)}
    return st, {k: list(v) for k, v in _LINES_CACHE[key].items()}


def clean_line(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace(" ", " ")).strip()


def is_bullet(s: str) -> bool:
    return bool(BULLET_RE.match(s)) and len(clean_line(BULLET_RE.sub("", s, count=1))) > 0


def strip_bullet(s: str) -> str:
    return clean_line(BULLET_RE.sub("", s, count=1))


def title_from_excerpt(excerpt: str) -> str:
    t = clean_line(excerpt).rstrip(" .;:")
    if len(t) <= TITLE_MAX:
        return t
    cut = t[:TITLE_MAX].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "…"


def found_on_page(st: SourceText, page: int, excerpt: str) -> bool:
    return normalize_for_match(excerpt) in st.pages.get(page, "")


@dataclass
class Item:
    """Item extrait d'un programme, avant promotion."""

    level: Level
    domain: str
    domain_code: str
    chapter: str
    excerpt: str
    page: int
    kind: str = "objectif"          # objectif | contenu | capacite | connaissance | attendu
    difficulty: int = 2
    optional: bool = False
    # None : complétude déduite de la ponctuation finale ; True/False : le parseur sait
    # (ex. lignes de tableau sans point final mais complètes) — évite les faux « partiels ».
    complete: Optional[bool] = None


@dataclass
class Builder:
    """Construit des notions PROUVÉES pour une source et une matière."""

    source_id: str
    subject: Subject
    course: Course
    school_year: str
    program_version: str
    st: SourceText = field(init=False)
    lines: Dict[int, List[str]] = field(init=False)
    notions: List[Notion] = field(default_factory=list)
    rejected: List[Tuple[Item, str]] = field(default_factory=list)
    _ids: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.st, self.lines = raw_pages(self.source_id)

    def _unique_id(self, level: Level, domain_code: str, title: str) -> Tuple[str, str]:
        base = make_notion_id(self.subject, level, domain_code, title)
        # Les ID sont limités en longueur : on tronque le slug proprement.
        head, slug = base.rsplit(".", 1)
        slug = slug[:70].rstrip("-")
        nid = f"{head}.{slug}"
        n = self._ids.get(nid, 0)
        self._ids[nid] = n + 1
        if n:
            nid = f"{nid}-{n + 1}"
            title = f"{title} ({n + 1})"
        return nid, title

    def add(self, it: Item) -> Optional[Notion]:
        excerpt = clean_line(it.excerpt)
        if len(excerpt) < 4:
            self.rejected.append((it, "extrait_trop_court"))
            return None
        if not found_on_page(self.st, it.page, excerpt):
            self.rejected.append((it, "extrait_absent_de_la_page"))
            return None
        if it.complete is None:
            partial = not excerpt.rstrip().endswith((".", "?", "!", ")", "»", ":", ";"))
        else:
            partial = not it.complete
        title = title_from_excerpt(excerpt)
        if partial and not title.endswith("…"):
            title = title + " …"
        nid, title = self._unique_id(it.level, it.domain_code, title)
        candidate = Notion(
            notion_id=nid, subject=self.subject, level=it.level, cycle=CYCLE_OF_LEVEL[it.level],
            course=self.course, school_year=self.school_year, official_program_version=self.program_version,
            domain=it.domain, domain_code=it.domain_code, chapter=it.chapter[:200], title=title,
            normalized_title=normalize_title(title), difficulty=it.difficulty,
            # L'objectif d'apprentissage EST le libellé officiel (aucun ajout rédactionnel).
            learning_objectives=(excerpt,) if it.kind in ("objectif", "capacite", "attendu") else (),
            source_type=SourceType.CANDIDATE_UNVERIFIED, source_title=self.st.source.title,
            source_url_or_ref=self.st.source.reference or self.st.source.url,
            provenance_note=(f"Extrait officiel ({it.kind}) recopié verbatim depuis {self.source_id}, page {it.page} ; "
                             "promotion automatique vérifiée par SHA-256 et recherche exacte. Revue humaine requise "
                             "avant toute génération de contenu servi (review_status=NOT_REVIEWED)."
                             + (" Libellé officiel PARTIEL : la phrase est interrompue dans le PDF (mise en page "
                                "en colonnes) ; compléter à la relecture." if partial else "")),
            optional_in_program=it.optional,
        )
        try:
            proven = promote_notion(candidate, self.st, it.page, excerpt)
        except ValueError as exc:
            self.rejected.append((it, str(exc)))
            return None
        self.notions.append(proven)
        return proven

    def by_level(self) -> Dict[Level, List[Notion]]:
        out: Dict[Level, List[Notion]] = {}
        for n in self.notions:
            out.setdefault(n.level, []).append(n)
        return out


def link_sequential_prerequisites(notions: Sequence[Notion]) -> List[Notion]:
    """Prérequis minimal et sûr : dans un même chapitre, chaque objectif suit le précédent
    (ordre du programme). Aucun lien inter-niveaux n'est inventé ici."""
    out: List[Notion] = []
    prev: Dict[Tuple[str, str, str], str] = {}
    for n in notions:
        key = (n.level.value, n.domain_code, n.chapter)
        pre = prev.get(key)
        out.append(n.model_copy(update={"prerequisites": (pre,)}) if pre else n)
        prev[key] = n.notion_id
    return [Notion.model_validate(n.model_dump()) for n in out]


def write_notion_file(path: Path, subject: Subject, level: Level, course: Course, notions: Sequence[Notion],
                      generated_by: str) -> None:
    nf = NotionFile(
        schema_version="1.0", subject=subject, level=level, course=course, generated_by=generated_by,
        disclaimer=("Notions PROUVÉES : libellés officiels recopiés verbatim depuis le PDF officiel enregistré "
                    "(page et SHA-256 indiqués). Non encore relues par un humain : review_status=NOT_REVIEWED."),
        notions=tuple(notions),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json.loads(nf.model_dump_json()), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def report_rejections(rejected: Iterable[Tuple[Item, str]], limit: int = 20) -> str:
    rows = list(rejected)
    lines = [f"{len(rows)} item(s) rejeté(s)"]
    for it, why in rows[:limit]:
        lines.append(f"  p{it.page} {it.level.value} {why}: {it.excerpt[:90]!r}")
    return "\n".join(lines)
