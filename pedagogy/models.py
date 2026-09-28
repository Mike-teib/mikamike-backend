"""
models.py — Contrat canonique MikaMike : notions, sources, exercices, quiz.

Tous les objets sont immuables et refusent les champs inconnus. Les invariants de
provenance sont vérifiés à la construction :
  - une notion UNPROVEN n'a PAS de libellé officiel (on n'invente pas de texte officiel) ;
  - une notion PROVEN_OFFICIAL a obligatoirement : source officielle, référence,
    page/section, libellé officiel verbatim et empreinte SHA-256 du document ;
  - rien n'est PUBLISHED sans preuve officielle ET revue humaine approuvée.
La vérification que le libellé figure réellement dans le document est faite par
pedagogy.sources.verify_notion_against_source (preuve recalculée, jamais crue).
"""

from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --------------------------------------------------------------------------- #
# Référentiels
# --------------------------------------------------------------------------- #
class Subject(str, Enum):
    MATHS = "MATHS"
    PHYSIQUE_CHIMIE = "PHYSIQUE_CHIMIE"
    SVT = "SVT"
    # En 6e (cycle 3), la physique-chimie et les SVT relèvent de l'enseignement
    # « Sciences et technologie » : on ne les rattache PAS artificiellement à PC/SVT.
    SCIENCES_TECHNOLOGIE = "SCIENCES_TECHNOLOGIE"
    # Tronc commun de 1re/Tle, pluridisciplinaire.
    ENSEIGNEMENT_SCIENTIFIQUE = "ENSEIGNEMENT_SCIENTIFIQUE"


class Level(str, Enum):
    SIXIEME = "6E"
    CINQUIEME = "5E"
    QUATRIEME = "4E"
    TROISIEME = "3E"
    SECONDE = "2NDE"
    PREMIERE = "1RE"
    TERMINALE = "TLE"


LEVEL_ORDER: Tuple[Level, ...] = tuple(Level)
LEVEL_RANK: Dict[Level, int] = {lv: i for i, lv in enumerate(LEVEL_ORDER)}


class Cycle(str, Enum):
    CYCLE_3 = "CYCLE_3"
    CYCLE_4 = "CYCLE_4"
    LYCEE_GT = "LYCEE_GT"


CYCLE_OF_LEVEL: Dict[Level, Cycle] = {
    Level.SIXIEME: Cycle.CYCLE_3,
    Level.CINQUIEME: Cycle.CYCLE_4,
    Level.QUATRIEME: Cycle.CYCLE_4,
    Level.TROISIEME: Cycle.CYCLE_4,
    Level.SECONDE: Cycle.LYCEE_GT,
    Level.PREMIERE: Cycle.LYCEE_GT,
    Level.TERMINALE: Cycle.LYCEE_GT,
}

# Organisation du système (matière × niveau). Structure générale, À CONFIRMER contre
# les textes officiels lors de l'ingestion (cf. PEDAGOGY_ARCHITECTURE.md, décision D-ORG).
SUBJECT_LEVELS: Dict[Subject, frozenset] = {
    Subject.MATHS: frozenset(Level),
    Subject.PHYSIQUE_CHIMIE: frozenset(LEVEL_ORDER[1:]),
    Subject.SVT: frozenset(LEVEL_ORDER[1:]),
    Subject.SCIENCES_TECHNOLOGIE: frozenset({Level.SIXIEME}),
    Subject.ENSEIGNEMENT_SCIENTIFIQUE: frozenset({Level.PREMIERE, Level.TERMINALE}),
}


class Course(str, Enum):
    """Enseignement suivi (utile au lycée ; COMMON au collège)."""

    COMMON = "COMMON"                              # collège / tronc commun de Seconde
    SPECIALITE = "SPECIALITE"                      # spécialité 1re / Tle
    MATHS_COMPLEMENTAIRES = "MATHS_COMPLEMENTAIRES"
    MATHS_EXPERTES = "MATHS_EXPERTES"
    MATHS_SPECIFIQUES_1RE = "MATHS_SPECIFIQUES_1RE"  # enseignement de maths du tronc commun de 1re
    ENSEIGNEMENT_SCIENTIFIQUE = "ENSEIGNEMENT_SCIENTIFIQUE"


class ProofStatus(str, Enum):
    PROVEN_OFFICIAL = "PROVEN_OFFICIAL"  # libellé verbatim trouvé dans une source officielle enregistrée
    PROVEN_INTERNAL = "PROVEN_INTERNAL"  # validée par une source interne tracée (jamais suffisante pour la banque)
    UNPROVEN = "UNPROVEN"
    CONFLICT = "CONFLICT"                # sources contradictoires (niveau, version, libellé…)
    DEPRECATED = "DEPRECATED"            # ancienne version de programme


class ReviewStatus(str, Enum):
    NOT_REVIEWED = "NOT_REVIEWED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PublicationStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    BLOCKED = "BLOCKED"


class SourceType(str, Enum):
    OFFICIAL_BO = "OFFICIAL_BO"                  # Bulletin officiel (arrêté, programme)
    OFFICIAL_EDUSCOL = "OFFICIAL_EDUSCOL"        # ressources / repères officiels Éduscol
    OFFICIAL_OTHER = "OFFICIAL_OTHER"            # autre document officiel versionné
    INTERNAL_VALIDATED = "INTERNAL_VALIDATED"    # document interne MikaMike validé et tracé
    LEGACY_MIKAMIKE = "LEGACY_MIKAMIKE"          # ancien contenu MikaMike : candidat à auditer
    CANDIDATE_UNVERIFIED = "CANDIDATE_UNVERIFIED"  # candidat à vérifier (aucune preuve)


OFFICIAL_SOURCE_TYPES = frozenset({SourceType.OFFICIAL_BO, SourceType.OFFICIAL_EDUSCOL, SourceType.OFFICIAL_OTHER})

SHA256_RE = r"^[0-9a-f]{64}$"
NOTION_ID_RE = r"^(MATHS|PC|SVT|ST|ES)\.(6E|5E|4E|3E|2NDE|1RE|TLE)\.[A-Z0-9]{2,12}\.[a-z0-9][a-z0-9\-]{1,80}$"
SCHOOL_YEAR_RE = r"^(19|20)\d{2}-(19|20)\d{2}$"

SUBJECT_CODE: Dict[Subject, str] = {
    Subject.MATHS: "MATHS",
    Subject.PHYSIQUE_CHIMIE: "PC",
    Subject.SVT: "SVT",
    Subject.SCIENCES_TECHNOLOGIE: "ST",
    Subject.ENSEIGNEMENT_SCIENTIFIQUE: "ES",
}


def slugify(text: str) -> str:
    base = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", base).strip("-")
    if not s:
        raise ValueError("slug_vide")
    return s[:80].rstrip("-")


def normalize_title(text: str) -> str:
    """Forme de comparaison : NFC, casse repliée, espaces simples, sans ponctuation finale."""
    t = unicodedata.normalize("NFC", text or "").casefold()
    t = " ".join(t.split())
    return t.rstrip(" .;:,")


def make_notion_id(subject: Subject, level: Level, domain_code: str, title: str) -> str:
    """Identifiant STABLE : dépend uniquement de matière, niveau, domaine et titre."""
    code = re.sub(r"[^A-Z0-9]", "", domain_code.upper())[:12]
    if len(code) < 2:
        raise ValueError("code_domaine_invalide")
    return f"{SUBJECT_CODE[subject]}.{level.value}.{code}.{slugify(title)}"


# --------------------------------------------------------------------------- #
# Sources officielles
# --------------------------------------------------------------------------- #
class SourceRetrieval(str, Enum):
    EXPECTED = "EXPECTED"          # document attendu, pas encore récupéré (référence à confirmer)
    RETRIEVED = "RETRIEVED"        # fichier présent localement, empreinte calculée
    VERIFIED = "VERIFIED"          # fichier présent + référence confirmée par une personne


class OfficialSource(_Frozen):
    source_id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9_\-]{2,80}$")
    source_type: SourceType
    title: str = Field(min_length=3, max_length=400)
    publisher: str = Field(min_length=2, max_length=200)
    reference: str = Field(default="", max_length=300, description="ex. BO spécial n°…")
    url: str = Field(default="", max_length=1000)
    subjects: Tuple[Subject, ...] = Field(min_length=1)
    levels: Tuple[Level, ...] = Field(min_length=1)
    courses: Tuple[Course, ...] = (Course.COMMON,)
    school_year_start: str = Field(pattern=SCHOOL_YEAR_RE, description="1re rentrée d'application")
    school_year_end: Optional[str] = Field(default=None, pattern=SCHOOL_YEAR_RE)
    retrieval: SourceRetrieval = SourceRetrieval.EXPECTED
    local_path: str = ""
    sha256: str = ""
    reference_verified: bool = False
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _coherence(self) -> "OfficialSource":
        if self.retrieval != SourceRetrieval.EXPECTED:
            if not self.local_path or not re.fullmatch(SHA256_RE, self.sha256):
                raise ValueError("source_recuperee_sans_fichier_ou_sha256")
        if self.retrieval == SourceRetrieval.VERIFIED and not self.reference_verified:
            raise ValueError("source_verified_sans_reference_confirmee")
        if self.source_type not in OFFICIAL_SOURCE_TYPES and self.source_type != SourceType.INTERNAL_VALIDATED:
            raise ValueError("type_de_source_non_officiel")
        return self


# --------------------------------------------------------------------------- #
# Notion canonique
# --------------------------------------------------------------------------- #
class Notion(_Frozen):
    notion_id: str = Field(pattern=NOTION_ID_RE)
    subject: Subject
    level: Level
    cycle: Cycle
    course: Course = Course.COMMON
    school_year: str = Field(pattern=SCHOOL_YEAR_RE, description="année scolaire visée")
    official_program_version: str = Field(min_length=2, max_length=200)
    domain: str = Field(min_length=2, max_length=200)
    domain_code: str = Field(pattern=r"^[A-Z0-9]{2,12}$")
    chapter: str = Field(min_length=2, max_length=200)
    title: str = Field(min_length=2, max_length=300)
    official_wording: Optional[str] = Field(default=None, max_length=3000)
    normalized_title: str = Field(min_length=2, max_length=300)
    prerequisites: Tuple[str, ...] = ()
    child_notions: Tuple[str, ...] = ()
    related_notions: Tuple[str, ...] = ()
    competency_ids: Tuple[str, ...] = ()
    learning_objectives: Tuple[str, ...] = ()
    expected_skills: Tuple[str, ...] = ()
    common_mistakes: Tuple[str, ...] = ()
    difficulty: int = Field(ge=1, le=5)
    source_type: SourceType
    source_id: Optional[str] = None
    source_title: str = Field(min_length=2, max_length=400)
    source_url_or_ref: str = Field(min_length=2, max_length=1000)
    source_page_or_section: Optional[str] = Field(default=None, max_length=300)
    source_sha256: Optional[str] = Field(default=None, pattern=SHA256_RE)
    proof_status: ProofStatus = ProofStatus.UNPROVEN
    review_status: ReviewStatus = ReviewStatus.NOT_REVIEWED
    publication_status: PublicationStatus = PublicationStatus.DRAFT
    # Traçabilité des candidats (ex. « rappel de connaissances à vérifier », ID legacy)
    provenance_note: str = Field(default="", max_length=2000)
    legacy_ids: Tuple[str, ...] = ()
    optional_in_program: bool = False
    cross_subject_links: Tuple[str, ...] = Field(default=(), description="ex. prérequis Maths d'une notion de PC")

    @model_validator(mode="after")
    def _invariants(self) -> "Notion":
        if self.cycle != CYCLE_OF_LEVEL[self.level]:
            raise ValueError("cycle_incoherent_avec_niveau")
        if self.level not in SUBJECT_LEVELS[self.subject]:
            raise ValueError("matiere_absente_a_ce_niveau")
        if not self.notion_id.startswith(f"{SUBJECT_CODE[self.subject]}.{self.level.value}.{self.domain_code}."):
            raise ValueError("notion_id_incoherent")
        if self.normalized_title != normalize_title(self.title):
            raise ValueError("normalized_title_incoherent")
        if self.notion_id in self.prerequisites:
            raise ValueError("notion_prerequis_d_elle_meme")

        official = self.source_type in OFFICIAL_SOURCE_TYPES
        if self.proof_status == ProofStatus.PROVEN_OFFICIAL:
            missing = [
                name for name, ok in (
                    ("source_officielle", official),
                    ("source_id", bool(self.source_id)),
                    ("page_ou_section", bool(self.source_page_or_section)),
                    ("libelle_officiel", bool(self.official_wording and self.official_wording.strip())),
                    ("sha256", bool(self.source_sha256)),
                ) if not ok
            ]
            if missing:
                raise ValueError("preuve_officielle_incomplete:" + ",".join(missing))
        if self.proof_status == ProofStatus.PROVEN_INTERNAL and self.source_type != SourceType.INTERNAL_VALIDATED:
            raise ValueError("preuve_interne_sans_source_interne")
        if self.proof_status == ProofStatus.UNPROVEN and self.official_wording:
            # On ne stocke jamais un « libellé officiel » non prouvé.
            raise ValueError("libelle_officiel_sur_notion_non_prouvee")
        if self.publication_status == PublicationStatus.PUBLISHED and not (
            self.proof_status == ProofStatus.PROVEN_OFFICIAL and self.review_status == ReviewStatus.APPROVED
        ):
            raise ValueError("publication_sans_preuve_ou_revue")
        return self

    @property
    def eligible_for_content(self) -> bool:
        """Seules les notions PROUVÉES OFFICIELLEMENT alimentent exercices et quiz."""
        return self.proof_status == ProofStatus.PROVEN_OFFICIAL


# --------------------------------------------------------------------------- #
# Exercices
# --------------------------------------------------------------------------- #
class ExerciseType(str, Enum):
    QCM = "QCM"
    SHORT_ANSWER = "SHORT_ANSWER"
    CALCULATION = "CALCULATION"
    PROBLEM = "PROBLEM"
    REASONING = "REASONING"
    TRUE_FALSE_ARGUED = "TRUE_FALSE_ARGUED"
    MATCHING = "MATCHING"
    ORDERING = "ORDERING"
    DOCUMENT_READING = "DOCUMENT_READING"
    GRAPH_INTERPRETATION = "GRAPH_INTERPRETATION"
    EXPERIMENT_PROTOCOL = "EXPERIMENT_PROTOCOL"
    SITUATION_STUDY = "SITUATION_STUDY"


class DifficultyBand(str, Enum):
    DISCOVERY = "DISCOVERY"          # découverte
    APPLICATION = "APPLICATION"
    CONSOLIDATION = "CONSOLIDATION"
    ADVANCED = "ADVANCED"


BANK_TARGET: Dict[DifficultyBand, int] = {
    DifficultyBand.DISCOVERY: 5,
    DifficultyBand.APPLICATION: 5,
    DifficultyBand.CONSOLIDATION: 5,
    DifficultyBand.ADVANCED: 3,
}
QUIZ_TARGET_PER_NOTION = 10


class AnswerKind(str, Enum):
    MATH_EXPR = "MATH_EXPR"        # vérification symbolique (SymPy)
    QUANTITY = "QUANTITY"          # valeur + unité (analyse dimensionnelle)
    EXACT_TEXT = "EXACT_TEXT"      # texte court normalisé
    CHOICE = "CHOICE"              # index(es) de choix
    BOOLEAN = "BOOLEAN"            # vrai / faux (+ argument noté par rubrique)
    ORDERING = "ORDERING"          # suite ordonnée d'éléments
    MATCHING = "MATCHING"          # paires gauche → droite
    RUBRIC = "RUBRIC"              # réponse rédigée : critères observables obligatoires


class ExpectedAnswer(_Frozen):
    kind: AnswerKind
    value: Any
    unit: Optional[str] = None
    tolerance_relative: Optional[float] = Field(default=None, ge=0, le=0.5)
    significant_figures: Optional[int] = Field(default=None, ge=1, le=10)
    required_form: Optional[str] = None  # ex. fraction_irreductible, developpee, factorisee
    rubric: Tuple[str, ...] = ()          # critères observables (kind RUBRIC / BOOLEAN)


class GenerationOrigin(str, Enum):
    HUMAN_AUTHORED = "HUMAN_AUTHORED"
    MODEL_ASSISTED_DRAFT = "MODEL_ASSISTED_DRAFT"  # rédigé avec assistance, relecture humaine obligatoire
    IMPORTED_LEGACY = "IMPORTED_LEGACY"
    FIXTURE_TEST = "FIXTURE_TEST"                  # jeu de test, jamais publiable


class QAStatus(str, Enum):
    NOT_CHECKED = "NOT_CHECKED"
    AUTO_PASSED = "AUTO_PASSED"
    AUTO_FAILED = "AUTO_FAILED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class Exercise(_Frozen):
    exercise_id: str = Field(pattern=r"^EX\.[A-Za-z0-9.\-]{3,160}$")
    notion_id: str = Field(pattern=NOTION_ID_RE)
    subject: Subject
    level: Level
    difficulty: DifficultyBand
    exercise_type: ExerciseType
    statement: str = Field(min_length=5, max_length=6000)
    expected_answer: ExpectedAnswer
    solution: str = Field(min_length=1, max_length=6000)
    step_by_step_solution: Tuple[str, ...] = Field(min_length=1)
    hints: Tuple[str, ...] = Field(min_length=1, max_length=6)
    common_errors: Dict[str, str] = Field(default_factory=dict, description="réponse fausse → diagnostic")
    remediation: str = Field(min_length=5, max_length=3000)
    estimated_time_min: int = Field(ge=1, le=120)
    skills_tested: Tuple[str, ...] = Field(min_length=1)
    prerequisites: Tuple[str, ...] = ()
    source_notions: Tuple[str, ...] = Field(min_length=1)
    choices: Tuple[str, ...] = ()        # QCM / association / ordre
    generation_origin: GenerationOrigin
    qa_status: QAStatus = QAStatus.NOT_CHECKED
    publication_status: PublicationStatus = PublicationStatus.DRAFT

    @model_validator(mode="after")
    def _coherence(self) -> "Exercise":
        if self.notion_id not in self.source_notions:
            raise ValueError("notion_absente_des_source_notions")
        if self.exercise_type == ExerciseType.QCM and len(self.choices) < 3:
            raise ValueError("qcm_moins_de_3_choix")
        if self.publication_status == PublicationStatus.PUBLISHED and self.qa_status != QAStatus.HUMAN_APPROVED:
            raise ValueError("publication_sans_validation_humaine")
        if self.generation_origin == GenerationOrigin.FIXTURE_TEST and self.publication_status != PublicationStatus.DRAFT:
            raise ValueError("fixture_non_publiable")
        return self


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #
class QuizItem(_Frozen):
    quiz_id: str = Field(pattern=r"^QZ\.[A-Za-z0-9.\-]{3,160}$")
    notion_id: str = Field(pattern=NOTION_ID_RE)
    subject: Subject
    level: Level
    question: str = Field(min_length=5, max_length=2000)
    choices: Tuple[str, ...] = Field(min_length=3, max_length=6)
    correct_answer: int = Field(ge=0, description="index de la seule bonne réponse")
    reference_answer: str = Field(min_length=1, max_length=500, description="clé indépendante des choix")
    answer_kind: AnswerKind = AnswerKind.EXACT_TEXT
    explanation: str = Field(min_length=10, max_length=3000)
    difficulty: DifficultyBand
    distractor_rationale: Dict[int, str] = Field(default_factory=dict, description="index → pourquoi c'est faux")
    common_error_target: Dict[int, str] = Field(default_factory=dict, description="index → erreur fréquente visée")
    generation_origin: GenerationOrigin
    qa_status: QAStatus = QAStatus.NOT_CHECKED
    publication_status: PublicationStatus = PublicationStatus.DRAFT

    @model_validator(mode="after")
    def _coherence(self) -> "QuizItem":
        if self.correct_answer >= len(self.choices):
            raise ValueError("bonne_reponse_hors_bornes")
        if self.correct_answer in self.distractor_rationale:
            raise ValueError("justification_de_distracteur_sur_la_bonne_reponse")
        bad = set(self.distractor_rationale) | set(self.common_error_target)
        if any(i < 0 or i >= len(self.choices) for i in bad):
            raise ValueError("index_de_distracteur_hors_bornes")
        if self.publication_status == PublicationStatus.PUBLISHED and self.qa_status != QAStatus.HUMAN_APPROVED:
            raise ValueError("publication_sans_validation_humaine")
        return self


# --------------------------------------------------------------------------- #
# Conteneurs de fichiers
# --------------------------------------------------------------------------- #
class NotionFile(_Frozen):
    """Un fichier de registre : une matière × un niveau (× un enseignement)."""

    schema_version: str = "1.0"
    subject: Subject
    level: Level
    course: Course = Course.COMMON
    generated_by: str = Field(min_length=2, max_length=200)
    disclaimer: str = Field(min_length=10, max_length=2000)
    notions: Tuple[Notion, ...]

    @model_validator(mode="after")
    def _homogene(self) -> "NotionFile":
        for n in self.notions:
            if n.subject != self.subject or n.level != self.level or n.course != self.course:
                raise ValueError(f"notion_hors_fichier:{n.notion_id}")
        ids = [n.notion_id for n in self.notions]
        if len(ids) != len(set(ids)):
            raise ValueError("notion_id_duplique_dans_fichier")
        return self


def json_schema_bundle() -> Dict[str, Any]:
    """Schémas JSON exportables (documentation, outillage externe)."""
    return {
        "Notion": Notion.model_json_schema(),
        "NotionFile": NotionFile.model_json_schema(),
        "OfficialSource": OfficialSource.model_json_schema(),
        "Exercise": Exercise.model_json_schema(),
        "QuizItem": QuizItem.model_json_schema(),
    }


def as_list(x: Any) -> List[Any]:
    return list(x) if isinstance(x, (list, tuple)) else [x]
