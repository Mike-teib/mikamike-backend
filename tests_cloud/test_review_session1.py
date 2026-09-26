"""
Non-régression des findings de la revue contradictoire de la session 1
(CLOUD_REVIEW_SESSION1.md). Chaque test reproduit le SCÉNARIO du finding et
échouait sur le head fb77fb8.
"""

import datetime as _dt
import json
import time

import jwt
import pytest

from app.api.v1.session.session_manager import MikaSessionState
from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.importers import MAX_LIGNE, ecrire_manifest, importer
from app.curriculum.model import SourceOfficielle
from app.curriculum.pedagogie.tuteur import (
    Action,
    PlanGuidage,
    TransitionInvalide,
    TuteurMika,
    valider_plan,
)
from app.curriculum.provenance import autorisation_generation
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.maths import equivalents, verifier_reponse
from app.core.pseudonymisation import hmac_eleve
from app.core.security_config import get_jwt_secret

N1 = "notion:fictif:comparer-fractions"


# --------------------------------------------------------------------------- #
# R2-01 / R2-02 — verrou de génération
# --------------------------------------------------------------------------- #
def test_r2_01_texte_tronque_declare_exact_refuse():
    ref = referentiel_fictif()
    idx = ref.index()
    tronquee = idx.notions[N1].model_copy(update={"texte": "[FICTIF] Comparer, ranger et encadrer des"})
    auto = autorisation_generation(tronquee, idx, autoriser_fictif=True)
    assert not auto.autorise
    assert "texte_recalcule_text_truncated" in auto.raisons


def test_r2_01_texte_sain_reste_autorise():
    idx = referentiel_fictif().index()
    assert autorisation_generation(idx.notions[N1], idx, autoriser_fictif=True).autorise


def test_r2_02_preuve_d_un_autre_programme_refusee():
    ref = referentiel_fictif()
    n1 = ref.index().notions[N1]
    autre = SourceOfficielle(id="src:autre:x", titre="Autre source", editeur="xx",
                             url="https://example.invalid/autre.pdf", date_publication="2020-01-01",
                             sha256_document="1" * 64, fictive=True)
    n1b = n1.model_copy(update={"preuve": n1.preuve.model_copy(update={"source_id": autre.id, "url": autre.url})})
    ref2 = ref.model_copy(update={"sources": ref.sources + (autre,), "notions": (n1b,)})
    auto = autorisation_generation(n1b, ref2.index(), autoriser_fictif=True)
    assert not auto.autorise and "preuve_hors_source_du_programme" in auto.raisons


# --------------------------------------------------------------------------- #
# R2-03 — SymPy : aucune entrée ne bloque ni ne fait planter le vérificateur
# --------------------------------------------------------------------------- #
HOSTILES = [
    "9^(59*59*59*59)", "9^(59*59*59*59*59)", "10^(59)^(59)", "exp(exp(exp(59)))",
    "(x+y+z+1)^60", "tan(x)^60+sin(x)^60+cos(x)^60", "((x+1)^2)^60", "2^(60*60)",
    "sqrt(sqrt(sqrt(sqrt(x))))", "(" * 60 + "x" + ")" * 60,
]


@pytest.mark.parametrize("hostile", HOSTILES)
def test_r2_03_sympy_entree_hostile_bornee(hostile):
    t = time.perf_counter()
    r = equivalents("1", hostile)
    assert time.perf_counter() - t < 3.0
    assert r.verdict != Verdict.VALID


@pytest.mark.parametrize("hostile", HOSTILES)
def test_r2_03_sympy_hostile_cote_reference(hostile):
    # Une clé de correction hostile ne doit jamais produire VALID ni exception.
    assert verifier_reponse(hostile, "1").verdict != Verdict.VALID


@pytest.mark.parametrize("a,b", [("2^(n+1)", "2*2^n"), ("x^(1/2)", "sqrt(x)"), ("x^2-1", "(x-1)(x+1)"),
                                 ("sin(x)^2+cos(x)^2", "1"), ("x^-2", "1/x^2")])
def test_r2_03_expressions_legitimes_toujours_valides(a, b):
    assert equivalents(a, b).verdict == Verdict.VALID


# --------------------------------------------------------------------------- #
# R2-04 — importeur : contenu hostile ⇒ FAILED, jamais d'exception
# --------------------------------------------------------------------------- #
def _lot(tmp_path, nom, contenu, type_="registre_notions"):
    (tmp_path / nom).write_text(contenu, encoding="utf-8")
    ecrire_manifest(tmp_path, {nom: type_})
    return tmp_path


def test_r2_04_json_profondement_imbrique_failed(tmp_path):
    lot = _lot(tmp_path, "n.jsonl", "[" * 100000 + "]" * 100000 + "\n")
    res = importer(lot)
    assert res.statut == "FAILED"


def test_r2_04_referentiel_imbrique_failed(tmp_path):
    lot = _lot(tmp_path, "r.json", '{"a":' * 50000 + "1" + "}" * 50000, "referentiel")
    assert importer(lot).statut == "FAILED"


def test_r2_04_entree_manifest_non_objet(tmp_path):
    (tmp_path / "IMPORT_MANIFEST.json").write_text(json.dumps({"version": 1, "fichiers": [42]}), "utf-8")
    assert importer(tmp_path).statut == "FAILED"


def test_r2_04_manifest_non_objet(tmp_path):
    (tmp_path / "IMPORT_MANIFEST.json").write_text("[1, 2]", "utf-8")
    assert importer(tmp_path).statut == "FAILED"


def test_r2_04_checkpoint_corrompu_ignore(tmp_path):
    lot = tmp_path / "lot"
    lot.mkdir()
    _lot(lot, "o.bin", "opaque", "opaque")
    cp = tmp_path / "cp.json"
    cp.write_text("{pas du json", "utf-8")
    assert importer(lot, checkpoint=cp).statut == "VALIDATED"


def test_r2_04_ligne_geante_refusee(tmp_path):
    lot = _lot(tmp_path, "n.jsonl", '{"x": "' + "a" * (MAX_LIGNE + 10) + '"}\n')
    res = importer(lot)
    assert res.statut == "FAILED" and "trop_longue" in res.fichiers["n.jsonl"]["raison"]


def test_r2_04_mapping_contradictoire_signale(tmp_path):
    ref = referentiel_fictif()
    (tmp_path / "ref.json").write_text(ref.model_dump_json(), "utf-8")
    lignes = [{"notion_id": N1, "chapitre_id": "chap:fictif:fractions-6e"},
              {"notion_id": N1, "chapitre_id": "chap:fictif:autre"}]
    (tmp_path / "m.jsonl").write_text("\n".join(json.dumps(x) for x in lignes), "utf-8")
    ecrire_manifest(tmp_path, {"ref.json": "referentiel", "m.jsonl": "mapping_notion_chapitre"})
    res = importer(tmp_path)
    assert res.statut == "REJECTED"
    assert any(a.code == "MAPPING_CONTRADICTOIRE" for a in res.anomalies)


def test_r2_04_telephone_fixe_detecte(tmp_path):
    lot = _lot(tmp_path, "n.jsonl", json.dumps({"texte": "appeler le 01 23 45 67 89"}) + "\n")
    res = importer(lot)
    assert res.statut == "FAILED" and "telephone" in res.fichiers["n.jsonl"]["raison"]


# --------------------------------------------------------------------------- #
# R2-05 / R2-06 — séance
# --------------------------------------------------------------------------- #
def _expirer(session_id):
    from app.api.v1.mikamike.store import SessionLocal

    db = SessionLocal()
    try:
        s = db.get(MikaSessionState, session_id)
        s.last_activity_ts = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) - _dt.timedelta(hours=1)
        db.commit()
    finally:
        db.close()


def test_r2_05_tiers_ne_peut_pas_desactiver_seance_expiree(client):
    client.post("/api/v1/session/heartbeat", json={"session_id": "vict-1", "user_id": "victime"})
    _expirer("vict-1")
    r = client.post("/api/v1/session/heartbeat", json={"session_id": "vict-1", "user_id": "attaquant"})
    assert r.status_code == 403
    from app.api.v1.mikamike.store import SessionLocal

    db = SessionLocal()
    try:
        assert db.get(MikaSessionState, "vict-1").is_active is True
        assert db.get(MikaSessionState, "vict-1").eleve_hmac == hmac_eleve("victime")
    finally:
        db.close()


def test_r2_06_etat_fusionne_borne(client):
    client.post("/api/v1/session/heartbeat", json={"session_id": "gros-1", "user_id": "u1"})
    codes = [client.post("/api/v1/session/save-state", json={
        "session_id": "gros-1", "user_id": "u1", "state_data": {f"k{i}": "x" * 900_000}}).status_code
        for i in range(4)]
    assert codes[:2] == [200, 200] and 413 in codes


# --------------------------------------------------------------------------- #
# R2-08 / R2-09 — tuteur
# --------------------------------------------------------------------------- #
def _exercice(**kw):
    n = referentiel_fictif().index().notions["notion:fictif:fractions-decimales"]
    base = dict(
        id="exo:fictif:revue-1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
        programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=3,
        objectif_pedagogique="[FICTIF] objectif", prerequis=(N1,),
        enonce="Écris 7/10 sous forme décimale.", reponse_attendue="0,7",
        type_verification="maths_symbolique", indices=("Lis la fraction à voix haute.",),
        erreurs_frequentes={"7,10": "le dénominateur a été recopié"},
        source_sha256_extrait=n.preuve.sha256_extrait,
    )
    base.update(kw)
    return Exercice(**base)


PLAN = PlanGuidage(questions_intermediaires=("Que représente le 10 ?",),
                   question_comprehension="Et 9/10 ?", reponse_comprehension="0,9",
                   correction_commentee="7/10 = 0,7.")


def test_r2_08_comprehension_sans_resolution_refusee():
    t = TuteurMika(_exercice(), PLAN)
    etat, _ = t.demarrer({N1: "MAITRISE"})
    with pytest.raises(TransitionInvalide):
        t.repondre_comprehension(etat, True)


def test_r2_08_comprehension_verifiee_cote_serveur():
    t = TuteurMika(_exercice(), PLAN)
    etat, _ = t.demarrer({N1: "MAITRISE"})
    etat, _ = t.demander_aide(etat)
    etat, r = t.repondre(etat, "0,7")
    assert r.action == Action.VERIFIER_COMPREHENSION
    etat2, r2 = t.repondre_comprehension_texte(etat, "0,09")
    assert etat2.comprehension_verifiee is False
    etat3, r3 = t.repondre_comprehension_texte(etat, "0,9")
    assert etat3.comprehension_verifiee is True and r3.action == Action.CONSOLIDATION
    with pytest.raises(TransitionInvalide):  # pas deux fois
        t.repondre_comprehension_texte(etat3, "0,9")


def test_r2_08_aide_apres_fin_sans_effet():
    t = TuteurMika(_exercice(), PLAN)
    etat, _ = t.demarrer({N1: "MAITRISE"})
    etat, _ = t.repondre(etat, "0,7")
    assert etat.termine
    etat2, r = t.demander_aide(etat)
    assert etat2 == etat and r.action == Action.REVUE_HUMAINE


def test_r2_09_diagnostic_qui_divulgue_la_reponse_refuse():
    ex = _exercice(erreurs_frequentes={"7,10": "la bonne réponse était 0,7"})
    assert "aide_divulgue_la_reponse" in valider_plan(PLAN, ex)


def test_r2_09_question_comprehension_divulgue_sa_cle():
    plan = PLAN.model_copy(update={"question_comprehension": "0,9 est-il égal à 9/10 ?"})
    assert "question_comprehension_divulgue_sa_reponse" in valider_plan(plan, _exercice())


# --------------------------------------------------------------------------- #
# R2-10 / R2-11 — jetons
# --------------------------------------------------------------------------- #
def _jeton(**claims):
    return jwt.encode(claims, get_jwt_secret(), algorithm="HS256")


def _app_garde():
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.api.v1.security.fail_closed import exiger_session_active

    a = FastAPI()

    @a.get("/p")
    def p(s: dict = Depends(exiger_session_active)):
        return s

    return TestClient(a)


def _exp(delta=3600):
    return int(_dt.datetime.now(_dt.timezone.utc).timestamp()) + delta


@pytest.mark.parametrize("claims", [
    {"sub": "eleve-1", "role": "eleve"},                                   # sans exp : valable à vie
    {"sub": "eleve-1", "exp": None},                                        # rôle absent
    {"sub": "7", "role": "parent", "typ": "compte", "email": "a@b.test"},   # jeton de compte
    {"sub": "eleve-1", "role": "admin"},                                    # rôle inconnu
])
def test_r2_10_garde_de_seance_refuse(claims):
    claims = dict(claims)
    if claims.get("exp", 0) is None:
        claims["exp"] = _exp()
    elif "exp" not in claims and claims.get("role") != "eleve":
        claims["exp"] = _exp()
    r = _app_garde().get("/p", headers={"Authorization": f"Bearer {_jeton(**claims)}"})
    assert r.status_code == 401


def test_r2_10_garde_de_seance_accepte_jeton_eleve_valide():
    r = _app_garde().get("/p", headers={"Authorization": f"Bearer {_jeton(sub='eleve-1', role='eleve', exp=_exp())}"})
    assert r.status_code == 200 and r.json()["pseudo_id"] == "eleve-1"


def test_r2_11_compte_refuse_jeton_d_un_autre_type(client):
    ins = client.post("/api/v1/comptes/inscription", json={"email": "parent-r211@example.com", "mot_de_passe": "motdepasse-long-1"})
    cid = ins.json()["compte"]["id"]
    faux = _jeton(sub=str(cid), typ="mika-eleve", role="eleve", exp=_exp())
    assert client.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {faux}"}).status_code == 401
    vrai = ins.json()["token"]
    assert jwt.decode(vrai, options={"verify_signature": False})["typ"] == "compte"
    assert client.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {vrai}"}).status_code == 200


def test_r2_11_compte_refuse_jeton_sans_exp(client):
    ins = client.post("/api/v1/comptes/inscription", json={"email": "parent-r211b@example.com", "mot_de_passe": "motdepasse-long-1"})
    sans_exp = _jeton(sub=str(ins.json()["compte"]["id"]), typ="compte")
    assert client.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {sans_exp}"}).status_code == 401


# --------------------------------------------------------------------------- #
# R2-12 / R2-13 — outils
# --------------------------------------------------------------------------- #
def test_r2_12_mutation_check_exige_une_baseline_verte(monkeypatch):
    from tools import mutation_check

    monkeypatch.setattr(mutation_check, "executer_suite", lambda *a: 1)
    assert mutation_check.main() == 2


def test_r2_12_mutant_non_execute_n_est_pas_tue(monkeypatch, tmp_path):
    from tools import mutation_check

    f = tmp_path / "m.py"
    f.write_text("A = 1\n", "utf-8")
    codes = iter([0, 2])  # baseline verte, puis erreur de collecte
    monkeypatch.setattr(mutation_check, "RACINE", tmp_path)
    monkeypatch.setattr(mutation_check, "MUTANTS", [mutation_check.Mutant("m", "m.py", "A = 1", "A = (")])
    monkeypatch.setattr(mutation_check, "executer_suite", lambda *a: next(codes))
    assert mutation_check.main() == 1
    assert f.read_text("utf-8") == "A = 1\n"  # restauré


def test_r2_13_manifest_hors_depot_refuse(tmp_path):
    from tools.verifier_manifest import verifier

    m = tmp_path / "m.txt"
    m.write_text("0" * 64 + "  ../../../../etc/passwd\n" + "0" * 64 + "  /etc/hostname\n", "utf-8")
    assert set(verifier(m).values()) == {"OUTSIDE"}


def test_r2_13_manifest_code_retour_non_nul(tmp_path):
    from tools.verifier_manifest import main

    m = tmp_path / "m.txt"
    m.write_text("0" * 64 + "  README.md\n", "utf-8")
    assert main([str(m)]) == 1


# --------------------------------------------------------------------------- #
# R2-16 — tableau de bord agrégé en SQL
# --------------------------------------------------------------------------- #
def test_r2_16_dashboard_agrege(client):
    for rep in ("x=3", "4", "3"):
        client.post("/api/v1/exercices/soumettre",
                    json={"exercice_id": "exo-maths-algebre-1", "student_pseudo_id": "dash-1", "reponse": rep})
    stats = client.get("/api/v1/parents/dashboard/dash-1").json()["statistiques_pedagogiques"]
    assert stats["exercices_tentes"] == 3 and stats["exercices_reussis"] == 2
    assert stats["competences"]["equations_1er_degre"]["tentatives"] == 3
    assert stats["taux_reussite"] == round(2 / 3, 3)
