"""
RGPD mineurs (lot 20) : durées de conservation et purge. Simulation par défaut, bornes
strictes, seules les données au-delà de la durée sont supprimées, historique pédagogique intact.
Données FICTIVES, bases SQLite jetables.
"""

import datetime as dt
import json

import pytest

from app.api.v1.mikamike.store import SessionLocal as MikaSession, TentativeExercice
from app.api.v1.session.session_manager import MikaSessionState
from app.api.v1.tutorat.store import TutoratRequete, TutoratSession
from app.core import retention
from app.db.registre import creer_tables_pour_tests
from paiement_comptes.database import SessionLocal as BillingSession
from paiement_comptes.liens import InvitationLien
from paiement_comptes.models_billing import Compte
from paiement_comptes.verification_email import VerificationEmail

T = dt.datetime(2030, 6, 1, 12, 0)


def _j(n):
    return T - dt.timedelta(days=n)


@pytest.fixture()
def bases():
    creer_tables_pour_tests(reinitialiser=True)
    with MikaSession() as m:
        for i, age in enumerate((5, 40)):
            m.add(MikaSessionState(session_id=f"s{i}", eleve_hmac="h" * 16, last_activity_ts=_j(age), created_at=_j(age)))
            m.add(TutoratSession(id=f"t{i}", eleve_hmac="h" * 16, exercice_id="exo", etat_json="{}",
                                 derniere_action="x", cree_le=_j(age * 5), maj_le=_j(age * 5)))
            m.add(TutoratRequete(tutorat_id=f"t{i}", requete_id="r", eleve_hmac="h" * 16, empreinte="0" * 64,
                                 reponse_json="{}", cree_le=_j(age)))
            m.add(TentativeExercice(eleve_hmac="h" * 16, exercice_id="exo", ts=_j(age * 100)))
        m.commit()
    with BillingSession() as b:
        c = Compte(email="fictif@example.com", mot_de_passe_hash="x")
        b.add(c)
        b.flush()
        b.add(VerificationEmail(compte_id=c.id, jeton_hash="a" * 64, email_cible="fictif@example.com",
                                cree_le=_j(20), expire_le=_j(19)))
        b.add(VerificationEmail(compte_id=c.id, jeton_hash="b" * 64, email_cible="fictif@example.com",
                                cree_le=_j(1), expire_le=T + dt.timedelta(hours=5)))
        for i, (exp, used) in enumerate(((_j(1), None), (_j(1), _j(2)), (T + dt.timedelta(hours=1), None))):
            b.add(InvitationLien(code_hash=str(i) * 64, eleve_hmac="h" * 16, relation="parent", emis_par="op",
                                 cree_le=_j(3), expire_le=exp, utilise_le=used))
        b.commit()
    yield
    creer_tables_pour_tests(reinitialiser=True)


def _compter(modele, session_cls):
    with session_cls() as s:
        return s.query(modele).count()


def test_simulation_ne_supprime_rien(bases):
    with MikaSession() as m:
        r = retention.purger_mika(m, maintenant=T)
    assert r == {"mika_session_states": 1, "mika_tutorat_requetes": 1, "mika_tutorat_sessions": 1}
    assert _compter(MikaSessionState, MikaSession) == 2 and _compter(TutoratSession, MikaSession) == 2


def test_purge_appliquee_selon_les_durees(bases):
    with MikaSession() as m:
        assert retention.purger_mika(m, appliquer=True, maintenant=T)["mika_session_states"] == 1
    with BillingSession() as b:
        r = retention.purger_billing(b, appliquer=True, maintenant=T)
    assert r == {"verifications_email": 1, "invitations_lien": 1}
    with MikaSession() as m:
        assert [s.session_id for s in m.query(MikaSessionState)] == ["s0"]
        assert [s.id for s in m.query(TutoratSession)] == ["t0"]           # 25 j < 180 j conservée
        assert m.query(TentativeExercice).count() == 2                      # historique pédagogique intact
    with BillingSession() as b:
        assert b.query(InvitationLien).count() == 2                         # utilisée + non expirée
        assert b.query(VerificationEmail).count() == 1


def test_surcharge_de_politique(bases, monkeypatch):
    monkeypatch.setenv("MIKA_RETENTION_TUTORAT_SESSIONS_JOURS", "10")
    with MikaSession() as m:
        assert retention.purger_mika(m, maintenant=T)["mika_tutorat_sessions"] == 2


@pytest.mark.parametrize("valeur", ["0", "-5", "9999", "abc", "1e3", " 30j"])
def test_duree_hors_bornes_refusee(monkeypatch, valeur):
    monkeypatch.setenv("MIKA_RETENTION_SESSIONS_JOURS", valeur)
    with pytest.raises(retention.PolitiqueInvalide):
        retention.politique()


def test_outil_simulation_par_defaut(bases, capsys):
    from tools import purge_retention

    assert purge_retention.main([]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["mode"] == "SIMULATION" and set(sortie["mika"]) == {
        "mika_session_states", "mika_tutorat_requetes", "mika_tutorat_sessions"}
    assert _compter(MikaSessionState, MikaSession) == 2
    assert purge_retention.main(["--force"]) == 2


def test_outil_politique_invalide(monkeypatch, capsys):
    from tools import purge_retention

    monkeypatch.setenv("MIKA_RETENTION_SESSIONS_JOURS", "0")
    assert purge_retention.main([]) == 2
