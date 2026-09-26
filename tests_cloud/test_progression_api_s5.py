"""
Session 5 — le moteur de progression sur historique branché sur l'API historique.

Contraintes vérifiées (au niveau du moteur ET à travers l'API) :
  - pas de diagnostic sur une seule réponse ;
  - avec_aide monotone : déclarer l'aide ne fait jamais monter le niveau ;
  - D14 : compréhension finale ratée ⇒ pas de réussite ;
  - progression bornée d'un cran par réponse ;
  - maîtrise exigeant une répétition dans le temps (≥ 2 jours distincts) ;
  - compatibilité : `etat_maitrise` garde le vocabulaire historique, `progression` s'ajoute ;
    `MIKA_PROGRESSION_MOTEUR=legacy` rétablit l'ancien calcul (retour arrière sans migration).
"""

import datetime as _dt
import itertools

import pytest
from sqlalchemy import event

from app.api.v1.mikamike import moteur
from app.api.v1.mikamike.learning_engine import ETATS_SOLIDES, EtatMaitrise
from app.api.v1.mikamike.store import SessionLocal, TentativeExercice, engine
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.pedagogie.progression import (
    HISTORIQUE_MAX,
    ORDRE,
    Niveau,
    Tentative,
    diagnostiquer,
)

JOUR = 86400.0
EXO, COMP = "exo-maths-algebre-1", "equations_1er_degre"
BONNE, FAUSSE = "3", "x = 999"
ETATS_HISTORIQUES = {e.value for e in EtatMaitrise}


def _rang(n: Niveau) -> int:
    return -1 if n == Niveau.NON_EVALUEE else ORDRE.index(n)


def _histoires(longueurs=(3, 4, 5), jours=(0, 1, 2)):
    opts = [(ok, aide, d) for ok in (True, False) for aide in (True, False) for d in jours]
    for n in longueurs:
        for combo in itertools.product(opts, repeat=n):
            if [c[2] for c in combo] != sorted(c[2] for c in combo):
                continue
            yield [Tentative(c[0], c[1], 1_900_000_000 + c[2] * JOUR + i * 60) for i, c in enumerate(combo)]


# --------------------------------------------------------------------------- #
# Moteur : propriétés exhaustives (petits historiques, 3 jours)
# --------------------------------------------------------------------------- #
def test_r8_declarer_l_aide_ne_fait_jamais_monter_le_niveau():
    violations = []
    for h in _histoires():
        base = _rang(diagnostiquer(h).niveau)
        for i, t in enumerate(h):
            if not t.avec_aide:
                h2 = list(h)
                h2[i] = t._replace(avec_aide=True)
                if _rang(diagnostiquer(h2).niveau) > base:
                    violations.append((h, i))
    assert not violations, violations[:2]


def test_r8_echec_aide_reste_un_echec():
    aide_ok = [Tentative(True, True, 1_900_000_000 + i * 60) for i in range(2)]
    echecs = [Tentative(False, False, 1_900_000_200), Tentative(False, False, 1_900_000_300)]
    assert diagnostiquer(aide_ok + echecs).niveau == Niveau.FRAGILE
    un_aide = [echecs[0], echecs[1]._replace(avec_aide=True)]
    assert diagnostiquer(aide_ok + un_aide).niveau == Niveau.FRAGILE


def test_espacement_mesure_sur_l_historique_borne():
    h = [Tentative(True, False, 1_900_000_000)] + [
        Tentative(True, False, 1_900_000_000 + JOUR + i * 60) for i in range(4)]
    assert diagnostiquer(h).niveau == Niveau.MAITRISEE
    meme_jour = [Tentative(True, False, 1_900_000_000 + i * 60) for i in range(8)]
    assert diagnostiquer(meme_jour).niveau == Niveau.EN_COURS


def test_libelle_historique_jamais_plus_favorable_que_le_diagnostic():
    for h in _histoires():
        d = diagnostiquer(h)
        e = moteur.etat_compatible(d, h)
        assert (e == EtatMaitrise.MAITRISE) == (d.niveau == Niveau.MAITRISEE)
        if e in ETATS_SOLIDES:
            assert d.niveau in (Niveau.EN_COURS, Niveau.MAITRISEE)
            assert sum(1 for t in h if t.correcte and not t.avec_aide) >= 3
        if d.niveau == Niveau.NON_EVALUEE:
            assert e in (EtatMaitrise.INCONNU, EtatMaitrise.EN_COURS, EtatMaitrise.ACQUIS_ASSISTE)
        if all(t.avec_aide or not t.correcte for t in h):
            assert e not in ETATS_SOLIDES


def test_libelles_non_evaluee_provisoires():
    t0 = 1_900_000_000
    cas = {
        (): EtatMaitrise.INCONNU,
        ((False, False),): EtatMaitrise.INCONNU,
        ((True, True),): EtatMaitrise.ACQUIS_ASSISTE,
        ((True, False),): EtatMaitrise.EN_COURS,
        ((True, True), (True, False)): EtatMaitrise.EN_COURS,
    }
    for seq, attendu in cas.items():
        h = [Tentative(ok, aide, t0 + i) for i, (ok, aide) in enumerate(seq)]
        assert moteur.etat_compatible(diagnostiquer(h), h) == attendu, seq


def test_non_acquise_libelle_a_revoir():
    h = [Tentative(False, False, 1_900_000_000 + i) for i in range(3)]
    assert moteur.etat_compatible(diagnostiquer(h), h) == EtatMaitrise.A_REVOIR


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def test_moteur_par_defaut_historique(monkeypatch):
    monkeypatch.delenv("MIKA_PROGRESSION_MOTEUR", raising=False)
    assert moteur.moteur_actif() == "historique"


@pytest.mark.parametrize("valeur", ["", "HISTORIQUE", " legacy "])
def test_valeurs_acceptees(monkeypatch, valeur):
    monkeypatch.setenv("MIKA_PROGRESSION_MOTEUR", valeur)
    assert moteur.moteur_actif() in moteur.MOTEURS


@pytest.mark.parametrize("valeur", ["simple", "off", "v2"])
def test_valeur_inconnue_refusee_sans_repli(monkeypatch, valeur):
    monkeypatch.setenv("MIKA_PROGRESSION_MOTEUR", valeur)
    with pytest.raises(moteur.MoteurConfigError):
        moteur.moteur_actif()


def test_demarrage_refuse_si_moteur_invalide(monkeypatch):
    from fastapi.testclient import TestClient

    from main import app

    monkeypatch.setenv("MIKA_PROGRESSION_MOTEUR", "simple")
    with pytest.raises(moteur.MoteurConfigError):
        with TestClient(app):
            pass


# --------------------------------------------------------------------------- #
# API — compatibilité et contraintes
# --------------------------------------------------------------------------- #
def _soumettre(client, eleve, reponse=BONNE, aide=False):
    r = client.post("/api/v1/exercices/soumettre", json={
        "exercice_id": EXO, "student_pseudo_id": eleve, "reponse": reponse, "avec_aide": aide})
    assert r.status_code == 200, r.text
    return r.json()


def _anciennes(eleve, *seq, jours_avant=3):
    """Journalise des tentatives datées de `jours_avant` jours (historique réel simulé)."""
    db = SessionLocal()
    try:
        base = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=jours_avant)
        for i, (ok, aide) in enumerate(seq):
            db.add(TentativeExercice(eleve_hmac=hmac_eleve(eleve), exercice_id=EXO, matiere="maths",
                                     niveau="4e", competence=COMP, est_correct=ok, avec_aide=aide,
                                     ts=base + _dt.timedelta(minutes=i)))
        db.commit()
    finally:
        db.close()


def test_contrat_reponse_compatible(client):
    out = _soumettre(client, "eleve-s5-contrat")
    assert set(out) == {"est_correct", "etat_maitrise", "message", "remediation", "progression"}
    assert out["etat_maitrise"] in ETATS_HISTORIQUES
    assert set(out["progression"]) == {"moteur", "niveau", "prochaine_action", "observations", "raisons"}
    assert out["progression"]["moteur"] == "historique" and out["progression"]["observations"] == 1


def test_pas_de_diagnostic_sur_une_seule_reponse(client):
    out = _soumettre(client, "eleve-s5-une", FAUSSE)
    assert out["progression"]["niveau"] == "NON_EVALUEE"
    assert out["progression"]["prochaine_action"] == "observer_encore"
    assert out["etat_maitrise"] == "INCONNU"
    out = _soumettre(client, "eleve-s5-une-ok", BONNE)
    assert out["progression"]["niveau"] == "NON_EVALUEE" and out["etat_maitrise"] not in \
        {e.value for e in ETATS_SOLIDES}


def test_maitrise_exige_repetition_dans_le_temps(client):
    eleve = "eleve-s5-temps"
    etats = [_soumettre(client, eleve)["etat_maitrise"] for _ in range(6)]
    assert "MAITRISE" not in etats and etats[-1] == "ACQUIS_AUTONOME"
    eleve2 = "eleve-s5-espace"
    _anciennes(eleve2, (True, False), (True, False))
    out = _soumettre(client, eleve2)
    assert out["etat_maitrise"] == "MAITRISE" and out["progression"]["niveau"] == "MAITRISEE"


def test_aide_monotone_via_api_jamais_solide(client):
    eleve = "eleve-s5-aide"
    _anciennes(eleve, *[(True, True)] * 6, jours_avant=5)
    _anciennes(eleve, *[(True, True)] * 6, jours_avant=2)
    for _ in range(4):
        out = _soumettre(client, eleve, aide=True)
        assert out["etat_maitrise"] not in {e.value for e in ETATS_SOLIDES}
        assert out["etat_maitrise"] == "ACQUIS_ASSISTE"


def test_aide_declaree_jamais_plus_favorable_via_api(client):
    for sequence in itertools.product((True, False), repeat=4):
        niveaux = {}
        for aide in (False, True):
            eleve = f"eleve-s5-mono-{''.join('1' if x else '0' for x in sequence)}-{int(aide)}"
            _anciennes(eleve, (True, False), jours_avant=4)
            for ok in sequence:
                out = _soumettre(client, eleve, BONNE if ok else FAUSSE, aide=aide)
            niveaux[aide] = _rang(Niveau(out["progression"]["niveau"]))
        assert niveaux[True] <= niveaux[False], sequence


def test_progression_bornee_a_un_cran_par_reponse_via_api(client):
    eleve = "eleve-s5-cran"
    _anciennes(eleve, *[(True, False)] * 4, jours_avant=6)
    precedent = None
    for ok in (False, False, False, False, True, True, True, False, True):
        n = Niveau(_soumettre(client, eleve, BONNE if ok else FAUSSE)["progression"]["niveau"])
        if precedent is not None and n in ORDRE and precedent in ORDRE:
            assert abs(ORDRE.index(n) - ORDRE.index(precedent)) <= 1, (precedent, n)
        precedent = n


def test_escalier_passe_la_tentative_courante(client):
    """La tentative de /escalier/etape n'est journalisée qu'à l'étape 8 : elle doit tout de
    même compter dans le diagnostic (sinon décalage d'une réponse avec /soumettre)."""
    eleve = "eleve-s5-esc"
    _anciennes(eleve, (True, False), (True, False), jours_avant=3)
    r = client.post("/api/v1/escalier/etape", json={
        "student_pseudo_id": eleve, "competence_objectif": COMP, "exercice_id": EXO, "reponse_eleve": BONNE})
    assert r.status_code == 200
    assert r.json()["etat_maitrise"] == "MAITRISE"
    assert r.json()["progression"]["observations"] == 3


def test_lecture_de_l_historique_bornee_en_sql(client):
    eleve = "eleve-s5-borne"
    _anciennes(eleve, *[(False, False)] * (HISTORIQUE_MAX + 20))
    requetes = []

    def capter(conn, cursor, statement, *a):
        if "mika_tentatives" in statement and "SELECT" in statement.upper():
            requetes.append(statement)

    event.listen(engine, "before_cursor_execute", capter)
    try:
        db = SessionLocal()
        try:
            h = moteur.historique(db, hmac_eleve(eleve), COMP)
        finally:
            db.close()
    finally:
        event.remove(engine, "before_cursor_execute", capter)
    assert len(h) == HISTORIQUE_MAX
    assert requetes and all("LIMIT" in q.upper() for q in requetes)


def test_historique_ordonne_du_plus_ancien_au_plus_recent(client):
    eleve = "eleve-s5-ordre"
    _anciennes(eleve, (False, False), jours_avant=3)
    _anciennes(eleve, (True, False), jours_avant=1)
    db = SessionLocal()
    try:
        h = moteur.historique(db, hmac_eleve(eleve), COMP)
    finally:
        db.close()
    assert [t.correcte for t in h] == [False, True]
    assert h[0].horodatage < h[1].horodatage


def test_legacy_retour_arriere_sans_migration(client, monkeypatch):
    monkeypatch.setenv("MIKA_PROGRESSION_MOTEUR", "legacy")
    etats = [_soumettre(client, "eleve-s5-legacy") for _ in range(3)]
    assert [e["etat_maitrise"] for e in etats] == ["EN_COURS", "ACQUIS_AUTONOME", "MAITRISE"]
    assert all(e["progression"] is None for e in etats)
    # Rebascule : le moteur sur historique relit la même table, sans conversion.
    monkeypatch.setenv("MIKA_PROGRESSION_MOTEUR", "historique")
    out = _soumettre(client, "eleve-s5-legacy")
    assert out["progression"]["observations"] == 4 and out["etat_maitrise"] == "ACQUIS_AUTONOME"


def test_prochaine_etape_ne_se_fonde_pas_sur_une_seule_reponse(client):
    eleve = "eleve-s5-pe"
    _soumettre(client, eleve)  # une bonne réponse : pas « consolidé »
    r = client.get("/api/v1/parcours/prochaine-etape", params={"student_id": eleve})
    assert r.status_code == 200 and r.json()["competence"] == COMP


def test_dashboard_parent_schema_ferme_inchange(client):
    eleve = "eleve-s5-dash"
    _soumettre(client, eleve)
    r = client.get(f"/api/v1/parents/dashboard/{eleve}")
    assert r.status_code == 200
    stats = r.json()["statistiques_pedagogiques"]
    assert set(stats) == {"exercices_tentes", "exercices_reussis", "taux_reussite", "competences", "niveau_actuel"}
    assert stats["competences"][COMP]["etat"] in ETATS_HISTORIQUES
