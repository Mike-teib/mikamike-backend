"""Validateur d'exercice (agent D) : un test positif + négatif par code d'anomalie.

Toutes les données sont FICTIVES ([FICTIF], generation_origin FIXTURE_TEST).
"""

from __future__ import annotations

from typing import Dict

import pytest

from pedagogy.issues import Severity
from pedagogy.models import (
    CYCLE_OF_LEVEL,
    SUBJECT_CODE,
    Exercise,
    Level,
    Notion,
    OfficialSource,
    Subject,
    normalize_title,
)
from pedagogy.registry import Registry
from pedagogy.validators.exercise import validate_exercise

SHA = "0123456789abcdef" * 4
SRC = "SRC-FICTIF-01"


# --------------------------------------------------------------------------- #
# Registre fictif
# --------------------------------------------------------------------------- #
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
        d.update(proof_status="PROVEN_OFFICIAL", review_status="APPROVED", source_id=source_id, source_page_or_section="p. 1",
                 official_wording="[FICTIF] libellé officiel", source_sha256=SHA)
    d.update(kw)
    return Notion(**d)


N_FRAC = "MATHS.4E.NC.fractions-fictives"
N_EQ = "MATHS.4E.ALG.equations-fictives"
N_GEO = "MATHS.4E.GEO.pythagore-fictif"
N_VIT = "PC.4E.MVT.vitesse-fictive"
N_PH = "PC.3E.CHIM.ph-fictif"
N_ORG = "SVT.5E.CORPS.organes-fictifs"
N_UNPROVEN = "MATHS.4E.NC.non-prouvee"
N_NOSRC = "MATHS.4E.NC.source-absente"
N_UNAPPROVED = "MATHS.4E.NC.non-approuvee"
N_PUB = "MATHS.4E.NC.publiee-fictive"


def make_registry() -> Registry:
    reg = Registry()
    reg.sources[SRC] = OfficialSource(
        source_id=SRC, source_type="OFFICIAL_BO", title="[FICTIF] Programme de test", publisher="Test",
        subjects=("MATHS", "PHYSIQUE_CHIMIE", "SVT"), levels=("5E", "4E", "3E"), school_year_start="2020-2021",
    )
    for n in (
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "fractions-fictives"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "ALG", "equations-fictives"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "GEO", "pythagore-fictif"),
        make_notion(Subject.PHYSIQUE_CHIMIE, Level.QUATRIEME, "MVT", "vitesse-fictive"),
        make_notion(Subject.PHYSIQUE_CHIMIE, Level.TROISIEME, "CHIM", "ph-fictif"),
        make_notion(Subject.SVT, Level.CINQUIEME, "CORPS", "organes-fictifs"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "non-prouvee", proven=False),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "source-absente", source_id="SRC-ABSENTE"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "non-approuvee", review_status="NOT_REVIEWED"),
        make_notion(Subject.MATHS, Level.QUATRIEME, "NC", "publiee-fictive",
                    review_status="APPROVED", publication_status="PUBLISHED"),
    ):
        reg.notions[n.notion_id] = n
    return reg


REG = make_registry()


def base(notion_id: str = N_FRAC, subject: str = "MATHS", level: str = "4E", **kw) -> Dict:
    d = dict(
        exercise_id="EX.FICTIF.calc-001",
        notion_id=notion_id, subject=subject, level=level,
        difficulty="APPLICATION", exercise_type="CALCULATION",
        statement="[FICTIF] Calculer 2/3 × 9/4 et donner le résultat sous forme de fraction irréductible.",
        expected_answer={"kind": "MATH_EXPR", "value": "3/2", "required_form": "fraction_irreductible"},
        solution="On multiplie les numérateurs et les dénominateurs : 2/3 × 9/4 = 18/12 = 3/2.",
        step_by_step_solution=("2 × 9 = 18 et 3 × 4 = 12, donc 2/3 × 9/4 = 18/12.",
                               "On simplifie par 6 : 18/12 = 3/2."),
        hints=("Multiplie les numérateurs entre eux et les dénominateurs entre eux, puis simplifie.",),
        common_errors={"18/12": "fraction non simplifiée", "11/7": "addition des termes au lieu du produit"},
        remediation="Revoir la multiplication de deux fractions puis la simplification.",
        estimated_time_min=4, skills_tested=("calculer",), source_notions=(notion_id,),
        generation_origin="FIXTURE_TEST",
    )
    d.update(kw)
    if "source_notions" not in kw:
        d["source_notions"] = (d["notion_id"],)
    return d


def ex(**kw) -> Exercise:
    return Exercise(**base(**kw))


def codes(e: Exercise, reg: Registry = REG):
    return {i.code for i in validate_exercise(e, reg)}


# --------------------------------------------------------------------------- #
# Fixtures réalistes de plusieurs types : aucun défaut attendu
# --------------------------------------------------------------------------- #
GOOD = {
    "calcul_fraction": base(),
    "qcm": base(
        exercise_id="EX.FICTIF.qcm-001", exercise_type="QCM", difficulty="DISCOVERY",
        statement="[FICTIF] Quelle est la valeur de 1/2 + 1/4 ?",
        choices=("3/4", "2/6", "1/6", "1/8"),
        expected_answer={"kind": "CHOICE", "value": 0},
        solution="On écrit 1/2 = 2/4, puis 2/4 + 1/4 = 3/4.",
        step_by_step_solution=("1/2 = 2/4.", "2/4 + 1/4 = 3/4."),
        hints=("Mets les deux fractions au même dénominateur.",),
        common_errors={"1": "addition des numérateurs et des dénominateurs"},
    ),
    "equation": base(
        exercise_id="EX.FICTIF.eq-001", notion_id=N_EQ,
        statement="[FICTIF] Résoudre l'équation 2x + 5 = 11.",
        expected_answer={"kind": "MATH_EXPR", "value": "x = 3"},
        solution="2x + 5 = 11 donc 2x = 6 donc x = 3.",
        step_by_step_solution=("On soustrait 5 : 2x = 11 - 5 = 6.", "On divise par 2 : x = 6/2 = 3."),
        hints=("Isole le terme en x.",), common_errors={"x = 8": "a ajouté 5 au lieu de soustraire"},
    ),
    "developpement": base(
        exercise_id="EX.FICTIF.dev-001", notion_id=N_EQ,
        statement="[FICTIF] Développer et réduire $(x+1)^2$.",
        expected_answer={"kind": "MATH_EXPR", "value": "x^2 + 2x + 1", "required_form": "developpee"},
        solution="On applique $(a+b)^2 = a^2 + 2ab + b^2$ : $(x+1)^2 = x^2 + 2x + 1$.",
        step_by_step_solution=("$(x+1)^2 = x^2 + 2 \\times x \\times 1 + 1^2$", "$= x^2 + 2x + 1$"),
        hints=("Utilise l'identité remarquable $(a+b)^2$.",),
        common_errors={"x^2 + 1": "oubli du double produit"},
    ),
    "grandeur_vitesse": base(
        exercise_id="EX.FICTIF.vit-001", notion_id=N_VIT, subject="PHYSIQUE_CHIMIE",
        statement="[FICTIF] Une voiture parcourt 150 km en 2 h. Calculer sa vitesse moyenne en km/h.",
        expected_answer={"kind": "QUANTITY", "value": 75, "unit": "km/h", "significant_figures": 2},
        solution="v = d / t = 150 km / 2 h = 75 km/h.",
        step_by_step_solution=("v = d / t", "v = 150 / 2 = 75 km/h"),
        hints=("La vitesse moyenne est le quotient de la distance par la durée.",),
        common_errors={"300 km/h": "multiplication au lieu de division", "75": "unité oubliée"},
    ),
    "grandeur_sci": base(
        exercise_id="EX.FICTIF.vit-002", notion_id=N_VIT, subject="PHYSIQUE_CHIMIE",
        statement="[FICTIF] Convertir 72 km/h en m/s.",
        expected_answer={"kind": "QUANTITY", "value": "20", "unit": "m/s", "tolerance_relative": 0.01},
        solution="72 km/h = 72 000 m / 3 600 s = 20 m/s.",
        step_by_step_solution=("1 km/h = 1000 m / 3600 s.", "72 / 3,6 = 20 m/s."),
        hints=("Divise par 3,6.",), common_errors={"259,2 m/s": "multiplié par 3,6"},
    ),
    "ordering": base(
        exercise_id="EX.FICTIF.ord-001", notion_id=N_VIT, subject="PHYSIQUE_CHIMIE", exercise_type="ORDERING",
        statement="[FICTIF] Range ces longueurs de la plus petite à la plus grande : 1 km ; 1 cm ; 1 m ; 1 mm.",
        choices=("1 km", "1 cm", "1 m", "1 mm"),
        expected_answer={"kind": "ORDERING", "value": ["1 mm", "1 cm", "1 m", "1 km"]},
        solution="1 mm < 1 cm < 1 m < 1 km.", step_by_step_solution=("On convertit tout en mètres.",
                                                                       "0,001 m < 0,01 m < 1 m < 1000 m."),
        hints=("Convertis chaque longueur en mètres.",), common_errors={"1 km ; 1 m ; 1 cm ; 1 mm": "ordre inversé"},
    ),
    "matching": base(
        exercise_id="EX.FICTIF.mat-001", notion_id=N_ORG, subject="SVT", level="5E", exercise_type="MATCHING",
        statement="[FICTIF] Associe chaque organe à sa fonction principale.",
        choices=("cœur", "poumons", "pomper le sang", "échanges gazeux"),
        expected_answer={"kind": "MATCHING", "value": {"cœur": "pomper le sang", "poumons": "échanges gazeux"}},
        solution="Le cœur met le sang en mouvement ; les poumons assurent les échanges gazeux.",
        step_by_step_solution=("Cœur → pomper le sang.", "Poumons → échanges gazeux."),
        hints=("Pense au trajet de l'air et à celui du sang.",),
        common_errors={"cœur -> échanges gazeux ; poumons -> pomper le sang": "fonctions inversées"},
    ),
    "exact_text": base(
        exercise_id="EX.FICTIF.txt-001", notion_id=N_ORG, subject="SVT", level="5E", exercise_type="SHORT_ANSWER",
        statement="[FICTIF] Quel gaz les végétaux chlorophylliens rejettent-ils à la lumière ?",
        expected_answer={"kind": "EXACT_TEXT", "value": ["dioxygène", "O2"]},
        solution="À la lumière, la photosynthèse produit du dioxygène.",
        step_by_step_solution=("La photosynthèse consomme du dioxyde de carbone.", "Elle rejette du dioxygène."),
        hints=("Pense à la photosynthèse.",), common_errors={"dioxyde de carbone": "confusion gaz absorbé / rejeté"},
    ),
    "vrai_faux_argumente": base(
        exercise_id="EX.FICTIF.vf-001", notion_id=N_FRAC, exercise_type="TRUE_FALSE_ARGUED",
        statement="[FICTIF] Vrai ou faux ? « La somme de deux fractions s'obtient en ajoutant les numérateurs et "
                  "les dénominateurs. » Justifie.",
        expected_answer={"kind": "RUBRIC", "value": "Faux, avec un contre-exemple.",
                         "rubric": ("Répond « faux »", "Donne un contre-exemple chiffré correct")},
        solution="Faux : 1/2 + 1/2 = 1 alors que la règle proposée donnerait 2/4.",
        step_by_step_solution=("On teste la règle sur un exemple.", "1/2 + 1/2 = 1 ≠ 2/4 : la règle est fausse."),
        hints=("Essaie avec 1/2 + 1/2.",),
    ),
    "lecture_document": base(
        exercise_id="EX.FICTIF.doc-001", notion_id=N_ORG, subject="SVT", level="5E", exercise_type="DOCUMENT_READING",
        statement="[FICTIF] Document : fréquence cardiaque d'un élève au repos (70 battements/min) puis après une "
                  "course (130 battements/min). Décris et explique l'évolution.",
        expected_answer={"kind": "RUBRIC", "value": "Augmentation expliquée par les besoins des muscles.",
                         "rubric": ("Cite les deux valeurs", "Indique l'augmentation",
                                    "Relie à l'apport de dioxygène aux muscles")},
        solution="La fréquence passe de 70 à 130 battements/min : les muscles ont besoin de plus de dioxygène.",
        step_by_step_solution=("Relever les valeurs.", "Expliquer par les besoins des muscles."),
        hints=("Compare les deux valeurs du document.",),
    ),
    "qcm_plusieurs": base(
        exercise_id="EX.FICTIF.qcm-002", exercise_type="QCM",
        statement="[FICTIF] Coche toutes les bonnes réponses : quelles fractions sont égales à 1/2 ?",
        choices=("2/4", "3/5", "5/10", "1/3"),
        expected_answer={"kind": "CHOICE", "value": [0, 2]},
        solution="2/4 = 1/2 et 5/10 = 1/2 ; 3/5 et 1/3 sont différentes de 1/2.",
        step_by_step_solution=("On simplifie chaque fraction.", "Les fractions 2/4 et 5/10 valent 1/2."),
        hints=("Simplifie chaque fraction.",),
    ),
    "pythagore_point_A": base(
        exercise_id="EX.FICTIF.geo-001", notion_id=N_GEO,
        statement="[FICTIF] Le triangle ABC est rectangle en A avec AB = 3 cm et AC = 4 cm. Calculer BC.",
        expected_answer={"kind": "QUANTITY", "value": 5, "unit": "cm"},
        solution="BC² = AB² + AC² = 9 + 16 = 25 donc BC = 5 cm.",
        step_by_step_solution=("BC² = 3² + 4² = 25", "BC = 5 cm"),
        hints=("Utilise le théorème de Pythagore.",),
    ),
}


@pytest.mark.parametrize("name", sorted(GOOD))
def test_fixtures_realistes_sans_anomalie(name):
    issues = validate_exercise(Exercise(**GOOD[name]), REG)
    assert issues == [], issues


# --------------------------------------------------------------------------- #
# Un cas positif par code
# --------------------------------------------------------------------------- #
FICTIVE_UNKNOWN = "MATHS.4E.NC.inconnue-fictive"

POSITIVE = {
    "NOTION_UNKNOWN": dict(notion_id=FICTIVE_UNKNOWN),
    "NOTION_NOT_PROVEN": dict(notion_id=N_UNPROVEN),
    "NOTION_NOT_APPROVED": dict(notion_id=N_UNAPPROVED),
    "NOTION_WITHOUT_SOURCE": dict(notion_id=N_NOSRC),
    "LEVEL_MISMATCH": dict(level="3E"),
    "SUBJECT_MISMATCH": dict(subject="PHYSIQUE_CHIMIE"),
    "PREREQUISITE_UNKNOWN": dict(prerequisites=(FICTIVE_UNKNOWN,)),
    "SOURCE_NOTION_UNKNOWN": dict(source_notions=(N_FRAC, FICTIVE_UNKNOWN)),
    "ANSWER_MISSING": dict(expected_answer={"kind": "MATH_EXPR", "value": "  "}),
    "SOLUTION_MISSING": dict(solution="   "),
    "SOLUTION_INCONSISTENT": dict(solution="2/3 × 9/4 = 5/4.", step_by_step_solution=("On trouve 5/4.",)),
    "SELF_CHECK_FAILED": dict(expected_answer={"kind": "MATH_EXPR", "value": "18/12",
                                               "required_form": "fraction_irreductible"}),
    "AMBIGUOUS_ANSWER": dict(expected_answer={"kind": "MATH_EXPR", "value": "trois demis"}),
    "QCM_NO_CORRECT": dict(exercise_type="QCM", choices=("3/2", "1/2", "2/3"),
                           expected_answer={"kind": "CHOICE", "value": 5}),
    "QCM_MULTIPLE_CORRECT": dict(exercise_type="QCM", choices=("3/2", "1/2", "2/3"),
                                 expected_answer={"kind": "CHOICE", "value": [0, 1]}),
    "ANSWER_IN_STATEMENT": dict(statement="[FICTIF] Montrer que 2/3 × 9/4 vaut 3/2."),
    "MATH_NOTATION_BROKEN": dict(statement="[FICTIF] Calculer $\\frac{2}{3 \\times \\frac{9}{4}$."),
    "UNIT_INCOHERENT": dict(notion_id=N_VIT, subject="PHYSIQUE_CHIMIE",
                            statement="[FICTIF] Une voiture parcourt 150 km en 2 h. Calculer sa vitesse en km/h.",
                            expected_answer={"kind": "QUANTITY", "value": 75, "unit": "kg"},
                            solution="v = 75 kg", step_by_step_solution=("v = 75 kg",)),
    "PHYSICALLY_IMPOSSIBLE": dict(notion_id=N_VIT, subject="PHYSIQUE_CHIMIE",
                                  statement="[FICTIF] Calculer la vitesse de la particule en m/s.",
                                  expected_answer={"kind": "QUANTITY", "value": "4,0 × 10^8", "unit": "m/s"},
                                  solution="v = 4,0 × 10^8 m/s", step_by_step_solution=("v = 4,0 × 10^8 m/s",)),
    "COMMON_ERROR_ACTUALLY_CORRECT": dict(common_errors={"6/4 ": "« erreur » qui est en fait… non simplifiée",
                                                         "3/2": "listée à tort comme erreur"}),
    "HINT_REVEALS_ANSWER": dict(hints=("Le résultat attendu est 3/2.",)),
    "PUBLISHED_FORBIDDEN": dict(generation_origin="HUMAN_AUTHORED", qa_status="HUMAN_APPROVED",
                                publication_status="PUBLISHED"),
}

SEVERITY = {
    "NOTION_UNKNOWN": Severity.BLOCKER, "NOTION_NOT_PROVEN": Severity.BLOCKER,
    "NOTION_NOT_APPROVED": Severity.BLOCKER, "NOTION_WITHOUT_SOURCE": Severity.BLOCKER, "ANSWER_MISSING": Severity.BLOCKER,
    "PUBLISHED_FORBIDDEN": Severity.BLOCKER, "LEVEL_MISMATCH": Severity.ERROR, "SUBJECT_MISMATCH": Severity.ERROR,
    "HINT_REVEALS_ANSWER": Severity.WARNING, "FIXTURE_IN_BANK": Severity.WARNING,
}


@pytest.mark.parametrize("code", sorted(POSITIVE))
def test_code_positif(code):
    issues = validate_exercise(ex(**POSITIVE[code]), REG)
    found = [i for i in issues if i.code == code]
    assert found, (code, issues)
    if code in SEVERITY:
        assert found[0].severity == SEVERITY[code]
    assert all(i.object_id == "EX.FICTIF.calc-001" for i in issues)


@pytest.mark.parametrize("code", sorted(POSITIVE) + ["FIXTURE_IN_BANK"])
def test_code_negatif_sur_exercice_conforme(code):
    assert code not in codes(ex())


def test_fixture_in_bank():
    e = ex()
    reg = make_registry()
    assert "FIXTURE_IN_BANK" not in codes(e, reg)
    reg.exercises[e.exercise_id] = e
    found = [i for i in validate_exercise(e, reg) if i.code == "FIXTURE_IN_BANK"]
    assert found and found[0].severity == Severity.WARNING


def test_notion_publiee_interdite():
    assert "PUBLISHED_FORBIDDEN" in codes(ex(notion_id=N_PUB))


def test_rubric_sans_critere_est_answer_missing():
    e = ex(**GOOD["vrai_faux_argumente"] | {"expected_answer": {"kind": "RUBRIC", "value": "Faux", "rubric": ()}})
    assert "ANSWER_MISSING" in codes(e)


def test_qcm_reponse_non_choice():
    e = ex(exercise_type="QCM", choices=("3/2", "1/2", "2/3"))  # kind MATH_EXPR
    assert "QCM_NO_CORRECT" in codes(e)


def test_qcm_choix_jumeau_equivalent():
    e = ex(**GOOD["qcm"] | {"choices": ("3/4", "0,75", "1/6", "1/8")})
    assert "QCM_MULTIPLE_CORRECT" in codes(e)


def test_qcm_plusieurs_sans_consigne():
    d = GOOD["qcm_plusieurs"] | {"statement": "[FICTIF] Quelle fraction est égale à 1/2 ?"}
    assert "QCM_MULTIPLE_CORRECT" in codes(Exercise(**d))
    assert "QCM_MULTIPLE_CORRECT" not in codes(Exercise(**GOOD["qcm_plusieurs"]))


def test_answer_in_statement_frontiere_de_jeton():
    d = dict(statement="[FICTIF] Arrondir 0,75 au dixième près, par excès.",
             expected_answer={"kind": "MATH_EXPR", "value": "0,8", "required_form": "decimal"},
             solution="0,75 arrondi au dixième par excès donne 0,8.",
             step_by_step_solution=("Le chiffre des centièmes est 5.", "On obtient 0,8."),
             hints=("Regarde le chiffre des centièmes.",), common_errors={"0,7": "arrondi par défaut"})
    assert codes(ex(**d)) == set()
    # « 0,7 » n'est PAS trouvé dans « 0,75 »
    d2 = d | {"expected_answer": {"kind": "MATH_EXPR", "value": "0,7", "required_form": "decimal"},
              "solution": "Au dixième par défaut : 0,7.", "step_by_step_solution": ("On obtient 0,7.",),
              "common_errors": {"0,8": "arrondi par excès"},
              "statement": "[FICTIF] Arrondir 0,75 au dixième près, par défaut."}
    assert "ANSWER_IN_STATEMENT" not in codes(ex(**d2))
    d3 = d2 | {"statement": "[FICTIF] Arrondir 0,75 au dixième près, par défaut (on trouve 0,7)."}
    assert "ANSWER_IN_STATEMENT" in codes(ex(**d3))


def test_unite_manquante_quand_enonce_en_demande_une():
    d = GOOD["grandeur_vitesse"] | {"expected_answer": {"kind": "QUANTITY", "value": 75}}
    assert "UNIT_INCOHERENT" in codes(Exercise(**d))


def test_unite_equivalente_acceptee():
    d = GOOD["grandeur_vitesse"] | {"expected_answer": {"kind": "QUANTITY", "value": "20,8", "unit": "m/s",
                                                        "tolerance_relative": 0.01},
                                    "statement": "[FICTIF] Une voiture parcourt 150 km en 2 h. "
                                                 "Calculer sa vitesse moyenne en m/s (ou en km/h).",
                                    "solution": "v = 75 km/h = 20,8 m/s.",
                                    "step_by_step_solution": ("v = 75 km/h", "v = 75 / 3,6 = 20,8 m/s"),
                                    "common_errors": {}}
    assert "UNIT_INCOHERENT" not in codes(Exercise(**d))


def test_point_A_en_geometrie_nest_pas_une_unite():
    assert "UNIT_INCOHERENT" not in codes(Exercise(**GOOD["pythagore_point_A"]))


def test_temperature_et_ph_impossibles():
    t = ex(notion_id=N_PH, subject="PHYSIQUE_CHIMIE", level="3E",
           statement="[FICTIF] Donner la température finale en K.",
           expected_answer={"kind": "QUANTITY", "value": -12, "unit": "K"},
           solution="T = -12 K", step_by_step_solution=("T = -12 K",), common_errors={})
    assert "PHYSICALLY_IMPOSSIBLE" in codes(t)
    ph = ex(notion_id=N_PH, subject="PHYSIQUE_CHIMIE", level="3E",
            statement="[FICTIF] Quel est le pH de la solution diluée ?",
            expected_answer={"kind": "QUANTITY", "value": 15}, solution="pH = 15",
            step_by_step_solution=("pH = 15",), common_errors={})
    assert "PHYSICALLY_IMPOSSIBLE" in codes(ph)
    ok = ex(notion_id=N_PH, subject="PHYSIQUE_CHIMIE", level="3E",
            statement="[FICTIF] Quel est le pH de la solution diluée ?",
            expected_answer={"kind": "QUANTITY", "value": 3}, solution="pH = 3",
            step_by_step_solution=("pH = 3",), common_errors={})
    assert "PHYSICALLY_IMPOSSIBLE" not in codes(ok)


def test_solution_quantite_incoherente():
    d = GOOD["grandeur_vitesse"] | {"solution": "v = 150 × 2 = 300 km/h.",
                                    "step_by_step_solution": ("v = 300 km/h",)}
    assert "SOLUTION_INCONSISTENT" in codes(Exercise(**d))


def test_solution_texte_incoherente():
    d = GOOD["exact_text"] | {"solution": "Ils rejettent de la vapeur d'eau.",
                              "step_by_step_solution": ("Transpiration.",)}
    assert "SOLUTION_INCONSISTENT" in codes(Exercise(**d))


def test_indice_revele_le_choix_correct():
    d = GOOD["qcm"] | {"choices": ("trois quarts", "deux sixièmes", "un sixième"),
                       "solution": "1/2 + 1/4 = 3/4, soit trois quarts.",
                       "hints": ("Pense à trois quarts.",)}
    assert "HINT_REVEALS_ANSWER" in codes(Exercise(**d))


def test_notation_casse_dans_un_indice():
    assert "MATH_NOTATION_BROKEN" in codes(ex(hints=("Calcule 2 � 9.",)))


def test_codes_documentes_dans_le_module():
    import pedagogy.validators.exercise as mod
    for code in list(POSITIVE) + ["FIXTURE_IN_BANK"]:
        assert code in mod.__doc__
