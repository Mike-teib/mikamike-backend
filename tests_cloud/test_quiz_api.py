"""
Session 6 — API HTTP des quiz (`mika-quiz/1`) : ownership, aucune clé avant soumission,
soumission unique, idempotence, avec_aide monotone, progression sur historique, limitation,
catalogue fail-closed (notion prouvée, question validée). Contenus FICTIFS.
"""

import pytest

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal
from app.api.v1.quiz import contenu
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.quiz_types import QuestionClassement, QuestionReponseCourte, QuestionVraiFaux
from tests_cloud.test_auth import A, B, _h, enforce, monde  # noqa: F401
from tests_cloud.test_import_v2_integrite import _quiz

N1 = "notion:fictif:comparer-fractions"
N2 = "notion:fictif:fractions-decimales"
URL = "/api/v1/quiz"


def _commun(nid=N2, **k):
    n = referentiel_fictif().index().notions[nid]
    return dict(notion_id=n.id, matiere=n.matiere, niveau=n.niveau, explication="Sept dixièmes : 0,7.", **k)


QCM = _quiz()  # quiz:fictif:v2-1, notion N1, bonne réponse index 0 (« 3/7 »)
VF = QuestionVraiFaux(id="quiz:fictif:vf-1", enonce="7/10 est égal à 0,7.", affirmation_vraie=True, **_commun())
RC = QuestionReponseCourte(id="quiz:fictif:rc-1", enonce="Écris sept dixièmes en écriture décimale.",
                           reponse_reference="0,7", type_verification="maths_symbolique", **_commun())
INVALIDE = QuestionVraiFaux(id="quiz:fictif:invalide", enonce="[FICTIF] Q ?", affirmation_vraie=True,
                            **_commun(nid="notion:fictif:sans-preuve"))


@pytest.fixture()
def cat():
    contenu.definir_catalogue(contenu.CatalogueQuiz(referentiel_fictif(), [QCM, VF, RC, INVALIDE],
                                                    autoriser_fictif=True))
    yield
    contenu.definir_catalogue(None)


def _start(c, eleve=A, req="q1", notion=N1, question=None, jeton=None):
    corps = {"student_pseudo_id": eleve, "requete_id": req, "notion_id": notion}
    if question:
        corps["question_id"] = question
    return c.post(f"{URL}/tentatives", json=corps, headers=_h(jeton) if jeton else {})


def _rep(c, t, reponse, req="r1", eleve=A, jeton=None, version=None):
    return c.post(f"{URL}/repondre", headers=_h(jeton) if jeton else {}, json={
        "student_pseudo_id": eleve, "requete_id": req, "tentative_id": t["tentative_id"],
        "version": version or t["version"], "reponse": reponse})


def _aide(c, t, req="a1", eleve=A, jeton=None):
    return c.post(f"{URL}/aide", headers=_h(jeton) if jeton else {}, json={
        "student_pseudo_id": eleve, "requete_id": req, "tentative_id": t["tentative_id"], "version": t["version"]})


CLES = ("index_correct", "affirmation_vraie", "reponse_reference", "ordre_correct", "paires", "correction",
        "explication", "resultat")


def _aucune_cle(obj):
    texte = str(obj)
    return all(k not in texte for k in CLES)


# --------------------------------------------------------------------------- #
# Parcours
# --------------------------------------------------------------------------- #
def test_obtenir_repondre_resultat_progression(client, cat):
    r = _start(client)
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["contract_version"] == "mika-quiz/1" and t["etat"] == "EN_COURS"
    assert t["question"]["type"] == "qcm" and t["question"]["choix"] == ["3/7", "2/7", "1/7"]
    assert _aucune_cle(t)  # aucune bonne réponse ni explication avant soumission
    out = _rep(client, t, 0).json()
    assert out["etat"] == "TERMINEE" and out["resultat"]["verdict"] == "CORRECT"
    assert out["resultat"]["correction"] == {"index_correct": 0} and out["resultat"]["explication"]
    assert out["progression"]["niveau"] == "NON_EVALUEE" and out["etat_maitrise"] == "EN_COURS"
    db = SessionLocal()
    try:
        tent = crud.get_tentatives(db, hmac_eleve(A))
        assert [(x.exercice_id, x.competence, x.est_correct, x.avec_aide) for x in tent] == [
            ("quiz:fictif:v2-1", N1, True, False)]
    finally:
        db.close()


def test_reponse_fausse(client, cat):
    t = _start(client).json()
    out = _rep(client, t, 2).json()
    assert out["resultat"]["verdict"] == "INCORRECT" and out["resultat"]["est_correct"] is False


def test_types_vrai_faux_et_reponse_courte(client, cat):
    t = _start(client, notion=N2, question="quiz:fictif:vf-1").json()
    assert t["question"]["type"] == "vrai_faux" and _aucune_cle(t)
    assert _rep(client, t, True).json()["resultat"]["verdict"] == "CORRECT"
    t = _start(client, req="q2", notion=N2, question="quiz:fictif:rc-1").json()
    assert _rep(client, t, "7/10").json()["resultat"]["verdict"] == "CORRECT"
    t = _start(client, req="q3", notion=N2, question="quiz:fictif:rc-1").json()
    assert _rep(client, t, "0,07").json()["resultat"]["verdict"] == "INCORRECT"


def test_reponse_de_mauvais_type_a_revoir_non_versee(client, cat):
    t = _start(client).json()
    out = _rep(client, t, "3/7").json()  # QCM : index attendu, texte reçu ⇒ indécidable
    assert out["resultat"]["verdict"] == "A_REVOIR" and out["progression"] is None
    db = SessionLocal()
    try:
        assert crud.get_tentatives(db, hmac_eleve(A)) == []
    finally:
        db.close()


def test_soumission_unique(client, cat):
    t = _start(client).json()
    assert _rep(client, t, 0).status_code == 200
    r = _rep(client, t, 1, req="r2")
    assert (r.status_code, r.json()["detail"]) == (409, "tentative_terminee")


def test_idempotence_et_reutilisation_de_cle(client, cat):
    t = _start(client).json()
    a = _rep(client, t, 0).json()
    b = _rep(client, t, 0).json()
    assert b["rejeu"] is True and {k: v for k, v in b.items() if k != "rejeu"} == \
        {k: v for k, v in a.items() if k != "rejeu"}
    assert _rep(client, t, 1).status_code == 409  # même requete_id, autre contenu
    s1, s2 = _start(client, req="q-neuf"), _start(client, req="q-neuf")
    assert (s1.status_code, s2.status_code) == (201, 200) and s1.json()["tentative_id"] == s2.json()["tentative_id"]
    db = SessionLocal()
    try:
        assert len(crud.get_tentatives(db, hmac_eleve(A))) == 1  # rejeu : aucune tentative en double
    finally:
        db.close()


def test_aide_monotone_elimine_un_distracteur_et_compte_aidee(client, cat):
    t = _start(client).json()
    t = _aide(client, t).json()
    assert t["avec_aide"] is True and t["aides"] == 1 and t["question"]["choix_elimine"] in (1, 2)
    assert _aucune_cle(t)
    t = _aide(client, t, req="a2").json()
    assert t["avec_aide"] is True and t["aides"] == 2
    out = _rep(client, t, 0).json()
    assert out["avec_aide"] is True and out["etat_maitrise"] == "ACQUIS_ASSISTE"
    db = SessionLocal()
    try:
        assert crud.get_tentatives(db, hmac_eleve(A))[0].avec_aide is True
    finally:
        db.close()


def test_version_perimee(client, cat):
    t = _start(client).json()
    _aide(client, t)
    r = _rep(client, t, 0)  # version 1 alors que l'aide l'a portée à 2
    assert (r.status_code, r.json()["detail"]) == (409, "version_perimee")


def test_reprise_de_tentative(client, cat):
    t = _start(client).json()
    r = client.get(f"{URL}/tentatives/{t['tentative_id']}", params={"student_id": A})
    assert r.status_code == 200 and r.json()["etat"] == "EN_COURS" and _aucune_cle(r.json())
    _rep(client, t, 0)
    r = client.get(f"{URL}/tentatives/{t['tentative_id']}", params={"student_id": A})
    assert r.json()["resultat"]["verdict"] == "CORRECT"


def test_question_suivante_non_encore_reussie(client, cat):
    t = _start(client, notion=N2).json()
    assert t["question"]["question_id"] == "quiz:fictif:rc-1"  # ordre déterministe
    _rep(client, t, "0,7")
    t2 = _start(client, req="q2", notion=N2).json()
    assert t2["question"]["question_id"] == "quiz:fictif:vf-1"


# --------------------------------------------------------------------------- #
# Fail-closed
# --------------------------------------------------------------------------- #
def test_catalogue_vide_par_defaut_404(client):
    r = _start(client)
    assert (r.status_code, r.json()["detail"]) == (404, "quiz_indisponible")


def test_notion_non_prouvee_jamais_servie(client, cat):
    r = _start(client, notion="notion:fictif:sans-preuve")
    assert r.status_code == 404


def test_question_invalide_jamais_servie(client):
    mauvais = _quiz(id="quiz:fictif:double", choix=("3/7", "6/14", "1/7"))  # deux bonnes réponses
    contenu.definir_catalogue(contenu.CatalogueQuiz(referentiel_fictif(), [mauvais], autoriser_fictif=True))
    try:
        assert _start(client).status_code == 404
    finally:
        contenu.definir_catalogue(None)


def test_contenu_retire_pendant_la_tentative(client, cat):
    t = _start(client).json()
    contenu.definir_catalogue(contenu.CatalogueQuiz(referentiel_fictif(), [], autoriser_fictif=True))
    r = _rep(client, t, 0)
    assert (r.status_code, r.json()["detail"]) == (409, "contenu_retire")


def test_fictif_interdit_en_production(monkeypatch):
    monkeypatch.setenv("MIKA_ENV", "production")
    with pytest.raises(ValueError):
        contenu.CatalogueQuiz(referentiel_fictif(), [QCM], autoriser_fictif=True)


@pytest.mark.parametrize("reponse", ["x" * 501, list(range(11)), {str(i): 0 for i in range(11)},
                                     {"12345": 0}, 1.5, None, {"a": "b"}, [1, "x"]])
def test_reponse_hors_bornes_ou_mal_typee_422(client, cat, reponse):
    t = _start(client).json()
    r = _rep(client, t, reponse)
    assert r.status_code == 422
    assert "x" * 50 not in r.text  # aucune recopie de la saisie


# --------------------------------------------------------------------------- #
# Enforce : ownership / BOLA
# --------------------------------------------------------------------------- #
def test_ownership_en_enforce(monde, cat):
    c, j = monde
    tb = _start(c, eleve=B, jeton=j["B"]).json()
    # A ne peut ni démarrer pour B, ni répondre, ni lire la tentative de B.
    assert _start(c, eleve=B, req="x", jeton=j["A"]).status_code == 403
    assert _rep(c, tb, 0, eleve=B, jeton=j["A"]).status_code == 403
    assert _rep(c, tb, 0, eleve=A, jeton=j["A"]).status_code == 404  # tentative d'un autre élève
    assert c.get(f"{URL}/tentatives/{tb['tentative_id']}", params={"student_id": A},
                 headers=_h(j["A"])).status_code == 404
    assert _start(c, eleve=B).status_code == 401  # sans jeton


# --------------------------------------------------------------------------- #
# Limitation
# --------------------------------------------------------------------------- #
def test_limitation_par_eleve_sans_blocage_croise(client, cat, monkeypatch):
    from app.core import limitation

    monkeypatch.setenv("MIKA_RATE_LIMIT", "on")
    monkeypatch.setattr(limitation.QUIZ_ELEVE, "max_echecs", 3)
    codes = [_start(client, req=f"l{i}").status_code for i in range(5)]
    assert codes[:3] == [201, 201, 201] and codes[3] == 429
    assert _start(client, eleve=B, req="autre").status_code == 201  # autre élève non bloqué


def test_classement_vue_publique(client):
    q = QuestionClassement(id="quiz:fictif:cl-1", enonce="Range du plus petit au plus grand.",
                           elements=("0,7", "0,07", "7"), ordre_correct=(1, 0, 2), valeurs=(0.7, 0.07, 7.0),
                           **_commun())
    contenu.definir_catalogue(contenu.CatalogueQuiz(referentiel_fictif(), [q], autoriser_fictif=True))
    try:
        t = _start(client, notion=N2).json()
        assert t["question"]["elements"] == ["0,7", "0,07", "7"] and _aucune_cle(t)
        assert _rep(client, t, [1, 0, 2]).json()["resultat"]["verdict"] == "CORRECT"
    finally:
        contenu.definir_catalogue(None)
