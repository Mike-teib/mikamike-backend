"""
API du tuteur Mika `mika-tutorat/1` (MIKA_API_CONTRACT.md) — contenu FICTIF uniquement.
"""

import itertools
import json
import re

import pytest

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal
from app.api.v1.tutorat import contenu
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.pedagogie.tuteur import PlanGuidage
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.maths import verifier_reponse

URL = "/api/v1/mika/session"
A, B = "eleve-tut-a", "eleve-tut-b"
PREREQ = "notion:fictif:comparer-fractions"
EXO = "exo:fictif:api-1"
REP = "0,7"


def _exercice(**kw):
    n = referentiel_fictif().index().notions["notion:fictif:fractions-decimales"]
    base = dict(
        id=EXO, notion_id=n.id, matiere=n.matiere, niveau=n.niveau, programme_id=n.programme_id,
        chapitre_id=n.chapitre_id, difficulte=4, objectif_pedagogique="[FICTIF] fraction décimale",
        prerequis=(PREREQ,), enonce="Écris 7/10 sous forme décimale.", reponse_attendue=REP,
        type_verification="maths_symbolique",
        indices=("Lis la fraction à voix haute.", "Combien de dixièmes y a-t-il ?"),
        erreurs_frequentes={"7,10": "le dénominateur a été recopié après la virgule"},
        source_sha256_extrait=n.preuve.sha256_extrait,
    )
    base.update(kw)
    return Exercice(**base)


PLAN = PlanGuidage(
    questions_intermediaires=("Que représente le 10 du dénominateur ?",),
    methodes_alternatives=("place 7 dixièmes dans un tableau de numération.",
                           "partage une unité en 10 parts égales et colorie-en 7."),
    question_comprehension="Et 9/10, comment l'écrirais-tu ?", reponse_comprehension="0,9",
    correction_commentee="7/10 se lit « sept dixièmes » : 0,7.",
    exercice_consolidation_id="exo:fictif:api-2",
)


@pytest.fixture()
def api(client):
    ex = _exercice()
    ex_sans_cle = _exercice(id="exo:fictif:api-sans-cle", enonce="Écris 3/10 sous forme décimale.",
                            reponse_attendue="0,3", erreurs_frequentes={})
    plan_sans_cle = PLAN.model_copy(update={"reponse_comprehension": "",
                                            "correction_commentee": "3/10 = 0,3."})
    contenu.definir_catalogue(contenu.CatalogueTutorat(
        referentiel_fictif(), [ex, ex_sans_cle], {EXO: PLAN, ex_sans_cle.id: plan_sans_cle},
        autoriser_fictif=True))
    db = SessionLocal()
    try:
        for eleve in (A, B):
            crud.upsert_etat(db, hmac_eleve(eleve), PREREQ, "ACQUIS_AUTONOME")
    finally:
        db.close()
    yield client
    contenu.definir_catalogue(None)


def _start(c, eleve=A, req="r-start", exo=EXO):
    return c.post(f"{URL}/start", json={"student_pseudo_id": eleve, "requete_id": req, "exercice_id": exo})


def _op(c, op, t, req, eleve=A, **kw):
    corps = {"student_pseudo_id": eleve, "requete_id": req, "tutorat_id": t["tutorat_id"],
             "version": t["version"], **kw}
    return c.post(f"{URL}/{op}", json=corps)


def _fuite(out) -> bool:
    """La réponse (toutes graphies équivalentes) apparaît-elle hors énoncé et correction ?"""
    textes = [m for m in out["etat"]["messages"] if m != _exercice().enonce and "sept dixièmes" not in m]
    for m in textes:
        for tok in re.findall(r"[0-9][0-9.,/]*", m):
            if verifier_reponse(REP, tok.rstrip(".,")).verdict == Verdict.VALID:
                return True
    return False


# --------------------------------------------------------------------------- #
# Démarrage
# --------------------------------------------------------------------------- #
def test_start_presente_l_exercice_sans_la_reponse(api):
    r = _start(api)
    assert r.status_code == 201
    out = r.json()
    assert out["contract_version"] == "mika-tutorat/1" and out["version"] == 1
    assert out["reponse"]["action"] == "PRESENTER_EXERCICE"
    assert REP not in json.dumps(out) and "0.7" not in json.dumps(out)
    assert "reponse_attendue" not in json.dumps(out)


def test_start_idempotent(api):
    r1, r2 = _start(api), _start(api)
    assert (r1.status_code, r2.status_code) == (201, 200)
    assert r2.json()["rejeu"] is True and r1.json()["tutorat_id"] == r2.json()["tutorat_id"]
    assert _start(api, exo="exo:fictif:api-sans-cle").status_code == 409  # même requete_id, autre corps


def test_start_deux_eleves_meme_requete_id_distincts(api):
    assert _start(api, A).json()["tutorat_id"] != _start(api, B).json()["tutorat_id"]


def test_exercice_inconnu_ou_plan_non_verifiable(api):
    assert _start(api, exo="exo:fictif:inexistant").status_code == 404
    # Plan sans clé de compréhension : non servi (compréhension non vérifiable côté serveur).
    assert _start(api, req="r2", exo="exo:fictif:api-sans-cle").status_code == 404


def test_catalogue_vide_par_defaut(client):
    contenu.definir_catalogue(None)
    assert _start(client).status_code == 404


def test_contenu_fictif_interdit_en_production(monkeypatch):
    monkeypatch.setenv("MIKA_ENV", "production")
    with pytest.raises(ValueError):
        contenu.CatalogueTutorat(referentiel_fictif(), [], {}, autoriser_fictif=True)


def test_notion_non_prouvee_jamais_servie(client):
    # Sans autoriser_fictif, la notion fictive est QUARANTINED : l'exercice n'est pas servi.
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [_exercice()], {EXO: PLAN}))
    try:
        assert _start(client).status_code == 404
    finally:
        contenu.definir_catalogue(None)


def test_prerequis_manquant_remediation_puis_termine(api):
    r = _start(api, eleve="eleve-sans-prerequis")
    out = r.json()
    assert out["reponse"]["action"] == "REMEDIER_PREREQUIS"
    assert out["reponse"]["notion_cible"] == PREREQ and out["etat"]["termine"]
    r2 = _op(api, "answer", out, "r1", eleve="eleve-sans-prerequis", reponse=REP)
    assert r2.status_code == 409 and r2.json()["detail"] == "tutorat_termine"


# --------------------------------------------------------------------------- #
# Réponses, aide graduée, compréhension
# --------------------------------------------------------------------------- #
def test_reussite_autonome_versee_au_learning_engine(api):
    t = _start(api).json()
    out = _op(api, "answer", t, "a1", reponse="0.70").json()
    assert out["reponse"]["action"] == "CONSOLIDATION"
    assert out["etat"]["niveau_estime"] == "ACQUIS_AUTONOME" and not out["etat"]["avec_aide"]
    db = SessionLocal()
    try:
        etats = crud.get_etats(db, hmac_eleve(A))
        tent = crud.get_tentatives(db, hmac_eleve(A))
    finally:
        db.close()
    assert etats["notion:fictif:fractions-decimales"] == "EN_COURS"
    assert len(tent) == 1 and tent[0].est_correct and not tent[0].avec_aide


def test_aide_graduee_dans_l_ordre_sans_solution_immediate(api):
    t = _start(api).json()
    actions = []
    for i in range(8):
        r = _op(api, "help", t, f"h{i}")
        if r.status_code == 409:
            break
        t = r.json()
        actions.append(t["reponse"]["action"])
        if t["reponse"]["action"] != "CORRECTION_COMMENTEE":
            assert not _fuite(t)
    assert actions == ["QUESTION_INTERMEDIAIRE", "DONNER_INDICE", "DONNER_INDICE", "AUTRE_METHODE",
                       "AUTRE_METHODE", "CORRECTION_COMMENTEE"]
    assert t["etat"]["niveau_estime"] == "FRAGILE" and t["etat"]["termine"]
    db = SessionLocal()
    try:
        # Session 5 (moteur sur historique) : un seul tutorat échoué n'est pas un diagnostic
        # (R1) ; l'ancien moteur donnait FRAGILE (conservé sous MIKA_PROGRESSION_MOTEUR=legacy).
        assert crud.get_etats(db, hmac_eleve(A))["notion:fictif:fractions-decimales"] == "INCONNU"
    finally:
        db.close()


def test_comprehension_verifiee_cote_serveur(api):
    t = _start(api).json()
    r = _op(api, "comprehension", t, "c0", reponse="0,9")
    assert r.status_code == 409 and r.json()["detail"] == "comprehension_non_demandee"
    t = _op(api, "help", t, "h1").json()
    t = _op(api, "answer", t, "a1", reponse=REP).json()
    assert t["reponse"]["action"] == "VERIFIER_COMPREHENSION" and t["etat"]["attend_comprehension"]
    assert t["etat"]["niveau_estime"] == "ACQUIS_ASSISTE"  # LE-06
    r = _op(api, "answer", t, "a2", reponse=REP)
    assert r.status_code == 409 and r.json()["detail"] == "comprehension_attendue"
    t = _op(api, "comprehension", t, "c1", reponse="0,09").json()
    assert t["reponse"]["action"] == "AUTRE_METHODE" and t["etat"]["comprehension_verifiee"] is False


def test_comprehension_reussie(api):
    t = _start(api).json()
    t = _op(api, "help", t, "h1").json()
    t = _op(api, "answer", t, "a1", reponse=REP).json()
    t = _op(api, "comprehension", t, "c1", reponse="0,90").json()
    assert t["reponse"]["action"] == "CONSOLIDATION" and t["etat"]["comprehension_verifiee"] is True
    assert t["etat"]["niveau_estime"] == "ACQUIS_ASSISTE"


# --------------------------------------------------------------------------- #
# Idempotence, versions, concurrence
# --------------------------------------------------------------------------- #
def test_rejeu_meme_requete_meme_reponse_sans_transition(api):
    t = _start(api).json()
    r1 = _op(api, "answer", t, "a1", reponse="5").json()
    r2 = _op(api, "answer", t, "a1", reponse="5").json()
    assert r2["rejeu"] and {**r1, "rejeu": True} == r2
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).json()["version"] == 2


def test_requete_id_reutilise_autre_contenu(api):
    t = _start(api).json()
    _op(api, "answer", t, "a1", reponse="5")
    r = _op(api, "answer", t, "a1", reponse="6")
    assert r.status_code == 409


def test_version_perimee(api):
    t = _start(api).json()
    _op(api, "answer", t, "a1", reponse="5")
    r = _op(api, "answer", t, "a2", reponse="6")  # client resté en version 1
    assert r.status_code == 409 and r.json()["detail"] == {"code": "version_perimee", "version_courante": 2}


def test_contenu_retire_en_cours(api):
    t = _start(api).json()
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [], {}, autoriser_fictif=True))
    r = _op(api, "answer", t, "a1", reponse="5")
    assert r.status_code == 409 and r.json()["detail"] == "contenu_retire"


OPS = ("faux", "vide", "aide")


@pytest.mark.parametrize("sequence", list(itertools.product(OPS, repeat=4)))
def test_proprietes_sur_sequences_api(api, sequence):
    t = _start(api).json()
    precedent = t
    for i, op in enumerate(sequence):
        if precedent["etat"]["termine"]:
            break
        if op == "aide":
            r = _op(api, "help", precedent, f"s{i}")
        else:
            r = _op(api, "answer", precedent, f"s{i}", reponse="" if op == "vide" else "5")
        assert r.status_code == 200, r.text
        t = r.json()
        # avec_aide monotone, version +1, difficulté non croissante, pas de fuite.
        assert t["etat"]["avec_aide"] >= precedent["etat"]["avec_aide"]
        assert t["version"] == precedent["version"] + 1
        assert t["reponse"]["difficulte_proposee"] <= precedent.get("reponse", t["reponse"])["difficulte_proposee"]
        if t["reponse"]["action"] != "CORRECTION_COMMENTEE":
            assert not _fuite(t)
        if t["etat"]["avec_aide"]:
            assert t["etat"]["niveau_estime"] != "ACQUIS_AUTONOME"
        precedent = t


# --------------------------------------------------------------------------- #
# Propriété / validation / RGPD
# --------------------------------------------------------------------------- #
def test_tutorat_d_un_autre_eleve_invisible(api):
    t = _start(api, A).json()
    assert _op(api, "answer", t, "x1", eleve=B, reponse=REP).status_code == 404
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": B}).status_code == 404
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).status_code == 200


def test_ownership_en_mode_enforce(api, monkeypatch):
    from app.core.auth import emettre_jeton_eleve
    from paiement_comptes import liens
    from paiement_comptes.database import SessionLocal as BillingSession
    from paiement_comptes.models_billing import Compte

    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    # Préparation (session 3, S3-01) : un jeton élève est désormais adossé à un compte lié.
    bdb = BillingSession()
    ids = {}
    for eleve in (A, B):
        c = Compte(email=f"parent-{eleve}@example.com", mot_de_passe_hash="x", role="parent")
        bdb.add(c)
        bdb.commit()
        liens.lier(bdb, c.id, hmac_eleve(eleve), "parent")
        ids[eleve] = c.id
    bdb.close()
    ja, _ = emettre_jeton_eleve(A, compte_id=ids[A])
    jb, _ = emettre_jeton_eleve(B, compte_id=ids[B])
    h = {"Authorization": f"Bearer {ja}"}
    r = api.post(f"{URL}/start", json={"student_pseudo_id": A, "requete_id": "e1", "exercice_id": EXO}, headers=h)
    assert r.status_code == 201
    t = r.json()
    corps = {"student_pseudo_id": A, "requete_id": "e2", "tutorat_id": t["tutorat_id"], "version": 1, "reponse": REP}
    assert api.post(f"{URL}/answer", json=corps).status_code == 401
    assert api.post(f"{URL}/answer", json=corps, headers={"Authorization": f"Bearer {jb}"}).status_code == 403
    corps_b = {**corps, "student_pseudo_id": B}
    assert api.post(f"{URL}/answer", json=corps_b, headers={"Authorization": f"Bearer {jb}"}).status_code == 404
    assert api.post(f"{URL}/answer", json=corps, headers=h).status_code == 200


@pytest.mark.parametrize("corps", [
    {"student_pseudo_id": A, "requete_id": "r", "exercice_id": EXO, "inattendu": 1},
    {"student_pseudo_id": "a b", "requete_id": "r", "exercice_id": EXO},
    {"student_pseudo_id": A, "requete_id": "r" * 200, "exercice_id": EXO},
    {"student_pseudo_id": A, "requete_id": "r"},
])
def test_validation_start(api, corps):
    assert api.post(f"{URL}/start", json=corps).status_code == 422


def test_validation_transition(api):
    t = _start(api).json()
    assert _op(api, "answer", t, "a1", reponse="x" * 501).status_code == 422
    assert _op(api, "answer", {**t, "version": 0}, "a1", reponse="5").status_code == 422
    assert _op(api, "answer", {**t, "tutorat_id": "../../etc"}, "a1", reponse="5").status_code == 422
    assert api.get(f"{URL}/XYZ", params={"student_id": A}).status_code == 422


def test_rgpd_export_et_effacement_du_tutorat(api):
    t = _start(api).json()
    _op(api, "answer", t, "a1", reponse="5")
    exp = api.get(f"/api/v1/rgpd/export/{A}").json()
    assert len(exp["tutorats_mika"]) == 1 and exp["tutorats_mika"][0]["tutorat_id"] == t["tutorat_id"]
    eff = api.delete(f"/api/v1/rgpd/effacer/{A}").json()
    assert eff["tutorats_supprimes"] == 1 and eff["requetes_tutorat_supprimees"] == 2
    assert api.get(f"{URL}/{t['tutorat_id']}", params={"student_id": A}).status_code == 404


def test_reponse_hostile_n_est_pas_une_erreur(api):
    t = _start(api).json()
    for i, hostile in enumerate(["9^(59*59*59*59)", "__import__('os')", "' OR 1=1 --", "‮0,7"]):
        r = _op(api, "answer", t, f"h{i}", reponse=hostile)
        assert r.status_code == 200
        t = r.json()
        if t["etat"]["termine"]:
            break
    assert t["etat"]["tentatives"] == 0  # illisible ⇒ reformulation, pas une erreur comptée
