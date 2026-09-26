"""
model.py — Modèle canonique des programmes scolaires français (sciences).

Objets (tous immuables, champs inconnus refusés) :
  SourceOfficielle → Programme → Domaine → Theme → Chapitre → Notion
  + Preuve (provenance d'une notion)

Versionnement : un Programme est valable de `rentree_debut` à `rentree_fin`
(incluse, None = toujours en vigueur). Une rentrée est désignée par l'année de
septembre (2025 = année scolaire 2025-2026).

Le tableau d'applicabilité NIVEAUX_PAR_MATIERE décrit l'ORGANISATION du système
scolaire (quelle matière existe à quel niveau), pas le contenu des programmes.
Il reste une configuration à confirmer contre les textes officiels (cf.
CLOUD_DATA_MODEL.md) ; il sert à refuser les incohérences grossières
(ex. « Sciences et technologie » en Terminale).
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.curriculum.ids import sha256_texte

ID_CANONIQUE = r"^[a-z0-9]+(:[a-z0-9][a-z0-9\-]*)+$"


class _Canon(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", use_enum_values=False)


# --------------------------------------------------------------------------- #
# Énumérations
# --------------------------------------------------------------------------- #
class Niveau(str, Enum):
    CM1 = "cm1"
    CM2 = "cm2"
    SIXIEME = "6e"
    CINQUIEME = "5e"
    QUATRIEME = "4e"
    TROISIEME = "3e"
    SECONDE = "2de"
    PREMIERE = "1re"
    TERMINALE = "tle"


class Cycle(str, Enum):
    CYCLE_3 = "cycle3"
    CYCLE_4 = "cycle4"
    LYCEE = "lycee"


CYCLE_DU_NIVEAU: Dict[Niveau, Cycle] = {
    Niveau.CM1: Cycle.CYCLE_3,
    Niveau.CM2: Cycle.CYCLE_3,
    Niveau.SIXIEME: Cycle.CYCLE_3,
    Niveau.CINQUIEME: Cycle.CYCLE_4,
    Niveau.QUATRIEME: Cycle.CYCLE_4,
    Niveau.TROISIEME: Cycle.CYCLE_4,
    Niveau.SECONDE: Cycle.LYCEE,
    Niveau.PREMIERE: Cycle.LYCEE,
    Niveau.TERMINALE: Cycle.LYCEE,
}

ORDRE_NIVEAUX: Tuple[Niveau, ...] = tuple(Niveau)


class Matiere(str, Enum):
    MATHEMATIQUES = "mathematiques"
    PHYSIQUE_CHIMIE = "physique-chimie"
    SVT = "svt"
    SCIENCES_ET_TECHNOLOGIE = "sciences-et-technologie"
    ENSEIGNEMENT_SCIENTIFIQUE = "enseignement-scientifique"


# Organisation du système (à confirmer contre les textes officiels, cf. docstring).
NIVEAUX_PAR_MATIERE: Dict[Matiere, FrozenSet[Niveau]] = {
    Matiere.MATHEMATIQUES: frozenset(Niveau),
    Matiere.PHYSIQUE_CHIMIE: frozenset({
        Niveau.CINQUIEME, Niveau.QUATRIEME, Niveau.TROISIEME,
        Niveau.SECONDE, Niveau.PREMIERE, Niveau.TERMINALE,
    }),
    Matiere.SVT: frozenset({
        Niveau.CINQUIEME, Niveau.QUATRIEME, Niveau.TROISIEME,
        Niveau.SECONDE, Niveau.PREMIERE, Niveau.TERMINALE,
    }),
    Matiere.SCIENCES_ET_TECHNOLOGIE: frozenset({Niveau.CM1, Niveau.CM2, Niveau.SIXIEME}),
    Matiere.ENSEIGNEMENT_SCIENTIFIQUE: frozenset({Niveau.PREMIERE, Niveau.TERMINALE}),
}


class StatutPreuve(str, Enum):
    PROVEN = "PROVEN"
    NOT_EVIDENCED = "NOT_EVIDENCED"
    AMBIGUOUS = "AMBIGUOUS"
    QUARANTINED = "QUARANTINED"


class StatutTexte(str, Enum):
    TEXT_EXACT = "TEXT_EXACT"
    TEXT_RECOVERED = "TEXT_RECOVERED"
    TEXT_TRUNCATED = "TEXT_TRUNCATED"
    TEXT_FRAGMENTED = "TEXT_FRAGMENTED"
    FORMULA_CORRUPTED = "FORMULA_CORRUPTED"
    COLUMN_CONTAMINATION = "COLUMN_CONTAMINATION"
    SOURCE_NOT_EVIDENCED = "SOURCE_NOT_EVIDENCED"
    AMBIGUOUS = "AMBIGUOUS"


STATUTS_TEXTE_UTILISABLES: FrozenSet[StatutTexte] = frozenset(
    {StatutTexte.TEXT_EXACT, StatutTexte.TEXT_RECOVERED}
)


# --------------------------------------------------------------------------- #
# Objets
# --------------------------------------------------------------------------- #
class SourceOfficielle(_Canon):
    """Document officiel (BO, programme Éduscol…) dont dérivent les notions."""

    id: str = Field(pattern=ID_CANONIQUE)
    titre: str = Field(min_length=3, max_length=500)
    editeur: str = Field(min_length=2, max_length=200)
    url: str = Field(min_length=8, max_length=1000)
    reference: str = Field(default="", max_length=200, description="ex. numéro du BO")
    date_publication: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    sha256_document: str = Field(pattern=r"^[0-9a-f]{64}$")
    # Une source FICTIVE (fixtures de test) ne peut jamais prouver une notion en production.
    fictive: bool = False

    @field_validator("url")
    @classmethod
    def _url_https(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("file://")):
            raise ValueError("url_source_non_https")
        return v


class Programme(_Canon):
    id: str = Field(pattern=ID_CANONIQUE)
    source_id: str = Field(pattern=ID_CANONIQUE)
    matiere: Matiere
    niveaux: Tuple[Niveau, ...] = Field(min_length=1)
    titre: str = Field(min_length=3, max_length=300)
    rentree_debut: int = Field(ge=1990, le=2100)
    rentree_fin: Optional[int] = Field(default=None, ge=1990, le=2100)

    @model_validator(mode="after")
    def _coherence(self) -> "Programme":
        if self.rentree_fin is not None and self.rentree_fin < self.rentree_debut:
            raise ValueError("rentree_fin_avant_debut")
        if len(set(self.niveaux)) != len(self.niveaux):
            raise ValueError("niveaux_dupliques")
        return self

    def en_vigueur(self, rentree: int) -> bool:
        return self.rentree_debut <= rentree and (self.rentree_fin is None or rentree <= self.rentree_fin)


class Domaine(_Canon):
    id: str = Field(pattern=ID_CANONIQUE)
    programme_id: str = Field(pattern=ID_CANONIQUE)
    titre: str = Field(min_length=2, max_length=300)
    ordre: int = Field(ge=0)


class Theme(_Canon):
    id: str = Field(pattern=ID_CANONIQUE)
    programme_id: str = Field(pattern=ID_CANONIQUE)
    domaine_id: str = Field(pattern=ID_CANONIQUE)
    titre: str = Field(min_length=2, max_length=300)
    ordre: int = Field(ge=0)


class Chapitre(_Canon):
    id: str = Field(pattern=ID_CANONIQUE)
    programme_id: str = Field(pattern=ID_CANONIQUE)
    theme_id: str = Field(pattern=ID_CANONIQUE)
    niveau: Niveau
    titre: str = Field(min_length=2, max_length=300)
    ordre: int = Field(ge=0)
    # Chapitre dont le rattachement est incertain (ex. titre ambigu dans la source).
    ambigu: bool = False


class Preuve(_Canon):
    """Provenance vérifiable d'une notion : où, dans quelle source, quel extrait exact."""

    source_id: str = Field(pattern=ID_CANONIQUE)
    document: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=8, max_length=1000)
    page: int = Field(ge=1, le=10000)
    section: str = Field(default="", max_length=300)
    extrait: str = Field(min_length=1, max_length=5000, description="extrait VERBATIM de la source")
    sha256_extrait: str = Field(pattern=r"^[0-9a-f]{64}$")
    statut: StatutPreuve = StatutPreuve.NOT_EVIDENCED
    date_verification: str = Field(default="", max_length=10)

    def empreinte_coherente(self) -> bool:
        return sha256_texte(self.extrait) == self.sha256_extrait


class Notion(_Canon):
    id: str = Field(pattern=ID_CANONIQUE)
    programme_id: str = Field(pattern=ID_CANONIQUE)
    chapitre_id: Optional[str] = Field(default=None, pattern=ID_CANONIQUE)
    niveau: Niveau
    matiere: Matiere
    texte: str = Field(min_length=1, max_length=2000)
    statut_texte: StatutTexte = StatutTexte.SOURCE_NOT_EVIDENCED
    preuve: Optional[Preuve] = None
    prerequis: Tuple[str, ...] = ()
    optionnelle: bool = False
    # Contenus pluridisciplinaires (Enseignement scientifique) : matières réellement
    # mobilisées SELON LA SOURCE. Vide = mono-disciplinaire.
    disciplines_mobilisees: Tuple[Matiere, ...] = ()
    # Identifiant hérité (ex. « maths_5e_04 ») pour la migration depuis l'existant.
    id_historique: str = Field(default="", max_length=64)

    @property
    def statut_preuve(self) -> StatutPreuve:
        return self.preuve.statut if self.preuve else StatutPreuve.NOT_EVIDENCED


class Referentiel(_Canon):
    """Ensemble cohérent d'objets canoniques (unité d'import / de validation)."""

    sources: Tuple[SourceOfficielle, ...] = ()
    programmes: Tuple[Programme, ...] = ()
    domaines: Tuple[Domaine, ...] = ()
    themes: Tuple[Theme, ...] = ()
    chapitres: Tuple[Chapitre, ...] = ()
    notions: Tuple[Notion, ...] = ()

    def index(self) -> "IndexReferentiel":
        return IndexReferentiel(self)


class IndexReferentiel:
    """Accès O(1) par identifiant (construit une fois, lecture seule)."""

    def __init__(self, ref: Referentiel):
        self.ref = ref
        self.sources = {s.id: s for s in ref.sources}
        self.programmes = {p.id: p for p in ref.programmes}
        self.domaines = {d.id: d for d in ref.domaines}
        self.themes = {t.id: t for t in ref.themes}
        self.chapitres = {c.id: c for c in ref.chapitres}
        self.notions = {n.id: n for n in ref.notions}

    def programmes_en_vigueur(self, matiere: Matiere, niveau: Niveau, rentree: int) -> List[Programme]:
        return [
            p for p in self.ref.programmes
            if p.matiere == matiere and niveau in p.niveaux and p.en_vigueur(rentree)
        ]
