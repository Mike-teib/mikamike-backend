"""
Session 5 — fournisseur de courriel : abstraction, faux fournisseur, SMTP générique.

Aucun courriel réel : le SMTP est testé contre un mini-serveur local (127.0.0.1, port éphémère)
ou une fabrique injectée. Aucune clé réelle : identifiants factices.
"""

import logging
import socket
import socketserver
import threading

import pytest

from app.core import courriel
from app.core.courriel import (
    ConfigCourrielInvalide,
    ConfigSMTP,
    EchecEnvoiCourriel,
    EmailProvider,
    FakeEmailProvider,
    Message,
    SMTPEmailProvider,
    TransportSMTP,
)

MSG = Message(destinataire="parent.test@example.invalid", sujet="MikaMike — vérifiez votre adresse",
              corps="Code : JETON-SECRET-123", type="VERIFICATION_EMAIL")
FAUX_MDP = "mdp-factice-de-test-000"


@pytest.fixture
def env_smtp(monkeypatch):
    for k in ("MIKA_ENV", "MIKA_SMTP_HOST", "MIKA_SMTP_PORT", "MIKA_SMTP_FROM", "MIKA_SMTP_USER",
              "MIKA_SMTP_PASSWORD", "MIKA_SMTP_SECURITE", "MIKA_SMTP_DELAI_S", "MIKA_SMTP_FROM_NAME"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("MIKA_SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("MIKA_SMTP_FROM", "no-reply@example.invalid")
    return monkeypatch


# --------------------------------------------------------------------------- #
# Abstraction
# --------------------------------------------------------------------------- #
def test_noms_anglais_sont_les_memes_objets():
    assert FakeEmailProvider is courriel.TransportFaux
    assert SMTPEmailProvider is TransportSMTP
    assert EmailProvider is courriel.TransportCourriel
    assert isinstance(courriel.boite_de_test(), FakeEmailProvider)


def test_faux_fournisseur_borne_et_filtre():
    f = FakeEmailProvider()
    for i in range(FakeEmailProvider.MAX + 5):
        f.envoyer(Message(f"a{i % 2}@example.invalid", "s", "c", "T"))
    assert len(f.messages) == FakeEmailProvider.MAX
    assert all(m.destinataire == "a0@example.invalid" for m in f.derniers("a0@example.invalid"))


# --------------------------------------------------------------------------- #
# Configuration (fail-closed, variables d'environnement uniquement)
# --------------------------------------------------------------------------- #
def test_config_minimale_hors_production(env_smtp):
    c = ConfigSMTP.depuis_env()
    assert (c.securite, c.port, c.utilisateur) == ("starttls", 587, None)


@pytest.mark.parametrize("var,valeur,motif", [
    ("MIKA_SMTP_HOST", "", "HOST"),
    ("MIKA_SMTP_FROM", "pas-une-adresse", "FROM"),
    ("MIKA_SMTP_FROM", "a@example.invalid\r\nBcc: x@example.invalid", "FROM"),
    ("MIKA_SMTP_SECURITE", "tls13", "SECURITE"),
    ("MIKA_SMTP_PORT", "70000", "PORT"),
    ("MIKA_SMTP_PORT", "abc", "PORT"),
    ("MIKA_SMTP_DELAI_S", "0", "DELAI"),
    ("MIKA_SMTP_DELAI_S", "x", "DELAI"),
    ("MIKA_SMTP_USER", "utilisateur", "USER"),
])
def test_config_invalide_refusee(env_smtp, var, valeur, motif):
    env_smtp.setenv(var, valeur)
    with pytest.raises((ConfigCourrielInvalide, ValueError)) as e:
        ConfigSMTP.depuis_env()
    assert motif in str(e.value).upper()


def test_production_exige_chiffrement_et_identifiants(env_smtp):
    env_smtp.setenv("MIKA_ENV", "production")
    with pytest.raises(ConfigCourrielInvalide, match="identifiants"):
        ConfigSMTP.depuis_env()
    env_smtp.setenv("MIKA_SMTP_USER", "u")
    env_smtp.setenv("MIKA_SMTP_PASSWORD", FAUX_MDP)
    assert ConfigSMTP.depuis_env().securite == "starttls"
    env_smtp.setenv("MIKA_SMTP_SECURITE", "aucune")
    with pytest.raises(ConfigCourrielInvalide, match="SMTP non chiffré interdit en production"):
        ConfigSMTP.depuis_env()


def test_identifiants_interdits_sans_chiffrement(env_smtp):
    env_smtp.setenv("MIKA_SMTP_SECURITE", "aucune")
    env_smtp.setenv("MIKA_SMTP_USER", "u")
    env_smtp.setenv("MIKA_SMTP_PASSWORD", FAUX_MDP)
    with pytest.raises(ConfigCourrielInvalide):
        ConfigSMTP.depuis_env()


def test_mot_de_passe_jamais_dans_repr_ni_erreur(env_smtp):
    env_smtp.setenv("MIKA_SMTP_USER", "u")
    env_smtp.setenv("MIKA_SMTP_PASSWORD", FAUX_MDP)
    c = ConfigSMTP.depuis_env()
    assert FAUX_MDP not in repr(c) and FAUX_MDP not in str(c)
    env_smtp.setenv("MIKA_SMTP_PORT", "0")
    with pytest.raises(ConfigCourrielInvalide) as e:
        ConfigSMTP.depuis_env()
    assert FAUX_MDP not in str(e.value)


def test_transport_smtp_selectionnable_et_valide_au_demarrage(env_smtp):
    env_smtp.setenv("MIKA_EMAIL_TRANSPORT", "smtp")
    assert courriel.nom_transport() == "smtp"
    env_smtp.delenv("MIKA_SMTP_HOST")
    with pytest.raises(ConfigCourrielInvalide):
        courriel.nom_transport()


def test_production_refuse_faux_accepte_smtp_configure(env_smtp):
    env_smtp.setenv("MIKA_ENV", "production")
    env_smtp.setenv("MIKA_EMAIL_TRANSPORT", "faux")
    with pytest.raises(ConfigCourrielInvalide):
        courriel.nom_transport()
    env_smtp.setenv("MIKA_EMAIL_TRANSPORT", "smtp")
    env_smtp.setenv("MIKA_SMTP_USER", "u")
    env_smtp.setenv("MIKA_SMTP_PASSWORD", FAUX_MDP)
    assert courriel.nom_transport() == "smtp"


# --------------------------------------------------------------------------- #
# Construction du message
# --------------------------------------------------------------------------- #
def test_message_construit_sans_injection(env_smtp):
    t = TransportSMTP()
    em = t.construire(MSG)
    assert em["To"] == MSG.destinataire and em["Subject"] == MSG.sujet
    assert em["Auto-Submitted"] == "auto-generated" and em["Message-ID"].endswith("@example.invalid>")
    for champ in ("destinataire", "sujet"):
        mauvais = Message(**{**MSG.__dict__, champ: "x@example.invalid\r\nBcc: espion@example.invalid"})
        with pytest.raises(ValueError):
            t.construire(mauvais)


# --------------------------------------------------------------------------- #
# Échange SMTP réel contre un serveur local (aucun réseau externe)
# --------------------------------------------------------------------------- #
class _SMTPLocal(socketserver.StreamRequestHandler):
    recus: list = []

    def _l(self, s):
        self.wfile.write((s + "\r\n").encode())

    def handle(self):
        self._l("220 local")
        data, dans_data, enveloppe = [], False, {}
        for brut in self.rfile:
            ligne = brut.decode("utf-8", "replace").rstrip("\r\n")
            if dans_data:
                if ligne == ".":
                    dans_data = False
                    _SMTPLocal.recus.append({**enveloppe, "data": "\n".join(data)})
                    self._l("250 ok")
                else:
                    data.append(ligne)
                continue
            cmd = ligne.upper()
            if cmd.startswith("EHLO"):
                self._l("250 local")
            elif cmd.startswith("MAIL FROM"):
                enveloppe["from"] = ligne
                self._l("250 ok")
            elif cmd.startswith("RCPT TO"):
                enveloppe["to"] = ligne
                self._l("250 ok")
            elif cmd == "DATA":
                dans_data = True
                self._l("354 go")
            elif cmd == "QUIT":
                self._l("221 bye")
                return
            else:
                self._l("250 ok")


@pytest.fixture
def serveur_smtp(env_smtp):
    _SMTPLocal.recus = []
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _SMTPLocal)
    srv.daemon_threads = True
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    env_smtp.setenv("MIKA_SMTP_HOST", "127.0.0.1")
    env_smtp.setenv("MIKA_SMTP_PORT", str(srv.server_address[1]))
    env_smtp.setenv("MIKA_SMTP_SECURITE", "aucune")
    yield _SMTPLocal.recus
    srv.shutdown()
    srv.server_close()


def test_envoi_smtp_reel_local(serveur_smtp, caplog):
    caplog.set_level(logging.INFO, logger="mikamike.courriel")
    TransportSMTP().envoyer(MSG)
    assert len(serveur_smtp) == 1
    recu = serveur_smtp[0]
    assert "parent.test@example.invalid" in recu["to"] and "no-reply@example.invalid" in recu["from"]
    assert "JETON-SECRET-123" in recu["data"]
    journaux = caplog.text
    assert "courriel_envoye" in journaux
    assert "parent.test@example.invalid" not in journaux and "JETON-SECRET-123" not in journaux


def test_echec_reseau_sans_fuite(env_smtp, caplog):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # port fermé : connexion refusée
    env_smtp.setenv("MIKA_SMTP_HOST", "127.0.0.1")
    env_smtp.setenv("MIKA_SMTP_PORT", str(port))
    env_smtp.setenv("MIKA_SMTP_SECURITE", "aucune")
    env_smtp.setenv("MIKA_SMTP_DELAI_S", "2")
    with pytest.raises(EchecEnvoiCourriel) as e:
        TransportSMTP().envoyer(MSG)
    assert MSG.destinataire not in str(e.value) and "JETON" not in str(e.value)
    assert MSG.destinataire not in caplog.text


class _SMTPEspion:
    appels: list = []

    def __init__(self, config):
        _SMTPEspion.appels = [("connexion", config.hote, config.port)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        _SMTPEspion.appels.append(("fermeture",))

    def starttls(self, context):
        assert context.check_hostname and context.verify_mode.name == "CERT_REQUIRED"
        _SMTPEspion.appels.append(("starttls",))

    def login(self, u, p):
        _SMTPEspion.appels.append(("login", u))

    def send_message(self, em):
        _SMTPEspion.appels.append(("envoi", em["To"]))


def test_starttls_verifie_puis_login_puis_envoi(env_smtp):
    env_smtp.setenv("MIKA_SMTP_USER", "u")
    env_smtp.setenv("MIKA_SMTP_PASSWORD", FAUX_MDP)
    TransportSMTP(fabrique_smtp=_SMTPEspion).envoyer(MSG)
    assert [a[0] for a in _SMTPEspion.appels] == ["connexion", "starttls", "login", "envoi", "fermeture"]


# --------------------------------------------------------------------------- #
# Intégration : panne du fournisseur
# --------------------------------------------------------------------------- #
class _EnPanne:
    def envoyer(self, message):
        raise EchecEnvoiCourriel("envoi_impossible:TimeoutError")


def test_panne_fournisseur_inscription_reussit_renvoi_503(client, monkeypatch):
    monkeypatch.setitem(courriel._FABRIQUES, "panne", _EnPanne)
    monkeypatch.setenv("MIKA_EMAIL_TRANSPORT", "panne")
    r = client.post("/api/v1/comptes/inscription", json={
        "email": "panne@example.com", "mot_de_passe": "Motdepasse-solide-42"})
    assert r.status_code == 201, r.text
    jeton = r.json()["token"]
    r = client.post("/api/v1/comptes/verification-email", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 503 and r.json()["detail"] == "courriel_indisponible"
