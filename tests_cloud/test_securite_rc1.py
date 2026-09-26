"""
Session 5 — audit de sécurité ciblé de la release candidate (enforce).

1. BOLA / IDOR : matrice de TOUTES les routes portant une identité d'élève. Pour chacune, la
   même requête est jouée par le propriétaire (témoin positif : 2xx, sinon le test ne prouve
   rien) puis par trois attaquants — parent d'un autre élève, jeton de séance d'un autre élève,
   compte élève d'un autre élève — qui ne doivent JAMAIS obtenir un 2xx.
2. Inventaire : toute route de l'API absente de la matrice et des exceptions justifiées fait
   échouer ce test (une nouvelle route doit être classée avant d'être livrée).
3. S5-01 : deux premières soumissions simultanées ⇒ plus de 500 (IntegrityError).
Acteurs FICTIFS (fixture `monde` de test_auth.py : pa ↔ A, pb ↔ B, ea = compte élève de A).
"""

import threading

import pytest

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal
from app.api.v1.tutorat import contenu
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.fixtures import referentiel_fictif
from tests_cloud.test_auth import A, B, _h, enforce, monde  # noqa: F401
from tests_cloud.test_mika_api import EXO, PLAN, PREREQ, _exercice

EX = "exo-maths-algebre-1"


def _seance(c, jeton, eleve):
    r = c.post("/api/v1/session/nouvelle", json={"user_id": eleve}, headers=_h(jeton))
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


def _tutorat(c, jeton, eleve, req):
    r = c.post("/api/v1/mika/session/start", json={"student_pseudo_id": eleve, "requete_id": req,
                                                   "exercice_id": EXO}, headers=_h(jeton))
    assert r.status_code in (200, 201), r.text  # 200 = rejeu idempotent du même start
    return r.json()


# Chaque entrée : (méthode, gabarit OpenAPI, fabrique(c, jetons, cible, jeton_de_preparation) -> kwargs)
# `cible` = élève visé ; la préparation (séance, tutorat) est faite par le PROPRIÉTAIRE de la cible.
def _corps(**kw):
    return lambda c, j, cible, prop: {"json": {k: (cible if v == "@" else v) for k, v in kw.items()}}


def _sid(route_corps):
    def f(c, j, cible, prop):
        sid = _seance(c, prop, cible)
        return {"json": {"session_id": sid, "user_id": cible, **route_corps}}
    return f


def _tut(op, **kw):
    def f(c, j, cible, prop):
        t = _tutorat(c, prop, cible, f"bola-{op}-{cible}")
        return {"json": {"student_pseudo_id": cible, "requete_id": f"{op}-x", "tutorat_id": t["tutorat_id"],
                         "version": t["version"], **kw}}
    return f


_N = {"k": 0}


def _tut_comprehension(c, j, cible, prop):
    """Tutorat amené par son propriétaire à l'étape « vérifier la compréhension »."""
    _N["k"] += 1
    t = _tutorat(c, prop, cible, f"bola-comp-{cible}-{_N['k']}")
    for op, req, kw in (("help", "h", {}), ("answer", "a", {"reponse": "0,7"})):
        r = c.post(f"/api/v1/mika/session/{op}", headers=_h(prop), json={
            "student_pseudo_id": cible, "requete_id": f"{req}-{_N['k']}", "tutorat_id": t["tutorat_id"],
            "version": t["version"], **kw})
        assert r.status_code == 200, r.text
        t = r.json()
    assert t["etat"]["attend_comprehension"]
    return {"json": {"student_pseudo_id": cible, "requete_id": f"c-{_N['k']}", "tutorat_id": t["tutorat_id"],
                     "version": t["version"], "reponse": "0,9"}}


def _tut_get(c, j, cible, prop):
    t = _tutorat(c, prop, cible, f"bola-get-{cible}")
    return {"url": f"/api/v1/mika/session/{t['tutorat_id']}", "params": {"student_id": cible}}


def _stream(c, j, cible, prop):
    return {"params": {"session_id": _seance(c, prop, cible)}}


MATRICE = [
    ("POST", "/api/v1/escalier/etape", _corps(student_pseudo_id="@", competence_objectif="equations_1er_degre",
                                              exercice_id=EX, reponse_eleve="3")),
    ("POST", "/api/v1/exercices/soumettre", _corps(student_pseudo_id="@", exercice_id=EX, reponse="3")),
    ("POST", "/api/v1/memory/schedule", _corps(user_id="@", notion_id="equations_1er_degre", mastery_event="SUCCESS")),
    ("POST", "/api/v1/memory/detect-fragile", _corps(user_id="@", scores=[0.2, 0.9])),
    ("POST", "/api/v1/parcours", _corps(user_id="@", level="5e", subject="mathematiques")),
    ("GET", "/api/v1/parcours/prochaine-etape", lambda c, j, cible, prop: {"params": {"student_id": cible}}),
    ("GET", "/api/v1/parcours/{user_id}/{level}/{subject}",
     lambda c, j, cible, prop: {"url": f"/api/v1/parcours/{cible}/5e/mathematiques"}),
    ("GET", "/api/v1/parents/dashboard/{student_pseudo_id}",
     lambda c, j, cible, prop: {"url": f"/api/v1/parents/dashboard/{cible}"}),
    ("GET", "/api/v1/rgpd/export/{student_pseudo_id}", lambda c, j, cible, prop: {"url": f"/api/v1/rgpd/export/{cible}"}),
    ("POST", "/api/v1/session/nouvelle", _corps(user_id="@")),
    ("POST", "/api/v1/session/heartbeat", _sid({})),
    ("POST", "/api/v1/session/save-state", _sid({"state_data": {"ardoise": "x"}})),
    ("POST", "/api/v1/session/reconnect", _sid({})),
    ("GET", "/api/v1/session/stream", _stream),
    ("POST", "/api/v1/mika/session/start", _corps(student_pseudo_id="@", requete_id="bola-start", exercice_id=EXO)),
    ("POST", "/api/v1/mika/session/answer", _tut("answer", reponse="0,7")),
    ("POST", "/api/v1/mika/session/help", _tut("help")),
    ("POST", "/api/v1/mika/session/comprehension", _tut_comprehension),
    ("GET", "/api/v1/mika/session/{tutorat_id}", _tut_get),
    ("POST", "/api/v1/liens/invitations", _corps(student_pseudo_id="@")),
    ("POST", "/api/v1/auth/eleve/jeton", _corps(student_pseudo_id="@")),
    # Destructif : en dernier dans chaque scénario (fixture neuve à chaque paramètre).
    ("DELETE", "/api/v1/rgpd/effacer/{student_pseudo_id}", lambda c, j, cible, prop: {"url": f"/api/v1/rgpd/effacer/{cible}"}),
]

# Routes hors matrice, avec la raison (toute autre route non classée fait échouer l'inventaire).
EXCEPTIONS = {
    "/health": "public, sans donnée",
    "/api/v1/comptes/": "portée = le compte du jeton (aucun identifiant d'autrui accepté) ; test_verification_email, test_auth",
    "/api/v1/paiement/": "portée = le compte du jeton ; webhook signé Stripe",
    "/api/v1/liens/accepter": "le code est la capacité ; usage unique, adresse vérifiée (test_invitations)",
}

# Jetons autorisés à agir pour la CIBLE selon la route (propriétaire légitime).
PROPRIETAIRE = {"/api/v1/auth/eleve/jeton": "pb", "/api/v1/rgpd/effacer/{student_pseudo_id}": "pb",
                "/api/v1/rgpd/export/{student_pseudo_id}": "pb", "/api/v1/parents/dashboard/{student_pseudo_id}": "pb"}


@pytest.fixture()
def mondeb(monde):
    c, jetons = monde
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [_exercice()], {EXO: PLAN},
                                                       autoriser_fictif=True))
    db = SessionLocal()
    for e in (A, B):
        crud.upsert_etat(db, hmac_eleve(e), PREREQ, "ACQUIS_AUTONOME")
    db.close()
    yield c, jetons
    contenu.definir_catalogue(None)


def _jouer(c, methode, gabarit, kwargs, jeton):
    kw = dict(kwargs)
    url = kw.pop("url", gabarit)
    return c.request(methode, url, headers=_h(jeton), **kw)


@pytest.mark.parametrize("methode,gabarit,fabrique", MATRICE, ids=[f"{m} {g}" for m, g, _ in MATRICE])
def test_bola_matrice(mondeb, methode, gabarit, fabrique):
    c, j = mondeb
    proprietaire = j[PROPRIETAIRE.get(gabarit, "B")]
    # 1) Attaquants : jamais un 2xx sur les données de B.
    for attaquant in ("pa", "A", "ea"):
        r = _jouer(c, methode, gabarit, fabrique(c, j, B, j["B"]), j[attaquant])
        assert not (200 <= r.status_code < 300), (attaquant, r.status_code, r.text[:200])
        assert r.status_code in (401, 403, 404), (attaquant, r.status_code, r.text[:200])
        assert B not in r.text or r.status_code == 404 and "detail" in r.json()
    # 2) Témoin positif : la même requête par le propriétaire légitime réussit.
    r = _jouer(c, methode, gabarit, fabrique(c, j, B, j["B"]), proprietaire)
    assert 200 <= r.status_code < 300, (r.status_code, r.text[:300])


def test_inventaire_toutes_les_routes_classees(client):
    from main import app

    couvertes = {g for _, g, _ in MATRICE}
    non_classees = []
    for chemin, ops in app.openapi()["paths"].items():
        if chemin in couvertes or any(chemin == e or (e.endswith("/") and chemin.startswith(e)) for e in EXCEPTIONS):
            continue
        non_classees.append(f"{','.join(ops)} {chemin}")
    assert non_classees == [], "route non classée (ajouter à MATRICE ou EXCEPTIONS avec raison)"


def test_s5_01_premieres_soumissions_simultanees_sans_500(client, monkeypatch):
    orig = crud.upsert_etat
    barriere = threading.Barrier(2)

    def entrelace(db, h, c, e):
        db.get(crud.EtatCompetence, (h, c))
        barriere.wait(timeout=5)  # les deux requêtes ont lu « aucune ligne » avant d'écrire
        return orig(db, h, c, e)

    monkeypatch.setattr(crud, "upsert_etat", entrelace)
    codes = []

    def soumettre():
        r = client.post("/api/v1/exercices/soumettre", json={"exercice_id": EX, "student_pseudo_id": "course-1",
                                                             "reponse": "3"})
        codes.append(r.status_code)

    fils = [threading.Thread(target=soumettre) for _ in range(2)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert codes == [200, 200]
    db = SessionLocal()
    try:
        assert list(crud.get_etats(db, hmac_eleve("course-1"))) == ["equations_1er_degre"]
        assert len(crud.get_tentatives(db, hmac_eleve("course-1"))) == 2
    finally:
        db.close()
