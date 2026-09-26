"""Professeur virtuel Mika (Phase 12) et récurrence (Phase 13)."""

import itertools

import pytest

from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.pedagogie.recurrence import (
    QUESTIONS_GUIDAGE,
    diagnostiquer_redaction,
    prochaine_question,
    verifier_formule_explicite,
    verifier_heredite_fonction_auxiliaire,
)
from app.curriculum.pedagogie.tuteur import Action, PlanGuidage, TuteurMika, valider_plan
from app.curriculum.verifiers.base import Verdict

PREREQ = "notion:fictif:comparer-fractions"


def _exercice(**kw) -> Exercice:
    n = referentiel_fictif().index().notions["notion:fictif:fractions-decimales"]
    base = dict(
        id="exo:fictif:tuteur-1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
        programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=3,
        objectif_pedagogique="[FICTIF] Écrire une fraction décimale en nombre décimal",
        prerequis=(PREREQ,), enonce="Écris 7/10 sous forme décimale.", reponse_attendue="0,7",
        type_verification="maths_symbolique",
        indices=("Lis la fraction à voix haute.", "Combien de dixièmes y a-t-il ?"),
        erreurs_frequentes={"7,10": "le dénominateur a été recopié après la virgule",
                            "0,07": "confusion entre dixièmes et centièmes"},
        source_sha256_extrait=n.preuve.sha256_extrait,
    )
    base.update(kw)
    return Exercice(**base)


PLAN = PlanGuidage(
    questions_intermediaires=("Que représente le 10 du dénominateur ?",),
    methodes_alternatives=("place 7 dixièmes dans un tableau de numération.",
                           "partage une unité en 10 parts égales et colorie-en 7."),
    question_comprehension="Et 9/10, comment l'écrirais-tu ?",
    correction_commentee="7/10 se lit « sept dixièmes » : 0,7 (le 7 au rang des dixièmes).",
    exercice_consolidation_id="exo:fictif:tuteur-2",
)
SOLIDE = {PREREQ: "ACQUIS_AUTONOME"}


@pytest.fixture()
def tuteur():
    return TuteurMika(_exercice(), PLAN)


# --------------------------------------------------------------------------- #
# Démarche
# --------------------------------------------------------------------------- #
def test_prerequis_manquant_bloque(tuteur):
    etat, r = tuteur.demarrer({PREREQ: "FRAGILE"})
    assert r.action == Action.REMEDIER_PREREQUIS
    assert r.notion_cible == PREREQ and etat.prerequis_manquant == PREREQ and etat.termine


def test_reussite_autonome_consolidation(tuteur):
    etat, r = tuteur.demarrer(SOLIDE)
    assert r.action == Action.PRESENTER_EXERCICE and r.donnees["prerequis_acquis"] == [PREREQ]
    etat, r = tuteur.repondre(etat, "0,7")
    assert r.action == Action.CONSOLIDATION
    assert etat.niveau_estime == "ACQUIS_AUTONOME" and not etat.avec_aide


def test_parcours_complet_dans_l_ordre(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    actions = []
    for rep in ["0,07", "5", "5", "5"]:
        etat, r = tuteur.repondre(etat, rep)
        actions.append(r.action)
    assert actions == [Action.IDENTIFIER_BLOCAGE, Action.QUESTION_INTERMEDIAIRE,
                       Action.DONNER_INDICE, Action.DONNER_INDICE]
    etat, r = tuteur.repondre(etat, "5")
    assert r.action == Action.AUTRE_METHODE
    etat, r = tuteur.repondre(etat, "0,7")
    assert r.action == Action.VERIFIER_COMPREHENSION        # réussite avec aide
    assert etat.niveau_estime == "ACQUIS_ASSISTE"            # LE-06
    etat, r = tuteur.repondre_comprehension(etat, True)
    assert r.action == Action.CONSOLIDATION


def test_erreur_frequente_diagnostiquee(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    etat, r = tuteur.repondre(etat, "7,10")
    assert r.action == Action.IDENTIFIER_BLOCAGE
    assert "dénominateur" in r.message and etat.tentatives == 1


def test_aides_epuisees_correction_commentee(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    for _ in range(10):
        etat, r = tuteur.repondre(etat, "42")
        if etat.termine:
            break
    assert r.action == Action.CORRECTION_COMMENTEE
    assert etat.niveau_estime == "FRAGILE" and etat.avec_aide


def test_comprehension_ratee_autre_methode(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    etat, _ = tuteur.demander_aide(etat)
    etat, _ = tuteur.repondre(etat, "0,7")
    etat, r = tuteur.repondre_comprehension(etat, False)
    assert r.action == Action.AUTRE_METHODE


def test_reponse_illisible_reformulation_puis_revue(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    for attendu in [Action.DEMANDER_REFORMULATION, Action.DEMANDER_REFORMULATION, Action.REVUE_HUMAINE]:
        etat, r = tuteur.repondre(etat, "import os")
        assert r.action == attendu
    assert etat.tentatives == 0  # une réponse illisible n'est pas une erreur


def test_reponse_vide_n_est_pas_une_tentative(tuteur):
    etat, _ = tuteur.demarrer(SOLIDE)
    etat, r = tuteur.repondre(etat, "  ")
    assert r.action == Action.LAISSER_REESSAYER and etat.tentatives == 0


# --------------------------------------------------------------------------- #
# Garanties (propriétés sur TOUTES les séquences de réponses)
# --------------------------------------------------------------------------- #
REPONSES = ["0,07", "7,10", "42", "", "demande_aide"]


def _jouer(tuteur, sequence):
    etat, r = tuteur.demarrer(SOLIDE)
    trace = [r]
    for rep in sequence:
        if etat.termine:
            break
        etat, r = tuteur.demander_aide(etat) if rep == "demande_aide" else tuteur.repondre(etat, rep)
        trace.append(r)
    return etat, trace


@pytest.mark.parametrize("sequence", list(itertools.product(REPONSES, repeat=5)))
def test_proprietes_pedagogiques(tuteur, sequence):
    etat, trace = _jouer(tuteur, sequence)
    messages = [r.message for r in trace]
    # 1. jamais deux fois le même message
    assert len(messages) == len(set(messages))
    # 2. jamais la réponse avant la correction commentée
    for r in trace:
        if r.action != Action.CORRECTION_COMMENTEE:
            assert "0,7" not in r.message.replace("0,70", "")
    # 3. monotonie : la difficulté proposée ne croît jamais
    diffs = [r.difficulte_proposee for r in trace]
    assert diffs == sorted(diffs, reverse=True)
    # 4. LE-06 : toute aide reçue interdit « autonome »
    if etat.avec_aide:
        assert etat.niveau_estime != "ACQUIS_AUTONOME"


def test_plus_d_aide_jamais_plus_difficile(tuteur):
    etat, r0 = tuteur.demarrer(SOLIDE)
    precedent = r0.difficulte_proposee
    for _ in range(6):
        etat, r = tuteur.demander_aide(etat)
        assert r.difficulte_proposee <= precedent
        precedent = r.difficulte_proposee
        if etat.termine:
            break


# --------------------------------------------------------------------------- #
# Validation du plan de guidage
# --------------------------------------------------------------------------- #
def test_plan_qui_divulgue_la_reponse_refuse():
    plan = PLAN.model_copy(update={"questions_intermediaires": ("La réponse est 0,7, recopie-la.",)})
    assert "aide_divulgue_la_reponse" in valider_plan(plan, _exercice())
    with pytest.raises(ValueError):
        TuteurMika(_exercice(), plan)


def test_plan_repetitif_refuse():
    plan = PLAN.model_copy(update={"methodes_alternatives": ("même chose", "même chose")})
    assert "aides_repetees" in valider_plan(plan, _exercice())


def test_plan_sans_aide_refuse():
    plan = PlanGuidage(correction_commentee="c")
    assert "aucune_aide_disponible" in valider_plan(plan, _exercice(indices=()))


def test_reponse_contenue_dans_nombre_plus_grand_non_signalee():
    # « 0,7 » ne doit pas être détecté dans « 0,75 » (faux positif de divulgation).
    plan = PLAN.model_copy(update={"questions_intermediaires": ("Compare avec 0,75.",)})
    assert "aide_divulgue_la_reponse" not in valider_plan(plan, _exercice())


# --------------------------------------------------------------------------- #
# Récurrence
# --------------------------------------------------------------------------- #
REDAC_OK = {
    "initialisation": "Pour n = 0 : u0 = 1 et 2^0 = 1, donc P(0) est vraie.",
    "hypothese": "Supposons P(n) vraie pour un certain entier n ≥ 0.",
    "heredite": "Montrons P(n+1). D'après l'hypothèse de récurrence, u(n+1) = 2u(n) = 2×2^n = 2^(n+1).",
    "conclusion": "Par récurrence, P(n) est vraie pour tout entier n ≥ 0.",
}


def test_redaction_correcte():
    assert diagnostiquer_redaction(REDAC_OK, 0) == []
    assert prochaine_question([]) is None


@pytest.mark.parametrize("section,texte,confusion", [
    ("initialisation", "", "INIT_ABSENTE"),
    ("initialisation", "Supposons P(0) vraie.", "INIT_SUPPOSEE"),
    ("initialisation", "Pour n = 1 : P(1) est vraie.", "INIT_MAUVAIS_RANG"),
    ("hypothese", "Supposons P(n) vraie pour tout n.", "HYP_POUR_TOUT_N"),
    ("hypothese", "Supposons P(n+1) vraie.", "HYP_SUR_P_N_PLUS_1"),
    ("heredite", "Montrons P(n). On calcule u(n).", "HER_OBJECTIF_P_N"),
    ("heredite", "Montrons P(n+1). On sait que P(n+1) est vraie donc c'est fini.", "HER_UTILISE_P_N_PLUS_1"),
    ("heredite", "Montrons P(n+1). u(n+1) = 2u(n) = 2^(n+1).", "HER_SANS_HYPOTHESE"),
    ("conclusion", "", "CONCL_ABSENTE"),
    ("conclusion", "Donc P(n+1) est vraie.", "CONCL_P_N_PLUS_1_SEULEMENT"),
    ("conclusion", "Donc la propriété est vraie.", "CONCL_SANS_RANG"),
])
def test_confusions_detectees(section, texte, confusion):
    redac = dict(REDAC_OK, **{section: texte})
    conf = diagnostiquer_redaction(redac, 0)
    assert confusion in conf
    q = QUESTIONS_GUIDAGE[confusion]
    assert q.endswith("?") and "2^(n+1)" not in q  # une question, pas la réponse


def test_ecritures_variantes_de_p_n_plus_1():
    redac = dict(REDAC_OK, hypothese="Supposons P_{n+1} vraie.")
    assert "HYP_SUR_P_N_PLUS_1" in diagnostiquer_redaction(redac, 0)
    redac = dict(REDAC_OK, heredite="Montrons P( n + 1 ) grâce à l'hypothèse de récurrence.")
    assert diagnostiquer_redaction(redac, 0) == []


@pytest.mark.parametrize("f,u0,n0,formule,verdict", [
    ("2x", "1", 0, "2^n", Verdict.VALID),
    ("2x", "1", 0, "2n+1", Verdict.INVALID),
    ("x+3", "2", 0, "3n+2", Verdict.VALID),
    ("x+3", "2", 1, "3n+2", Verdict.INVALID),
    ("x+3", "2", 0, "3n+2+y", Verdict.NEEDS_HUMAN_REVIEW),
])
def test_formule_explicite(f, u0, n0, formule, verdict):
    assert verifier_formule_explicite(f, u0, n0, formule).verdict == verdict


@pytest.mark.parametrize("f,a,b,verdict", [
    ("sqrt(x+2)", "0", "2", Verdict.VALID),
    ("x/2+1", "0", "2", Verdict.VALID),
    ("-x+1", "0", "1", Verdict.INVALID),   # non croissante
    ("2x", "0", "2", Verdict.INVALID),     # f(b) > b
    ("x/2+1", "2", "0", Verdict.INVALID),  # intervalle invalide
])
def test_heredite_fonction_auxiliaire(f, a, b, verdict):
    assert verifier_heredite_fonction_auxiliaire(f, a, b).verdict == verdict
