"""Exercices (Phase 9) et quiz (Phase 10) : verrous de création, doublons, quiz ambigus."""

import pytest

from app.curriculum.exercices import Exercice, RefusCreation, creer_exercice, valider_exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.model import Matiere, Niveau
from app.curriculum.quiz import QuestionQuiz, valider_question


@pytest.fixture()
def ref():
    return referentiel_fictif()


@pytest.fixture()
def idx(ref):
    return ref.index()


def _ex(idx, **surcharges) -> Exercice:
    n = idx.notions["notion:fictif:fractions-decimales"]
    base = dict(
        id="exo:fictif:fractions-decimales-1",
        notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
        programme_id=n.programme_id, chapitre_id=n.chapitre_id,
        difficulte=2,
        objectif_pedagogique="[FICTIF] Passer d'une écriture fractionnaire décimale à un nombre décimal",
        prerequis=n.prerequis,
        enonce="Écris sous forme décimale la fraction 7/10.",
        reponse_attendue="0,7",
        type_verification="maths_symbolique",
        parametres_verification={"forme_requise": "decimal"},
        indices=("Que signifie « dixième » ?", "7/10 = 7 dixièmes", "Le chiffre des dixièmes est 7"),
        erreurs_frequentes={"7,10": "confusion numérateur/dénominateur", "0,07": "centièmes au lieu de dixièmes"},
        source_sha256_extrait=n.preuve.sha256_extrait,
    )
    base.update(surcharges)
    return Exercice(**base)


# --------------------------------------------------------------------------- #
# Exercices
# --------------------------------------------------------------------------- #
def test_exercice_valide_cree(idx):
    banque = []
    creer_exercice(_ex(idx), idx, banque, autoriser_fictif=True)
    assert len(banque) == 1


def test_exercice_refuse_hors_mode_test_sur_source_fictive(idx):
    with pytest.raises(RefusCreation):
        creer_exercice(_ex(idx), idx, [])


def test_exercice_refuse_notion_non_prouvee(idx):
    n = idx.notions["notion:fictif:sans-preuve"]
    ex = _ex(idx, notion_id=n.id, prerequis=())
    raisons = valider_exercice(ex, idx, autoriser_fictif=True)
    assert "notion_non_autorisee:preuve_not_evidenced" in raisons
    assert "source_incoherente" in raisons


def test_exercice_refuse_texte_quarantine(ref):
    from app.curriculum.model import StatutTexte
    n = next(x for x in ref.notions if x.id == "notion:fictif:fractions-decimales")
    n2 = n.model_copy(update={"statut_texte": StatutTexte.COLUMN_CONTAMINATION})
    ref2 = ref.model_copy(update={"notions": tuple(n2 if x.id == n.id else x for x in ref.notions)})
    raisons = valider_exercice(_ex(ref2.index()), ref2.index(), autoriser_fictif=True)
    assert "notion_non_autorisee:texte_column_contamination" in raisons


def test_exercice_refuse_chapitre_ambigu(ref):
    chap = ref.chapitres[0].model_copy(update={"ambigu": True})
    ref2 = ref.model_copy(update={"chapitres": (chap,)})
    raisons = valider_exercice(_ex(ref2.index()), ref2.index(), autoriser_fictif=True)
    assert "notion_non_autorisee:chapitre_ambigu" in raisons


@pytest.mark.parametrize("champ,valeur,raison", [
    ("matiere", Matiere.SVT, "matiere_incoherente"),
    ("niveau", Niveau.TERMINALE, "niveau_incoherent"),
    ("programme_id", "prog:autre", "programme_incoherent"),
    ("chapitre_id", "chap:autre", "chapitre_incoherent"),
    ("source_sha256_extrait", "f" * 64, "source_incoherente"),
    ("prerequis", (), "prerequis_de_la_notion_non_declares"),
    ("prerequis", ("notion:fictif:comparer-fractions", "notion:inexistante"), "prerequis_inconnu:notion:inexistante"),
])
def test_exercice_incoherences(idx, champ, valeur, raison):
    assert raison in valider_exercice(_ex(idx, **{champ: valeur}), idx, autoriser_fictif=True)


def test_reponse_attendue_doit_etre_verifiable(idx):
    ex = _ex(idx, reponse_attendue="sept dixièmes")
    assert any(r.startswith("reponse_attendue_non_verifiable") for r in valider_exercice(ex, idx, autoriser_fictif=True))


def test_erreur_frequente_en_fait_correcte_detectee(idx):
    ex = _ex(idx, erreurs_frequentes={"0,70": "faux diagnostic"})
    assert "erreur_frequente_en_fait_correcte" in valider_exercice(ex, idx, autoriser_fictif=True)


def test_fuite_reponse_dans_enonce(idx):
    ex = _ex(idx, enonce="Écris 7/10 sous forme décimale (indice : 0,7).")
    assert "reponse_fuite_dans_enonce" in valider_exercice(ex, idx, autoriser_fictif=True)


def test_doublon_exact_refuse(idx):
    banque = [_ex(idx)]
    ex2 = _ex(idx, id="exo:fictif:copie", enonce="Écris  sous forme décimale la fraction 7/10.")
    with pytest.raises(RefusCreation) as e:
        creer_exercice(ex2, idx, banque, autoriser_fictif=True)
    assert "doublon_exact:exo:fictif:fractions-decimales-1" in e.value.raisons


def test_doublon_equivalent_refuse_mais_variante_acceptee(idx):
    banque = [_ex(idx)]
    equiv = _ex(idx, id="exo:fictif:equiv", reponse_attendue="0,70",
                erreurs_frequentes={"7,10": "confusion"})
    assert "doublon_equivalent:exo:fictif:fractions-decimales-1" in valider_exercice(equiv, idx, banque, autoriser_fictif=True)
    variante = _ex(idx, id="exo:fictif:variante", enonce="Écris sous forme décimale la fraction 3/10.",
                   reponse_attendue="0,3", erreurs_frequentes={"3,10": "confusion"})
    assert valider_exercice(variante, idx, banque, autoriser_fictif=True) == []


def test_id_deja_utilise(idx):
    assert "id_deja_utilise" in valider_exercice(_ex(idx), idx, [_ex(idx)], autoriser_fictif=True)


# --------------------------------------------------------------------------- #
# Quiz
# --------------------------------------------------------------------------- #
def _q(idx, **surcharges) -> QuestionQuiz:
    n = idx.notions["notion:fictif:fractions-decimales"]
    base = dict(
        id="quiz:fictif:q1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
        enonce="Quelle est l'écriture décimale de 3/10 ?",
        choix=("0,3", "3,10", "0,03", "30"),
        index_correct=0,
        reponse_reference="3/10",
        type_verification="maths_symbolique",
        explication="3/10 se lit « trois dixièmes » : le chiffre des dixièmes est 3.",
    )
    base.update(surcharges)
    return QuestionQuiz(**base)


def test_quiz_valide(idx):
    assert valider_question(_q(idx), idx, autoriser_fictif=True) == []


def test_quiz_double_bonne_reponse(idx):
    q = _q(idx, choix=("0,3", "3/10", "0,03", "30"))
    assert "DOUBLE_BONNE_REPONSE" in valider_question(q, idx, autoriser_fictif=True)


def test_quiz_choix_dupliques_et_ambigus(idx):
    q = _q(idx, choix=("0,3", "0,03", "0,03 ", "Toutes les réponses"))
    r = valider_question(q, idx, autoriser_fictif=True)
    assert "CHOIX_DUPLIQUES" in r and "CHOIX_AMBIGU" in r


def test_quiz_fuite_et_non_explicable(idx):
    q = _q(idx, enonce="0,3 est-elle l'écriture décimale de 3/10 ?", explication="")
    r = valider_question(q, idx, autoriser_fictif=True)
    assert "FUITE_REPONSE" in r and "NON_EXPLICABLE" in r


def test_quiz_fuite_par_longueur(idx):
    q = _q(idx, type_verification="texte_exact",
           choix=("Le chiffre des dixièmes vaut trois donc 0,3", "3,10", "0,03", "30"),
           reponse_reference="Le chiffre des dixièmes vaut trois donc 0,3")
    assert "FUITE_LONGUEUR" in valider_question(q, idx, autoriser_fictif=True)


def test_quiz_distracteur_non_plausible(idx):
    q = _q(idx, choix=("0,3", "banane", "0,03", "30"))
    assert "DISTRACTEUR_NON_PLAUSIBLE" in valider_question(q, idx, autoriser_fictif=True)


def test_quiz_niveau_incoherent_et_notion_non_prouvee(idx):
    r = valider_question(_q(idx, niveau=Niveau.TERMINALE), idx, autoriser_fictif=True)
    assert "NIVEAU_INCOHERENT" in r
    r2 = valider_question(_q(idx, notion_id="notion:fictif:sans-preuve"), idx, autoriser_fictif=True)
    assert "NOTION_NON_AUTORISEE:preuve_not_evidenced" in r2


def test_quiz_index_hors_bornes(idx):
    assert "INDEX_CORRECT_HORS_BORNES" in valider_question(_q(idx, index_correct=7), idx, autoriser_fictif=True)


def test_quiz_bonne_reponse_designee_fausse(idx):
    r = valider_question(_q(idx, index_correct=1), idx, autoriser_fictif=True)  # « 3,10 » ≠ 3/10
    assert "BONNE_REPONSE_INCORRECTE" in r
    assert "DOUBLE_BONNE_REPONSE" in r  # « 0,3 » est alors une bonne réponse non désignée
