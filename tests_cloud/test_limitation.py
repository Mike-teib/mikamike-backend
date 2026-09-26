"""
R7 — Limitation des tentatives (app/core/limitation.py) : fenêtre, compteur, backoff, reset,
mémoire bornée, et surtout ABSENCE de DoS contre un autre utilisateur.

Horloge simulée (aucune attente réelle). Adresses IP simulées via X-Forwarded-For avec
MIKA_PROXY_HOPS=1 (un proxy de confiance). Comptes FICTIFS.
"""

import pytest

from app.core import limitation as L
from app.core.pseudonymisation import hmac_eleve
from paiement_comptes import crud_billing, liens
from paiement_comptes.database import SessionLocal as BillingSession
from paiement_comptes.router_comptes import creer_token

MDP = "motdepasse-de-test-1"


class Horloge:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture()
def horloge(monkeypatch):
    h = Horloge()
    for lim in L.TOUS:
        monkeypatch.setattr(lim, "horloge", h)
    return h


def _lim(**kw):
    h = Horloge()
    p = dict(max_echecs=3, fenetre_s=60, backoff_base_s=10, backoff_max_s=80, horloge=h)
    p.update(kw)
    return L.Limiteur("t", **p), h


# --------------------------------------------------------------------------- #
# Unitaire
# --------------------------------------------------------------------------- #
def test_seuil_fenetre_et_compteur():
    lim, h = _lim()
    for _ in range(2):
        lim.echec("k")
    assert lim.attente("k") == 0  # sous le seuil
    lim.echec("k")
    assert lim.attente("k") == 10  # seuil atteint : base


def test_backoff_exponentiel_plafonne():
    lim, h = _lim()
    attentes = []
    for _ in range(3):
        lim.echec("k")
    for _ in range(5):
        attentes.append(lim.attente("k"))
        h.t += attentes[-1]  # attend la fin du blocage puis échoue encore
        lim.echec("k")
        h.t += 0.0
    assert attentes == [10, 20, 40, 80, 80]


def test_fenetre_glissante_oublie_les_vieux_echecs():
    lim, h = _lim()
    lim.echec("k")
    lim.echec("k")
    h.t += 61
    lim.echec("k")
    assert lim.attente("k") == 0  # les 2 premiers sont sortis de la fenêtre
    assert len(lim) == 1


def test_reset_sur_succes():
    lim, h = _lim()
    for _ in range(3):
        lim.echec("k")
    lim.succes("k")
    assert lim.attente("k") == 0
    lim.echec("k")
    assert lim.attente("k") == 0


def test_cles_isolees():
    lim, _ = _lim()
    for _ in range(3):
        lim.echec("a")
    assert lim.attente("a") > 0 and lim.attente("b") == 0


def test_memoire_bornee_cles_et_historique():
    lim, h = _lim(max_cles=100)
    for i in range(10_000):
        lim.echec(f"cle-{i}")
    assert len(lim) == 100
    for _ in range(10_000):
        lim.echec("chaude")
    etat = next(iter(v for v in lim._etats.values() if len(v.echecs) > 1))
    assert len(etat.echecs) <= lim._max_hist


def test_aucune_pii_en_memoire():
    lim, _ = _lim()
    lim.echec("1.2.3.4|victime@example.com")
    assert all("@" not in k and len(k) == 32 for k in lim._etats)


@pytest.mark.parametrize("kw", [dict(max_echecs=0), dict(fenetre_s=0), dict(backoff_base_s=0),
                                dict(backoff_base_s=10, backoff_max_s=5)])
def test_parametres_invalides(kw):
    with pytest.raises(ValueError):
        _lim(**kw)


def test_mode_off_interdit_en_production(monkeypatch):
    monkeypatch.setenv("MIKA_RATE_LIMIT", "off")
    monkeypatch.setenv("MIKA_ENV", "production")
    with pytest.raises(L.ConfigLimitationInvalide):
        L.actif()
    monkeypatch.setenv("MIKA_ENV", "")
    monkeypatch.setenv("MIKA_RATE_LIMIT", "peut-etre")
    with pytest.raises(L.ConfigLimitationInvalide):
        L.actif()


# --------------------------------------------------------------------------- #
# Connexion
# --------------------------------------------------------------------------- #
@pytest.fixture()
def comptes(client, monkeypatch, horloge):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    monkeypatch.setenv("MIKA_PROXY_HOPS", "1")
    db = BillingSession()
    for nom in ("victime", "autre"):
        crud_billing.creer_compte(db, email=f"{nom}@example.com", mot_de_passe=MDP)
    db.close()
    return client


def _login(c, email, mdp="mauvais-mdp-000", ip="10.0.0.1"):
    return c.post("/api/v1/comptes/connexion", json={"email": email, "mot_de_passe": mdp},
                  headers={"X-Forwarded-For": ip})


def test_force_brute_ciblee_bloquee_avec_retry_after(comptes):
    for _ in range(5):
        assert _login(comptes, "victime@example.com").status_code == 401
    r = _login(comptes, "victime@example.com", mdp=MDP)  # même le BON mot de passe est refusé
    assert r.status_code == 429 and r.json()["detail"] == "trop_de_tentatives"
    assert int(r.headers["Retry-After"]) == 30


def test_pas_de_dos_contre_la_victime(comptes):
    """L'attaquant (10.0.0.66) s'acharne : la victime (autre IP) se connecte normalement."""
    for _ in range(40):
        _login(comptes, "victime@example.com", ip="10.0.0.66")
    assert _login(comptes, "victime@example.com", ip="10.0.0.66").status_code == 429
    assert _login(comptes, "victime@example.com", mdp=MDP, ip="192.168.1.20").status_code == 200


def test_pas_de_dos_attaquant_distribue(comptes):
    """150 échecs sur l'e-mail de la victime depuis 150 IP (botnet) : la victime n'est PAS
    verrouillée (aucune clé « e-mail seul » par défaut — sinon n'importe qui la bloquerait)."""
    for i in range(150):
        assert _login(comptes, "victime@example.com", ip=f"10.8.{i // 200}.{i % 200}").status_code == 401
    assert _login(comptes, "victime@example.com", mdp=MDP, ip="192.168.1.20").status_code == 200


def test_utilisateur_de_la_meme_ip_non_bloque_par_la_cle_ciblee(comptes):
    for _ in range(5):
        _login(comptes, "victime@example.com")
    assert _login(comptes, "autre@example.com", mdp=MDP).status_code == 200


def test_pulverisation_depuis_une_ip_bloquee(comptes):
    for i in range(30):
        _login(comptes, f"inconnu{i}@example.com", ip="10.9.9.9")
    assert _login(comptes, "autre@example.com", mdp=MDP, ip="10.9.9.9").status_code == 429
    assert _login(comptes, "autre@example.com", mdp=MDP, ip="10.9.9.10").status_code == 200


def test_reset_apres_connexion_reussie(comptes):
    for _ in range(4):
        _login(comptes, "victime@example.com")
    assert _login(comptes, "victime@example.com", mdp=MDP).status_code == 200
    for _ in range(4):
        assert _login(comptes, "victime@example.com").status_code == 401  # compteur reparti de zéro


def test_fin_du_blocage_puis_backoff_double(comptes, horloge):
    for _ in range(5):
        _login(comptes, "victime@example.com")
    horloge.t += 31
    assert _login(comptes, "victime@example.com").status_code == 401  # 6e échec autorisé…
    r = _login(comptes, "victime@example.com")
    assert r.status_code == 429 and int(r.headers["Retry-After"]) == 60  # …puis blocage doublé


def test_blocage_identique_email_existant_ou_non(comptes):
    for email in ("victime@example.com", "fantome@example.com"):
        for _ in range(5):
            _login(comptes, email, ip="10.1.1.1")
    a = _login(comptes, "victime@example.com", ip="10.1.1.1")
    b = _login(comptes, "fantome@example.com", ip="10.1.1.1")
    assert (a.status_code, a.json(), a.headers["Retry-After"]) == (b.status_code, b.json(), b.headers["Retry-After"])


def test_bloque_avant_bcrypt(comptes, monkeypatch):
    for _ in range(5):
        _login(comptes, "victime@example.com")
    appels = []
    monkeypatch.setattr(crud_billing, "verifier_mot_de_passe", lambda *a: appels.append(1) or False)
    assert _login(comptes, "victime@example.com").status_code == 429
    assert appels == []  # un blocage ne coûte aucun hachage (anti-DoS CPU)


def test_x_forwarded_for_ignore_sans_proxy_de_confiance(comptes, monkeypatch):
    monkeypatch.setenv("MIKA_PROXY_HOPS", "0")
    for i in range(5):  # l'attaquant change l'en-tête à chaque requête : inutile
        _login(comptes, "victime@example.com", ip=f"10.0.0.{i}")
    assert _login(comptes, "victime@example.com", ip="10.0.0.200").status_code == 429


def test_x_forwarded_for_entrees_forgees_a_gauche_ignorees(comptes):
    for i in range(5):
        _login(comptes, "victime@example.com", ip=f"6.6.6.{i}, 10.0.0.1")
    assert _login(comptes, "victime@example.com", ip="1.1.1.1, 10.0.0.1").status_code == 429


def test_limite_email_global_optionnelle(comptes, monkeypatch):
    monkeypatch.setenv("MIKA_RL_EMAIL_GLOBAL", "1")
    for i in range(100):
        _login(comptes, "victime@example.com", ip=f"10.2.{i // 250}.{i % 250}")
    assert _login(comptes, "victime@example.com", mdp=MDP, ip="192.168.1.20").status_code == 429


def test_limitation_desactivable_hors_production(comptes, monkeypatch):
    monkeypatch.setenv("MIKA_RATE_LIMIT", "off")
    for _ in range(10):
        assert _login(comptes, "victime@example.com").status_code == 401


def test_inscriptions_en_rafale(client, monkeypatch, horloge):
    import bcrypt

    gensalt = bcrypt.gensalt
    monkeypatch.setattr(crud_billing._bcrypt, "gensalt", lambda *a, **k: gensalt(4))
    codes = [client.post("/api/v1/comptes/inscription",
                         json={"email": f"n{i}@example.com", "mot_de_passe": MDP}).status_code for i in range(21)]
    assert codes[:20] == [201] * 20 and codes[20] == 429


# --------------------------------------------------------------------------- #
# Jetons
# --------------------------------------------------------------------------- #
@pytest.fixture()
def parent(client, monkeypatch, horloge):
    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    monkeypatch.setenv("MIKA_PROXY_HOPS", "1")
    db = BillingSession()
    p = crud_billing.creer_compte(db, email="p-rl@example.com", mot_de_passe=MDP, role="parent")
    liens.lier(db, p.id, hmac_eleve("eleve-rl"), "parent")
    tok = creer_token(p)
    db.close()
    return client, tok


def _jeton(c, tok, ip="10.0.0.1"):
    return c.post("/api/v1/auth/eleve/jeton", json={"student_pseudo_id": "eleve-rl"},
                  headers={"Authorization": f"Bearer {tok}", "X-Forwarded-For": ip})


def test_quota_emission_jetons_par_compte(parent):
    c, tok = parent
    codes = [_jeton(c, tok, ip=f"10.3.0.{i}").status_code for i in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429


def test_jetons_invalides_repetes_bloquent_la_source_seulement(parent):
    c, tok = parent
    h = {"X-Forwarded-For": "10.4.4.4"}
    for i in range(50):
        r = c.get("/api/v1/rgpd/export/eleve-rl", headers={**h, "Authorization": f"Bearer faux.{i}.jeton"})
        assert r.status_code == 401
    r = c.get("/api/v1/rgpd/export/eleve-rl", headers={**h, "Authorization": f"Bearer {tok}"})
    assert r.status_code == 429  # même un jeton valide : la source sonde des jetons
    r = c.get("/api/v1/rgpd/export/eleve-rl", headers={"X-Forwarded-For": "10.5.5.5", "Authorization": f"Bearer {tok}"})
    assert r.status_code in (200, 404)  # autre source : non affectée


def test_jetons_invalides_sur_comptes_moi(parent):
    c, tok = parent
    for i in range(50):
        c.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer x{i}", "X-Forwarded-For": "10.6.6.6"})
    assert c.get("/api/v1/comptes/moi", headers={"Authorization": f"Bearer {tok}",
                                                  "X-Forwarded-For": "10.6.6.6"}).status_code == 429


def test_jeton_de_compte_invalide_a_l_emission_compte_comme_sondage(parent):
    c, _ = parent
    for i in range(50):
        assert _jeton(c, f"faux{i}", ip="10.7.7.7").status_code == 401
    assert _jeton(c, "faux", ip="10.7.7.7").status_code == 429


def test_oubli_apres_inactivite_depuis_la_fin_du_blocage():
    lim, h = _lim()
    for _ in range(3):
        lim.echec("k")
    h.t += 10 + 59  # blocage (10 s) + 59 s d'inactivité : historique conservé
    lim.echec("k")
    assert lim.attente("k") == 20
    h.t += 20 + 61  # fin du blocage + 61 s sans échec : oublié
    lim.echec("k")
    assert lim.attente("k") == 0
