"""
sources.py — Preuve de provenance à partir des documents officiels LOCAUX.

Chaîne :
  1. un document officiel (PDF du BO / Éduscol) est déposé dans pedagogy/sources/official/ ;
  2. register_source() calcule son SHA-256 et extrait le texte page par page ;
  3. verify_notion_against_source() vérifie que le libellé officiel de la notion figure
     VERBATIM (après normalisation typographique sans perte de sens) à la page déclarée ;
  4. propose_promotions() cherche, pour chaque notion candidate UNPROVEN, les pages où
     son titre apparaît ; la promotion en PROVEN_OFFICIAL reste une action explicite
     (promote_notion) qui recopie le texte EXACT de la source — jamais le texte candidat.

Aucune requête réseau : les documents doivent être présents localement.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence

from pedagogy.models import (
    OFFICIAL_SOURCE_TYPES,
    Notion,
    OfficialSource,
    ProofStatus,
    SourceRetrieval,
)

_LIGATURES = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl", "œ": "oe", "Œ": "OE"}
_APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'", "´": "'"}
_DASHES = {"–": "-", "—": "-", "‑": "-", "−": "-"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def normalize_for_match(text: str) -> str:
    """
    Normalisation typographique SANS perte de sens pour comparer un libellé à un texte
    extrait de PDF : ligatures, apostrophes/tirets typographiques, césures de fin de
    ligne (« multi-\\nplication »), espaces multiples, casse. Les chiffres, symboles
    mathématiques et la ponctuation interne sont conservés.
    """
    t = unicodedata.normalize("NFKC", text or "")
    for table in (_LIGATURES, _APOSTROPHES, _DASHES):
        for a, b in table.items():
            t = t.replace(a, b)
    t = t.replace("­", "")
    t = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", t)  # césure en fin de ligne
    t = re.sub(r"\s+", " ", t)
    return t.casefold().strip()


@dataclass(frozen=True)
class SourceText:
    source: OfficialSource
    pages: Dict[int, str]  # numéro de page (1-based) → texte normalisé


class ExtractionError(RuntimeError):
    pass


def extract_pdf_pages(path: Path) -> Dict[int, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ExtractionError("pypdf_absent: pip install -r requirements-pedagogy.txt") from exc
    try:
        reader = PdfReader(str(path))
        return {i + 1: normalize_for_match(page.extract_text() or "") for i, page in enumerate(reader.pages)}
    except Exception as exc:
        raise ExtractionError(f"pdf_illisible:{path.name}") from exc


def load_source_text(source: OfficialSource, root: Path) -> SourceText:
    """Vérifie l'empreinte du fichier enregistré puis extrait son texte."""
    if source.retrieval == SourceRetrieval.EXPECTED:
        raise ExtractionError(f"source_non_recuperee:{source.source_id}")
    path = (root / source.local_path).resolve()
    if root.resolve() not in path.parents:
        raise ExtractionError("chemin_source_hors_depot")
    if not path.is_file():
        raise ExtractionError(f"fichier_source_absent:{source.local_path}")
    reel = sha256_file(path)
    if reel != source.sha256:
        raise ExtractionError(f"sha256_different:{source.source_id}")
    if path.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(path)
    else:  # texte brut : pages séparées par \f
        pages = {i + 1: normalize_for_match(p) for i, p in enumerate(path.read_text(encoding="utf-8").split("\f"))}
    return SourceText(source, pages)


def register_source(source: OfficialSource, root: Path) -> OfficialSource:
    """Renvoie la source marquée RETRIEVED avec l'empreinte réelle du fichier local."""
    path = (root / source.local_path).resolve()
    if not source.local_path or not path.is_file():
        raise ExtractionError(f"fichier_source_absent:{source.local_path or '(vide)'}")
    retrieval = SourceRetrieval.VERIFIED if source.reference_verified else SourceRetrieval.RETRIEVED
    return source.model_copy(update={"sha256": sha256_file(path), "retrieval": retrieval})


class ProofResult(NamedTuple):
    status: ProofStatus
    reasons: List[str]


def _page_numbers(spec: Optional[str]) -> List[int]:
    if not spec:
        return []
    nums: List[int] = []
    for a, b in re.findall(r"(\d+)(?:\s*-\s*(\d+))?", spec):
        lo, hi = int(a), int(b or a)
        if hi < lo or hi - lo > 50:
            return []
        nums.extend(range(lo, hi + 1))
    return nums


def verify_notion_against_source(notion: Notion, texts: Dict[str, SourceText]) -> ProofResult:
    """
    Recalcule la preuve d'une notion (jamais crue sur parole) :
      PROVEN_OFFICIAL : source officielle enregistrée, empreinte identique à celle de la
                        notion, libellé officiel présent verbatim à la page déclarée ;
      CONFLICT        : libellé présent dans la source mais à une autre page, ou
                        source d'une autre matière / d'un autre niveau ;
      UNPROVEN        : pas de source, source non récupérée, libellé absent.
    """
    if notion.proof_status == ProofStatus.DEPRECATED:
        return ProofResult(ProofStatus.DEPRECATED, ["deprecated_declare"])
    if not notion.source_id or notion.source_type not in OFFICIAL_SOURCE_TYPES:
        return ProofResult(ProofStatus.UNPROVEN, ["pas_de_source_officielle"])
    st = texts.get(notion.source_id)
    if st is None:
        return ProofResult(ProofStatus.UNPROVEN, ["source_non_recuperee"])
    src = st.source
    if notion.source_sha256 != src.sha256:
        return ProofResult(ProofStatus.CONFLICT, ["sha256_notion_different_du_document"])
    if notion.subject not in src.subjects or notion.level not in src.levels:
        return ProofResult(ProofStatus.CONFLICT, ["source_d_une_autre_matiere_ou_niveau"])
    if not notion.official_wording:
        return ProofResult(ProofStatus.UNPROVEN, ["libelle_officiel_absent"])
    needle = normalize_for_match(notion.official_wording)
    if len(needle) < 3:
        return ProofResult(ProofStatus.UNPROVEN, ["libelle_trop_court"])
    pages = _page_numbers(notion.source_page_or_section)
    found_on = [p for p, txt in st.pages.items() if needle in txt]
    if not found_on:
        return ProofResult(ProofStatus.UNPROVEN, ["libelle_introuvable_dans_la_source"])
    if pages and not set(pages) & set(found_on):
        return ProofResult(ProofStatus.CONFLICT, [f"libelle_trouve_page_{found_on[0]}_pas_page_declaree"])
    if not pages:
        return ProofResult(ProofStatus.UNPROVEN, ["page_non_declaree"])
    return ProofResult(ProofStatus.PROVEN_OFFICIAL, [])


class PromotionCandidate(NamedTuple):
    notion_id: str
    source_id: str
    pages: List[int]
    matched_text: str


def propose_promotions(notions: Iterable[Notion], texts: Dict[str, SourceText]) -> List[PromotionCandidate]:
    """Pages où le TITRE d'une notion candidate apparaît dans une source compatible."""
    out: List[PromotionCandidate] = []
    for n in notions:
        if n.proof_status != ProofStatus.UNPROVEN:
            continue
        needle = normalize_for_match(n.title)
        if len(needle) < 6:
            continue
        for sid, st in sorted(texts.items()):
            if n.subject not in st.source.subjects or n.level not in st.source.levels:
                continue
            pages = sorted(p for p, txt in st.pages.items() if needle in txt)
            if pages:
                out.append(PromotionCandidate(n.notion_id, sid, pages, n.title))
    return out


def promote_notion(notion: Notion, st: SourceText, page: int, exact_excerpt: str) -> Notion:
    """
    Promotion EXPLICITE : l'extrait fourni doit figurer tel quel à la page indiquée.
    Le libellé officiel stocké est l'extrait de la source, pas le titre candidat.
    """
    if normalize_for_match(exact_excerpt) not in st.pages.get(page, ""):
        raise ValueError("extrait_absent_de_la_page")
    promoted = notion.model_copy(update={
        "source_type": st.source.source_type,
        "source_id": st.source.source_id,
        "source_title": st.source.title,
        "source_url_or_ref": st.source.reference or st.source.url or st.source.local_path,
        "source_page_or_section": str(page),
        "source_sha256": st.source.sha256,
        "official_wording": exact_excerpt,
        "proof_status": ProofStatus.PROVEN_OFFICIAL,
    })
    # Revalidation complète des invariants du modèle.
    promoted = Notion.model_validate(promoted.model_dump())
    res = verify_notion_against_source(promoted, {st.source.source_id: st})
    if res.status != ProofStatus.PROVEN_OFFICIAL:
        raise ValueError("promotion_non_verifiable:" + ",".join(res.reasons))
    return promoted


def recompute_statuses(notions: Sequence[Notion], texts: Dict[str, SourceText]) -> Dict[str, ProofResult]:
    return {n.notion_id: verify_notion_against_source(n, texts) for n in notions}
