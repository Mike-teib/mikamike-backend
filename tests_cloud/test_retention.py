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


# --------------------------------------------------------------------------- #
# Session 5 — rapport scellé, lots, reprise, idempotence, audit chaîné
# --------------------------------------------------------------------------- #
def _rapport(t=T):
    with MikaSession() as m, BillingSession() as b:
        return retention.rapport(m, b, maintenant=t)


def _appliquer(r, t=T + dt.timedelta(hours=1), lot=500):
    with MikaSession() as m, BillingSession() as b:
        return retention.appliquer_rapport(m, b, r, lot=lot, maintenant=t)


def test_s5_toutes_les_durees_configurables(bases, monkeypatch):
    assert set(retention.politique()) == {"SESSIONS", "TUTORAT_REQUETES", "TUTORAT_SESSIONS",
                                          "VERIFICATIONS_EMAIL", "INVITATIONS_EXPIREES"}
    monkeypatch.setenv("MIKA_RETENTION_INVITATIONS_EXPIREES_JOURS", "5")
    with BillingSession() as b:
        assert retention.purger_billing(b, maintenant=T)["invitations_lien"] == 0
    monkeypatch.setenv("MIKA_RETENTION_INVITATIONS_EXPIREES_JOURS", "0")
    with BillingSession() as b:
        assert retention.purger_billing(b, maintenant=T)["invitations_lien"] == 1
    monkeypatch.setenv("MIKA_RETENTION_INVITATIONS_EXPIREES_JOURS", "-1")
    with pytest.raises(retention.PolitiqueInvalide):
        retention.politique()


def test_s5_rapport_scelle_et_sans_donnee_personnelle(bases):
    r = _rapport()
    assert r["format"] == retention.FORMAT_RAPPORT and len(r["empreinte"]) == 64
    assert r["mika"]["mika_session_states"] == 1 and r["billing"]["invitations_lien"] == 1
    texte = json.dumps(r)
    assert "fictif@example.com" not in texte and "h" * 16 not in texte


@pytest.mark.parametrize("alteration,motif", [
    (lambda r: r["mika"].__setitem__("mika_session_states", 99), "empreinte"),
    (lambda r: r.__setitem__("format", "autre"), "format"),
])
def test_s5_rapport_altere_refuse(bases, alteration, motif):
    r = _rapport()
    alteration(r)
    with pytest.raises(retention.RapportInvalide, match=motif):
        _appliquer(r)


def test_s5_rapport_perime_ou_futur_refuse(bases):
    r = _rapport()
    with pytest.raises(retention.RapportInvalide, match="perime"):
        _appliquer(r, t=T + dt.timedelta(hours=25))
    with pytest.raises(retention.RapportInvalide, match="perime"):
        _appliquer(r, t=T - dt.timedelta(hours=1))


def test_s5_politique_modifiee_depuis_le_rapport_refusee(bases, monkeypatch):
    r = _rapport()
    monkeypatch.setenv("MIKA_RETENTION_SESSIONS_JOURS", "1")
    with pytest.raises(retention.RapportInvalide, match="politique_modifiee"):
        _appliquer(r)


def test_s5_application_a_la_date_de_reference(bases):
    r = _rapport()
    with MikaSession() as m:  # devient éligible APRÈS la référence : conservée
        m.add(MikaSessionState(session_id="s-limite", eleve_hmac="h" * 16,
                               last_activity_ts=_j(30) + dt.timedelta(minutes=10), created_at=_j(31)))
        m.commit()
    res = _appliquer(r, t=T + dt.timedelta(hours=2))
    assert res["supprimes"]["mika"]["mika_session_states"] == 1
    with MikaSession() as m:
        assert {s.session_id for s in m.query(MikaSessionState)} == {"s0", "s-limite"}


def test_s5_perimetre_elargi_refuse(bases):
    r = _rapport()
    with MikaSession() as m:  # import de données anciennes après le rapport
        m.add(MikaSessionState(session_id="s-vieux", eleve_hmac="h" * 16, last_activity_ts=_j(400), created_at=_j(400)))
        m.commit()
    with pytest.raises(retention.RapportInvalide, match="perimetre_elargi:mika_session_states"):
        _appliquer(r)
    assert _compter(MikaSessionState, MikaSession) == 3  # rien supprimé


def test_s5_lots_metriques_et_idempotence(bases):
    with MikaSession() as m:
        for i in range(7):
            m.add(MikaSessionState(session_id=f"v{i}", eleve_hmac="h" * 16, last_activity_ts=_j(90), created_at=_j(90)))
        m.commit()
    res = _appliquer(_rapport(), lot=3)
    met = res["metriques"]["mika_session_states"]
    assert met["lignes"] == 8 and met["lots"] == 3 and met["duree_ms"] >= 0
    assert res["metriques"]["mika_tutorat_requetes"]["lignes"] == 1  # clé primaire composite
    res2 = _appliquer(_rapport(T + dt.timedelta(minutes=5)), t=T + dt.timedelta(hours=1))
    assert all(n == 0 for base in res2["supprimes"].values() for n in base.values())


def test_s5_reprise_apres_interruption(bases, monkeypatch):
    with MikaSession() as m:
        for i in range(6):
            m.add(MikaSessionState(session_id=f"v{i}", eleve_hmac="h" * 16, last_activity_ts=_j(90), created_at=_j(90)))
        m.commit()
    r = _rapport()
    vrai_delete, appels = retention.delete, {"n": 0}

    def delete_fragile(modele):
        appels["n"] += 1
        if appels["n"] == 3:
            raise RuntimeError("coupure simulée")
        return vrai_delete(modele)

    monkeypatch.setattr(retention, "delete", delete_fragile)
    with pytest.raises(RuntimeError):
        _appliquer(r, lot=2)
    assert 0 < _compter(MikaSessionState, MikaSession) < 8  # lots validés conservés, base cohérente
    monkeypatch.setattr(retention, "delete", vrai_delete)
    _appliquer(r, lot=2)  # même rapport : reprise jusqu'au bout
    with MikaSession() as m:
        assert [s.session_id for s in m.query(MikaSessionState)] == ["s0"]


def test_s5_lot_invalide(bases):
    with pytest.raises(retention.PolitiqueInvalide):
        _appliquer(_rapport(), lot=0)


def test_s5_outil_flux_complet_et_audit(bases, tmp_path, monkeypatch, capsys):
    from tools import purge_retention as pr

    audit = tmp_path / "audit.jsonl"
    monkeypatch.setenv("MIKA_RETENTION_AUDIT", str(audit))
    fichier = tmp_path / "rapport.json"
    monkeypatch.setenv("MIKA_OPERATEUR", "op-test")
    assert pr.main(["--appliquer"]) == 2                        # jamais sans rapport
    assert pr.main(["--appliquer", "--lot", "3"]) == 2
    assert pr.main(["--sortie", str(fichier)]) == 0
    capsys.readouterr()
    monkeypatch.delenv("MIKA_OPERATEUR", raising=False)
    assert pr.main(["--appliquer", "--rapport", str(fichier)]) == 2  # opérateur requis
    monkeypatch.setenv("MIKA_OPERATEUR", "op-test")
    assert pr.main(["--appliquer", "--rapport", str(fichier), "--lot", "2"]) == 0
    sortie = json.loads(capsys.readouterr().out)
    assert sortie["mode"] == "APPLIQUE" and sortie["supprimes"]["mika"]["mika_session_states"] >= 0
    entrees = [json.loads(x) for x in audit.read_text().splitlines()]
    assert [e["etape"] for e in entrees] == ["DEBUT", "FIN"]
    assert entrees[0]["precedent"] == "0" * 64 and entrees[1]["operateur"] == "op-test"
    assert "fictif@example.com" not in audit.read_text() and "h" * 16 not in audit.read_text()
    assert pr.verifier_audit(audit) == []
    assert pr.main(["--verifier-audit"]) == 0


def test_s5_audit_detecte_alteration_et_interruption(tmp_path):
    from tools import purge_retention as pr

    p = tmp_path / "a.jsonl"
    pr.ecrire_audit({"execution": "x1", "etape": "DEBUT"}, p)
    pr.ecrire_audit({"execution": "x1", "etape": "FIN"}, p)
    pr.ecrire_audit({"execution": "x2", "etape": "DEBUT"}, p)
    assert pr.verifier_audit(p) == ["ligne 3 : exécution x2 sans FIN (interrompue : relancer pour reprendre)"]
    lignes = p.read_text().splitlines()
    lignes[1] = lignes[1].replace('"FIN"', '"ECHEC"')
    p.write_text("\n".join(lignes) + "\n")
    assert any("chaîne rompue" in a for a in pr.verifier_audit(p))


def test_s5_outil_rapport_refuse_code_3(bases, tmp_path, monkeypatch):
    from tools import purge_retention as pr

    monkeypatch.setenv("MIKA_RETENTION_AUDIT", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("MIKA_OPERATEUR", "op-test")
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"format": "x"}))
    assert pr.main(["--appliquer", "--rapport", str(f)]) == 3
    assert pr.main(["--lot", "5"]) == 2
