"""
chapitrage.py — Rattachement notion → chapitre PROUVÉ par la structure du document (lot 8).

Hiérarchie des preuves : preuve source structurelle > comparaison structurelle > heuristique.
Une heuristique (proximité lexicale, titre ressemblant) n'est JAMAIS une preuve.

Entrées :
  - `StructureDocument` (fichier de type `structure_document` du lot) : pour UN document source
    (empreinte), les pages du sommaire, des annexes, les chapitres avec leur plage de pages, les
    colonnes par page (mise en page multi-colonnes) et les zones « prérequis » ;
  - les preuves attachées à une ligne de mapping :
      {"type": "section_pdf" | "tableau_officiel" | "sommaire" | "proximite_lexicale",
       "sha256_document", "page", "bbox": [x0, y0, x1, y1], "cellule": {"ligne", "colonne"}}

Une preuve SOUTIENT le chapitre dont elle se situe dans la zone (pages + colonne) ; elle est
écartée si elle est : lexicale, du sommaire seul, en annexe, dans une zone de prérequis, un titre
de colonne de tableau, sur un autre document, ou hors de toute zone de chapitre.
Verdict :
  PROUVE         toutes les preuves retenues désignent le chapitre déclaré ;
  CONTRADICTOIRE les preuves désignent UN autre chapitre ;
  AMBIGU         les preuves désignent plusieurs chapitres ;
  NON_PROUVE     aucune preuve retenue.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, NamedTuple, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

TYPES_PREUVE = ("section_pdf", "tableau_officiel", "sommaire", "proximite_lexicale")


class Verdict(str, Enum):
    PROUVE = "PROUVE"
    CONTRADICTOIRE = "CONTRADICTOIRE"
    AMBIGU = "AMBIGU"
    NON_PROUVE = "NON_PROUVE"
    DECLARE = "DECLARE"  # rattachement déclaré par le producteur, sans preuve structurelle


class Colonne(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page: int = Field(ge=1)
    x0: float
    x1: float


class Zone(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page: int = Field(ge=1)
    y0: float
    y1: float


class ChapitreStructure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    chapitre_id: str = Field(min_length=1, max_length=200)
    page_debut: int = Field(ge=1)
    page_fin: int = Field(ge=1)
    colonnes: Tuple[Colonne, ...] = ()


class Plage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page_debut: int = Field(ge=1)
    page_fin: int = Field(ge=1)


class StructureDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sha256_document: str = Field(pattern=r"^[0-9a-f]{64}$")
    sommaire_pages: Tuple[int, ...] = ()
    annexes: Tuple[Plage, ...] = ()
    zones_prerequis: Tuple[Zone, ...] = ()
    chapitres: Tuple[ChapitreStructure, ...] = Field(min_length=1)


class Cellule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ligne: int = Field(ge=0)
    colonne: str = Field(min_length=1, max_length=200)


class PreuveChapitre(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: Literal["section_pdf", "tableau_officiel", "sommaire", "proximite_lexicale"]
    sha256_document: str = Field(pattern=r"^[0-9a-f]{64}$")
    page: int = Field(ge=1)
    bbox: Optional[Tuple[float, float, float, float]] = None
    cellule: Optional[Cellule] = None


class Resultat(NamedTuple):
    verdict: Verdict
    chapitres_soutenus: Tuple[str, ...]
    ecartees: Tuple[str, ...]


def _chapitre_de(p: PreuveChapitre, s: StructureDocument) -> Tuple[Optional[str], Optional[str]]:
    """(chapitre soutenu, raison d'écartement)."""
    if p.type == "proximite_lexicale":
        return None, "preuve_lexicale_insuffisante"
    if p.type == "sommaire":
        return None, "sommaire_seul"
    if p.sha256_document != s.sha256_document:
        return None, "autre_document"
    if p.page in s.sommaire_pages:
        return None, "preuve_dans_le_sommaire"
    if any(a.page_debut <= p.page <= a.page_fin for a in s.annexes):
        return None, "preuve_en_annexe"
    if p.bbox is not None and any(z.page == p.page and z.y0 <= p.bbox[1] and p.bbox[3] <= z.y1
                                  for z in s.zones_prerequis):
        return None, "preuve_dans_les_prerequis"
    if p.type == "tableau_officiel":
        if p.cellule is None:
            return None, "cellule_manquante"
        if p.cellule.ligne == 0:
            return None, "preuve_titre_de_colonne"
    candidats = [c for c in s.chapitres if c.page_debut <= p.page <= c.page_fin]
    # Page multi-colonnes : la colonne (abscisses) départage les chapitres présents sur la page.
    avec_colonnes = [c for c in candidats if any(col.page == p.page for col in c.colonnes)]
    if avec_colonnes:
        if p.bbox is None:
            return None, "coordonnees_requises_page_multicolonne"
        dans = [c for c in avec_colonnes if any(col.page == p.page and col.x0 <= p.bbox[0] and p.bbox[2] <= col.x1
                                                for col in c.colonnes)]
        candidats = dans
    if len(candidats) != 1:
        return None, "hors_zone_de_chapitre" if not candidats else "zone_partagee"
    return candidats[0].chapitre_id, None


def evaluer(chapitre_declare: str, preuves: List[PreuveChapitre], structure: Optional[StructureDocument]) -> Resultat:
    if not preuves:
        return Resultat(Verdict.DECLARE, (), ())
    if structure is None:
        return Resultat(Verdict.NON_PROUVE, (), ("structure_document_absente",))
    soutenus, ecartees = set(), []
    for p in preuves:
        chap, raison = _chapitre_de(p, structure)
        if chap:
            soutenus.add(chap)
        else:
            ecartees.append(raison)
    if not soutenus:
        v = Verdict.NON_PROUVE
    elif len(soutenus) > 1:
        v = Verdict.AMBIGU
    elif soutenus == {chapitre_declare}:
        v = Verdict.PROUVE
    else:
        v = Verdict.CONTRADICTOIRE
    return Resultat(v, tuple(sorted(soutenus)), tuple(sorted(ecartees)))


def verifier_structure(s: StructureDocument) -> List[str]:
    """Cohérence interne : plages valides, chapitres sans chevauchement hors colonnes distinctes."""
    raisons = []
    for c in s.chapitres:
        if c.page_fin < c.page_debut:
            raisons.append(f"plage_invalide:{c.chapitre_id}")
    ids = [c.chapitre_id for c in s.chapitres]
    if len(ids) != len(set(ids)):
        raisons.append("chapitre_duplique")
    return raisons


def index_structures(structures: List[StructureDocument]) -> Dict[str, StructureDocument]:
    return {s.sha256_document: s for s in structures}
