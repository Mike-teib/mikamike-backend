"""Validateur de quiz (agent D) : un test positif + négatif par code d'anomalie.

Toutes les données sont FICTIVES ([FICTIF], generation_origin FIXTURE_TEST).
"""

from __future__ import annotations

from typing import Dict

import pytest

from pedagogy.issues import Severity
from pedagogy.models import (
    CYCLE_OF_LEVEL,
    SUBJECT_CODE,
    Level,
    Notion,
    OfficialSource,
    QuizItem,
    Subject,
    normalize_title,
)
from pedagogy.registry import Registry
from pedagogy.validators.quiz import validate_quiz

SHA = "fedcba9876543210" * 4
SRC = "SRC-FICTIF-QZ"


def make_notion(subject: Subject, level: Level, code: str, slug: str, *, proven: bool = True,
                source_id: str = SRC, **kw) -> Notion:
    title = f"[FICTIF] {slug}"
    d = dict(
        notion_id=f"{SUBJECT_CODE[subject]}.{level.value}.{code}.{slug}",
        subject=subject, level=level, cycle=CYCLE_OF_LEVEL[level], school_year="2025-2026",
        official_program_version="programme fictif", domain="Domaine fictif", domain_code=code,
        chapter="Chapitre fictif", title=title, normalized_title=normalize_title(title), difficulty=2,
        source_type="OFFICIAL_BO", source_title="Programme fictif", source_url_or_ref="BO fictif",
    )
    if proven:
        d.update(proof_status="PROVEN_OFFICIAL", review_status="APPROVED", source_id=source_id, source_page_or_section="§ 2",
                 official_wording="[FICTIF] libellé officiel", source_sha256=SHA)
    d.update(kw)
    return Notion(**d)


N_FRAC = "MATHS.4E.NC.fractions-fictives"
N_VIT = "PC.4E.MVT.vitesse-fictive"
N_CELL = "SVT.5E.VIV.cellule-fictive"
N_UNPROVEN = "MATHS.4E.NC.non-prouvee"
N_NOSRC = "MATHS.4E.NC.source-absente"
N_UNAPPROVED = "MATHS.4E.NC.non-approuvee"
N_PUB = "MATHS.4E.NC.publiee-fictive"


def make_registry() -> Registry:
    reg = Registry()
    reg.sources[SRC] = OfficialSource(
        source_id=SRC, source_type="OFFICIAL_BO", title="[FICTIF] Programme de test", publisher="Test",
        subjects=("MATHS", "PHYSIQUE_CHIMIE", "SVT"), levels=("5E", "4E"), school_year_start="2020-2021",
    )
    for n in (
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "fractions-fictives"),
        make_notion(Subject.PHYSIQUE_CHIMIE, Level.QUATRIEME, "MVT", "vitesse-fictive"),
        make_notion(Subject.SVT, Level.CINQUIEME, "VIV", "cellule-fictive"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "non-prouvee", proven=False),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "source-absente", source_id="SRC-ABSENTE"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "non-approuvee", review_status="NOT_REVIEWED"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "publiee-fictive",
                    review_status="APPROVED", publication_status="PUBLISHED"),
    ):
        reg.notions[n.notion_id] = n
    return reg


REG = make_registry()


def base(**kw) -> Dict:
    d = dict(
        quiz_id="QZ.FICTIF.frac-001", notion_id=N_FRAC, subject="MATHS", level="4E",
        question="[FICTIF] Combien vaut 1/2 + 1/3 ?",
        choices=("5/6", "2/5", "1/6", "2/6"),
        correct_answer=0, reference_answer="5/6", answer_kind="MATH_EXPR",
        explanation="On réduit au même dénominateur : 1/2 + 1/3 = 3/6 + 2/6 = 5/6.",
        difficulty="APPLICATION",
        distractor_rationale={1: "addition des numérateurs et des dénominateurs", 2: "soustraction au lieu "
                              "d'addition", 3: "dénominateur commun sans convertir les numérateurs"},
        common_error_target={1: "somme terme à terme"},
        generation_origin="FIXTURE_TEST",
    )
    d.update(kw)
    return d


def qz(**kw) -> QuizItem:
    return QuizItem(**base(**kw))


def codes(q: QuizItem, reg: Registry = REG):
    return {i.code for i in validate_quiz(q, reg)}


GOOD = {
    "maths": base(),
    "latex": base(quiz_id="QZ.FICTIF.frac-002", question="[FICTIF] Combien vaut $\\frac{1}{2} + \\frac{1}{3}$ ?",
                  choices=("$\\frac{5}{6}$", "$\\frac{2}{5}$", "$\\frac{1}{6}$", "$\\frac{2}{6}$")),
    "grandeur": base(quiz_id="QZ.FICTIF.vit-001", notion_id=N_VIT, subject="PHYSIQUE_CHIMIE",
                     question="[FICTIF] Un cycliste parcourt 30 km en 2 h. Quelle est sa vitesse moyenne ?",
                     choices=("15 km/h", "60 km/h", "32 km/h", "15 m/s"), reference_answer="15 km/h",
                     answer_kind="QUANTITY", explanation="v = d / t = 30 km / 2 h = 15 km/h.",
                     distractor_rationale={1: "produit au lieu du quotient", 2: "somme des données",
                                           3: "unité incorrecte"}, common_error_target={}),
    "texte": base(quiz_id="QZ.FICTIF.cel-001", notion_id=N_CELL, subject="SVT", level="5E",
                  question="[FICTIF] Quelle structure contient l'information génétique de la cellule ?",
                  choices=("le noyau", "la membrane", "le cytoplasme"), reference_answer="noyau",
                  answer_kind="EXACT_TEXT",
                  explanation="Chez les cellules animales et végétales, l'ADN est contenu dans le noyau.",
                  distractor_rationale={1: "limite la cellule", 2: "contient les organites"},
                  common_error_target={}),
    "booleen": base(quiz_id="QZ.FICTIF.frac-003", question="[FICTIF] Vrai ou faux : 2/4 est égal à 1/2.",
                    choices=("Vrai", "Faux", "Seulement si on arrondit"), reference_answer="vrai",
                    answer_kind="BOOLEAN", explanation="2/4 se simplifie par 2 et donne 1/2 : c'est vrai.",
                    distractor_rationale={1: "simplification oubliée", 2: "aucun arrondi n'est nécessaire"},
                    common_error_target={}),
}


@pytest.mark.parametrize("name", sorted(GOOD))
def test_fixtures_realistes_sans_anomalie(name):
    issues = validate_quiz(QuizItem(**GOOD[name]), REG)
    assert issues == [], issues


POSITIVE = {
    "NOTION_UNKNOWN": dict(notion_id="MATHS.4E.NC.inconnue-fictive"),
    "NOTION_NOT_PROVEN": dict(notion_id=N_UNPROVEN),
    "NOTION_NOT_APPROVED": dict(notion_id=N_UNAPPROVED),
    "NOTION_WITHOUT_SOURCE": dict(notion_id=N_NOSRC),
    "LEVEL_MISMATCH": dict(level="3E"),
    "SUBJECT_MISMATCH": dict(subject="PHYSIQUE_CHIMIE"),
    "CORRECT_ANSWER_WRONG": dict(correct_answer=1, distractor_rationale={0: "x", 2: "y", 3: "z"}),
    "CORRECT_ANSWER_UNDECIDABLE": dict(choices=("cinq sixièmes", "2/5", "1/6", "2/6")),
    "MULTIPLE_CORRECT": dict(choices=("5/6", "10/12", "1/6", "2/6")),
    "DISTRACTOR_UNDECIDABLE": dict(choices=("5/6", "deux cinquièmes", "1/6", "2/6")),
    "DUPLICATE_CHOICES": dict(choices=("5/6", "1/6", "1/6 ", "2/6")),
    "EMPTY_CHOICE": dict(choices=("5/6", "2/5", "  ", "2/6")),
    "AMBIGUOUS_CHOICE": dict(choices=("5/6", "2/5", "1/6", "Aucune de ces réponses")),
    "ANSWER_IN_QUESTION": dict(question="[FICTIF] Montrer que 1/2 + 1/3 = 5/6. Combien vaut 1/2 + 1/3 ?"),
    "EXPLANATION_MISSING": dict(explanation="             "),
    "EXPLANATION_TOO_SHORT": dict(explanation="Car 3/6+2/6."),
    "DISTRACTOR_RATIONALE_MISSING": dict(distractor_rationale={1: "somme terme à terme"}),
    "LENGTH_LEAK": dict(choices=("5/6, obtenu en réduisant au même dénominateur 6", "2/5", "1/6", "2/6"),
                        reference_answer="5/6"),
    "IMPLAUSIBLE_DISTRACTOR": dict(choices=("5/6", "2/5", "banane", "2/6")),
    "MATH_NOTATION_BROKEN": dict(explanation="On obtient $\\frac{5}{6$ après réduction au même dénominateur."),
    "PUBLISHED_FORBIDDEN": dict(generation_origin="HUMAN_AUTHORED", qa_status="HUMAN_APPROVED",
                                publication_status="PUBLISHED"),
}

SEVERITY = {
    "CORRECT_ANSWER_WRONG": Severity.BLOCKER, "MULTIPLE_CORRECT": Severity.BLOCKER,
    "NOTION_NOT_PROVEN": Severity.BLOCKER, "NOTION_NOT_APPROVED": Severity.BLOCKER, "PUBLISHED_FORBIDDEN": Severity.BLOCKER,
    "DISTRACTOR_RATIONALE_MISSING": Severity.WARNING, "LENGTH_LEAK": Severity.WARNING,
    "IMPLAUSIBLE_DISTRACTOR": Severity.WARNING, "FIXTURE_IN_BANK": Severity.WARNING,
}


@pytest.mark.parametrize("code", sorted(POSITIVE))
def test_code_positif(code):
    issues = validate_quiz(qz(**POSITIVE[code]), REG)
    found = [i for i in issues if i.code == code]
    assert found, (code, issues)
    if code in SEVERITY:
        assert found[0].severity == SEVERITY[code]


@pytest.mark.parametrize("code", sorted(POSITIVE) + ["FIXTURE_IN_BANK"])
def test_code_negatif_sur_quiz_conforme(code):
    assert code not in codes(qz())


def test_fixture_in_bank():
    q = qz()
    reg = make_registry()
    reg.quizzes[q.quiz_id] = q
    assert "FIXTURE_IN_BANK" in codes(q, reg)


def test_notion_publiee_interdite():
    assert "PUBLISHED_FORBIDDEN" in codes(qz(notion_id=N_PUB))


def test_ambiguous_choice_variantes():
    for c in ("Toutes les réponses", "Je ne sais pas", "aucune"):
        assert "AMBIGUOUS_CHOICE" in codes(qz(choices=("5/6", "2/5", "1/6", c)))
    # « Aucun arrondi » n'est pas un choix ambigu (mot différent)
    assert "AMBIGUOUS_CHOICE" not in codes(qz(choices=("5/6", "2/5", "1/6", "Aucun arrondi possible")))


def test_grandeur_unite_equivalente_est_multiple_correct():
    d = GOOD["grandeur"] | {"choices": ("15 km/h", "60 km/h", "32 km/h", "15000 m/h")}
    assert "MULTIPLE_CORRECT" in codes(QuizItem(**d))


def test_grandeur_mauvaise_unite_nest_pas_correcte():
    d = GOOD["grandeur"] | {"correct_answer": 3, "distractor_rationale": {0: "a", 1: "b", 2: "c"}}
    assert "CORRECT_ANSWER_WRONG" in codes(QuizItem(**d))


def test_texte_mauvaise_cle():
    d = GOOD["texte"] | {"reference_answer": "mitochondrie"}
    assert "CORRECT_ANSWER_WRONG" in codes(QuizItem(**d))


def test_answer_in_question_frontiere_de_jeton():
    # « 5/6 » n'apparaît pas dans « 5/60 »
    assert "ANSWER_IN_QUESTION" not in codes(qz(question="[FICTIF] Sachant que 5/60 = 1/12, combien vaut 1/2 + 1/3 ?"))


def test_rubric_interdit_en_quiz():
    assert "CORRECT_ANSWER_UNDECIDABLE" in codes(qz(answer_kind="RUBRIC"))


def test_codes_documentes_dans_le_module():
    import pedagogy.validators.quiz as mod
    for code in list(POSITIVE) + ["FIXTURE_IN_BANK"]:
        assert code in mod.__doc__
