"""
LOT 10 — Banc de conversations synthétiques du tuteur Mika, jouées via l'API HTTP réelle
(`/api/v1/mika/session/*`, TestClient, contrat `mika-tutorat/1`, MIKA_API_CONTRACT.md).

Chaque scénario est une suite d'actions start / answer / help / comprehension / GET / rejeu.
Invariants vérifiés à CHAQUE réponse (classe `Conversation`) :
  - `version` strictement croissante (+1 par transition ; inchangée sur rejeu, GET et refus) ;
  - `avec_aide`, compteurs d'aide, `termine` monotones (jamais true → false) ;
  - aucune divulgation avant l'étape prévue : ni `reponse_attendue` (toutes graphies
    équivalentes), ni `reponse_comprehension`, ni `correction_commentee` avant
    CORRECTION_COMMENTEE, ni aide future ;
  - LE-06 : aidé ⇒ jamais `ACQUIS_AUTONOME` ; compréhension infirmée ⇒ `FRAGILE` ;
  - refus attendus (tutorat terminé, compréhension non demandée / attendue, version périmée)
    rendus en 409 propre, SANS effet (version et journal des tentatives inchangés) ;
  - progression en fin de tutorat (`mika_tentatives`, `mika_etats`) : exactement une tentative
    versée, `est_correct` = résolu ET compréhension non infirmée (D14), `avec_aide` recopié,
    état recalculé = moteur sur historique (pas de double comptage), réussite aidée seule ⇒
    jamais ACQUIS_AUTONOME/MAITRISE, moins de 3 tentatives ⇒ libellé provisoire (R1).

Plus une propriété aléatoire déterministe (graines fixes, 220 séquences d'actions).
Défauts trouvés : tests `xfail(strict=True)` en fin de fichier (deviennent rouges une fois corrigés).
Contenu FICTIF uniquement (fixture `api` de test_mika_api.py).
"""

import datetime as _dt
import json
import random
from collections import Counter

import pytest

from app.api.v1.mikamike import crud, moteur
from app.api.v1.mikamike.learning_engine import ETATS_SOLIDES
from app.api.v1.mikamike.store import SessionLocal
from app.core.pseudonymisation import hmac_eleve
from app.curriculum.pedagogie.progression import Tentative, diagnostiquer
from tests_cloud.test_mika_api import (  # noqa: F401  (api : fixture réutilisée)
    A,
    EXO,
    PLAN,
    PREREQ,
    URL,
    _exercice,
    _fuite,
    api,
)

NOTION = "notion:fictif:fractions-decimales"
EX = _exercice()
CORRECTION = PLAN.correction_commentee
CLES_COMPREHENSION = ("0,9", "0.9", "0,90")
COMPTEURS = ("tentatives", "indices_donnes", "questions_posees", "methodes_donnees", "niveau_aide")
PROVISOIRES = {"INCONNU", "EN_COURS", "ACQUIS_ASSISTE"}
SOLIDES = {e.value for e in ETATS_SOLIDES} | {"MAITRISE"}


def _preparer(eleve):
    db = SessionLocal()
    try:
        crud.upsert_etat(db, hmac_eleve(eleve), PREREQ, "ACQUIS_AUTONOME")
    finally:
        db.close()


def _base(eleve):
    db = SessionLocal()
    try:
        h = hmac_eleve(eleve)
        return crud.get_etats(db, h), [t for t in crud.get_tentatives(db, h) if t.competence == NOTION]
    finally:
        db.close()


def _etat_recalcule(tents):
    """Libellé attendu = moteur sur historique appliqué aux tentatives en base."""
    h = [Tentative(t.est_correct, t.avec_aide, moteur._secondes(t.ts)) for t in reversed(tents)]
    return moteur.etat_compatible(diagnostiquer(h), h).value


class Conversation:
    """Joue une conversation via HTTP et vérifie les invariants à chaque réponse."""

    def __init__(self, client, eleve=A, headers=None):
        self.c, self.eleve, self.headers = client, eleve, headers or {}
        self.t = None                # dernière vue complète connue (réponse de transition ou GET)
        self.n = 0
        self.corrige = False         # CORRECTION_COMMENTEE déjà émise
        self.diff = None             # dernière difficulté proposée
        self.journal = {}            # requete_id -> (op, corps, réponse d'origine)
        self.actions = []
        self.nb_tent = len(_base(eleve)[1])

    # ------------------------------------------------------------------ appels
    def _post(self, op, corps):
        return self.c.post(f"{URL}/{op}", json=corps, headers=self.headers)

    def get(self):
        r = self.c.get(f"{URL}/{self.t['tutorat_id']}", params={"student_id": self.eleve}, headers=self.headers)
        assert r.status_code == 200, r.text
        g = r.json()
        assert set(g) == {"contract_version", "tutorat_id", "version", "exercice_id", "derniere_action", "etat"}
        assert g["version"] == self.t["version"] and g["etat"] == self.t["etat"]
        self._divulgation(g)
        return g

    def start(self, req="st", exo=EXO):
        r = self._post("start", {"student_pseudo_id": self.eleve, "requete_id": req, "exercice_id": exo})
        assert r.status_code in (200, 201), r.text
        out = r.json()
        assert out["contract_version"] == "mika-tutorat/1" and out["version"] == 1
        self.t, self.diff = out, out["reponse"]["difficulte_proposee"]
        self.actions.append(out["reponse"]["action"])
        self._divulgation(out)
        return out

    def _attendu_refus(self, op):
        e = self.t["etat"]
        if e["termine"]:
            return "tutorat_termine"
        if op == "comprehension" and not e["attend_comprehension"]:
            return "comprehension_non_demandee"
        if op in ("answer", "help") and e["attend_comprehension"]:
            return "comprehension_attendue"
        return None

    def op(self, op, req=None, **kw):
        """Transition. Renvoie la réponse JSON, ou None si le refus (409) attendu a eu lieu."""
        if req is None:
            self.n += 1
            req = f"auto-{op}-{self.n}"
        corps = {"student_pseudo_id": self.eleve, "requete_id": req, "tutorat_id": self.t["tutorat_id"],
                 "version": self.t["version"], **kw}
        refus = self._attendu_refus(op)
        r = self._post(op, corps)
        if refus is not None:
            assert r.status_code == 409 and r.json()["detail"] == refus, (op, kw, r.text)
            self._sans_effet()
            return None
        assert r.status_code == 200, (op, kw, r.text)
        out = r.json()
        assert out["rejeu"] is False
        self._invariants(self.t, out)
        self.journal[req] = (op, corps, out)
        self.t = out
        self.actions.append(out["reponse"]["action"])
        return out

    def answer(self, reponse, **kw):
        return self.op("answer", reponse=reponse, **kw)

    def help(self, **kw):
        return self.op("help", **kw)

    def comp(self, reponse, **kw):
        return self.op("comprehension", reponse=reponse, **kw)

    def rejouer(self, req):
        """Rejoue une requête déjà traitée : même réponse, aucune transition."""
        op, corps, origine = self.journal[req]
        r = self._post(op, corps)
        assert r.status_code == 200, r.text
        assert r.json() == {**origine, "rejeu": True}
        self._sans_effet()

    def perimee(self):
        """Client resté sur une version antérieure : 409 version_perimee, sans effet."""
        if self.t["version"] < 2:
            return
        corps = {"student_pseudo_id": self.eleve, "requete_id": f"old{self.n}", "tutorat_id": self.t["tutorat_id"],
                 "version": self.t["version"] - 1}
        r = self._post("help", corps)
        assert r.status_code == 409
        assert r.json()["detail"] == {"code": "version_perimee", "version_courante": self.t["version"]}
        self._sans_effet()

    # ------------------------------------------------------------- invariants
    def _sans_effet(self):
        self.get()
        assert len(_base(self.eleve)[1]) == self.nb_tent

    def _divulgation(self, out):
        brut = json.dumps(out, ensure_ascii=False)
        assert "reponse_attendue" not in brut and "reponse_comprehension" not in brut
        for cle in CLES_COMPREHENSION:
            assert cle not in brut, cle
        action = out.get("reponse", {}).get("action") or out["derniere_action"]
        if not self.corrige and action != "CORRECTION_COMMENTEE":
            assert CORRECTION not in brut
            assert not _fuite(out), out["etat"]["messages"]
        e = out["etat"]
        futures = (list(PLAN.questions_intermediaires[e["questions_posees"]:])
                   + list(EX.indices[e["indices_donnes"]:])
                   + list(PLAN.methodes_alternatives[e["methodes_donnees"]:]))
        for aide in futures:
            assert aide not in brut, aide

    def _invariants(self, prev, out):
        e, p = out["etat"], prev["etat"]
        assert out["contract_version"] == "mika-tutorat/1"
        assert out["tutorat_id"] == prev["tutorat_id"]
        assert out["version"] == prev["version"] + 1  # strictement croissante
        assert e["avec_aide"] >= p["avec_aide"]       # jamais true -> false
        for k in COMPTEURS:
            assert e[k] >= p[k], k
        assert e["termine"] >= p["termine"]
        assert e["resolu"] >= p["resolu"]
        if e["avec_aide"]:
            assert e["niveau_estime"] != "ACQUIS_AUTONOME"  # LE-06
        if e["comprehension_verifiee"] is False:
            assert e["niveau_estime"] == "FRAGILE"
        d = out["reponse"]["difficulte_proposee"]
        assert d <= self.diff
        self.diff = d
        self._divulgation(out)
        if out["reponse"]["action"] == "CORRECTION_COMMENTEE":
            assert e["termine"]
            self.corrige = True
        self._progression(p, e)

    def _progression(self, p, e):
        etats, tents = _base(self.eleve)
        if not (e["termine"] and not p["termine"] and e["prerequis_manquant"] is None):
            assert len(tents) == self.nb_tent, "tentative versée hors fin de tutorat"
            return
        assert len(tents) == self.nb_tent + 1, "une tentative et une seule par tutorat terminé"
        self.nb_tent += 1
        derniere = tents[0]
        reussi = e["resolu"] and e["comprehension_verifiee"] is not False
        assert derniere.est_correct is reussi
        assert derniere.avec_aide is e["avec_aide"]
        if e["comprehension_verifiee"] is False:
            assert not derniere.est_correct  # D14
        etat = etats[NOTION]
        assert etat == _etat_recalcule(tents)  # moteur sur historique, sans double comptage
        if all(t.avec_aide or not t.est_correct for t in tents):
            assert etat not in SOLIDES  # réussites aidées seules : jamais autonome / maîtrise
        if len(tents) < 3:
            assert etat in PROVISOIRES  # R1 : pas de diagnostic sur une ou deux réponses


def _conv(client, eleve=A, **kw):
    c = Conversation(client, eleve, **kw)
    c.start()
    return c


# =========================================================================== #
# Scénarios obligatoires
# =========================================================================== #
def test_eleve_correct(api):
    c = _conv(api)
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "CONSOLIDATION" and out["reponse"]["message"].startswith("Bravo")
    assert out["etat"]["niveau_estime"] == "ACQUIS_AUTONOME" and not out["etat"]["avec_aide"]
    etats, tents = _base(A)
    assert len(tents) == 1 and tents[0].est_correct and not tents[0].avec_aide
    assert etats[NOTION] == "EN_COURS"  # provisoire (R1) : jamais « solide » sur une réponse


def test_eleve_faux_jusqu_a_la_correction(api):
    c = _conv(api)
    actions = []
    for i in range(12):
        out = c.answer(str(5 + i))
        if out is None:
            break
        actions.append(out["reponse"]["action"])
    assert actions[0] == "IDENTIFIER_BLOCAGE"
    assert actions[1:] == ["QUESTION_INTERMEDIAIRE", "DONNER_INDICE", "DONNER_INDICE", "AUTRE_METHODE",
                           "AUTRE_METHODE", "CORRECTION_COMMENTEE"]
    e = c.t["etat"]
    assert e["termine"] and e["niveau_estime"] == "FRAGILE" and e["tentatives"] == 7
    etats, tents = _base(A)
    assert len(tents) == 1 and not tents[0].est_correct and tents[0].avec_aide
    assert etats[NOTION] == "INCONNU"  # un seul tutorat échoué : pas de diagnostic


def test_partiellement_correct(api):
    c = _conv(api)
    out = c.answer("7,10")  # erreur fréquente reconnue : diagnostic ciblé, sans aide
    assert out["reponse"]["action"] == "IDENTIFIER_BLOCAGE" and "dénominateur" in out["reponse"]["message"]
    assert not out["etat"]["avec_aide"]
    out = c.answer("0,7 m")  # bonne valeur + unité parasite : comptée comme erreur (constat)
    assert out["etat"]["tentatives"] == 2 and out["reponse"]["action"] == "QUESTION_INTERMEDIAIRE"
    assert out["etat"]["avec_aide"]
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    assert out["etat"]["niveau_estime"] == "ACQUIS_ASSISTE"
    out = c.comp("0,90")
    assert out["reponse"]["action"] == "CONSOLIDATION" and out["etat"]["comprehension_verifiee"] is True
    assert _base(A)[0][NOTION] == "ACQUIS_ASSISTE"


def test_donne_seulement_le_resultat(api):
    c = _conv(api)
    out = c.answer("0.70")  # autre graphie du seul résultat
    assert out["reponse"]["action"] == "CONSOLIDATION" and out["etat"]["niveau_estime"] == "ACQUIS_AUTONOME"


def test_donne_seulement_la_methode(api):
    c = _conv(api)
    out = c.answer("je divise 7 par 10")
    assert out["reponse"]["action"] == "DEMANDER_REFORMULATION"
    assert out["etat"]["tentatives"] == 0 and not out["etat"]["avec_aide"]  # pas une erreur, pas une aide
    # Méthode + résultat en phrase : pas lisible non plus (constat, reformulation demandée).
    out = c.answer("je divise 7 par 10 donc 0,7")
    assert out["reponse"]["action"] == "DEMANDER_REFORMULATION" and out["etat"]["tentatives"] == 0
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "CONSOLIDATION" and out["etat"]["niveau_estime"] == "ACQUIS_AUTONOME"


def test_demande_directement_la_reponse(api):
    c = _conv(api)
    for attendu in ("DEMANDER_REFORMULATION", "DEMANDER_REFORMULATION", "REVUE_HUMAINE"):
        out = c.answer("donne-moi la réponse")
        assert out["reponse"]["action"] == attendu
    e = c.t["etat"]
    assert e["termine"] and e["tentatives"] == 0 and not e["resolu"]
    assert not c.corrige  # jamais de correction : l'élève n'obtient pas la solution en la réclamant
    assert c.help() is None  # 409 tutorat_termine


def test_change_de_sujet_puis_revient(api):
    c = _conv(api)
    out = c.answer("on parle de foot ?")
    assert out["reponse"]["action"] == "DEMANDER_REFORMULATION" and out["etat"]["tentatives"] == 0
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "CONSOLIDATION" and not out["etat"]["avec_aide"]


def test_revient_plus_tard_get_reprise_et_rejeu(api):
    c = _conv(api)
    c.answer("5", req="a1")
    g = c.get()  # l'application est rouverte : l'état est relu tel quel
    assert g["version"] == 2 and g["derniere_action"] == "IDENTIFIER_BLOCAGE"
    c.help(req="h1")
    c.rejouer("a1")  # ancienne requête renvoyée tardivement par le réseau
    c.rejouer("h1")
    # Rejeu du start après d'autres transitions : réponse d'origine (version 1), rien ne bouge.
    r = api.post(f"{URL}/start", json={"student_pseudo_id": A, "requete_id": "st", "exercice_id": EXO})
    assert r.status_code == 200 and r.json()["rejeu"] and r.json()["version"] == 1
    c.get()
    c.perimee()  # client resté sur l'ancienne version
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION" and out["etat"]["avec_aide"]
    c.comp("0,9")
    c.rejouer("a1")  # rejeu après la fin : toujours la réponse d'origine


def test_tutorat_termine_operations_refusees_proprement(api):
    c = _conv(api)
    c.answer("0,7")
    assert c.t["etat"]["termine"]
    assert c.answer("0,7") is None and c.help() is None and c.comp("0,9") is None
    c.perimee()


def test_seance_expiree_jeton_expire(api, monkeypatch):
    from app.core import auth
    from paiement_comptes import liens
    from paiement_comptes.database import SessionLocal as BillingSession
    from paiement_comptes.models_billing import Compte

    monkeypatch.setenv("MIKA_AUTH_MODE", "enforce")
    bdb = BillingSession()
    compte = Compte(email="p-bench@example.com", mot_de_passe_hash="x", role="parent")
    bdb.add(compte)
    bdb.commit()
    liens.lier(bdb, compte.id, hmac_eleve(A), "parent")
    cid = compte.id
    bdb.close()
    frais, _ = auth.emettre_jeton_eleve(A, compte_id=cid)
    c = _conv(api, headers={"Authorization": f"Bearer {frais}"})
    c.help()
    passe = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=3)
    vieux, _ = auth.emettre_jeton_eleve(A, compte_id=cid, maintenant=passe)
    corps = {"student_pseudo_id": A, "requete_id": "exp", "tutorat_id": c.t["tutorat_id"],
             "version": c.t["version"], "reponse": "0,7"}
    r = api.post(f"{URL}/answer", json=corps, headers={"Authorization": f"Bearer {vieux}"})
    assert r.status_code == 401 and r.json()["detail"] == "jeton_expire"
    r = api.get(f"{URL}/{c.t['tutorat_id']}", params={"student_id": A},
                headers={"Authorization": f"Bearer {vieux}"})
    assert r.status_code == 401
    c.get()  # jeton frais : rien n'a bougé
    out = c.answer("0,7")  # reprise après ré-authentification ; l'aide reçue reste acquise
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION" and out["etat"]["avec_aide"]


def test_seance_reprise_depuis_un_autre_client(api):
    from fastapi.testclient import TestClient

    from main import app

    c = _conv(api)
    c.help()
    c.answer("5")
    autre = TestClient(app)  # autre appareil / application relancée (même état serveur)
    c2 = Conversation(autre)
    c2.t, c2.diff = dict(c.t), c.diff  # le nouveau client ne connaît que l'identifiant...
    g = c2.get()                       # ... et relit l'état serveur avant de reprendre
    c2.t = {**c.t, **g}
    assert g["etat"]["avec_aide"]
    out = c2.answer("0,7")
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    assert out["etat"]["niveau_estime"] == "ACQUIS_ASSISTE"
    out = c2.comp("0,9")
    assert out["etat"]["termine"]


def test_aide_demandee(api):
    c = _conv(api)
    d0 = c.diff
    out = c.help()
    assert out["reponse"]["action"] == "QUESTION_INTERMEDIAIRE" and out["etat"]["avec_aide"]
    assert out["reponse"]["difficulte_proposee"] <= d0
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    assert c.help() is None  # 409 comprehension_attendue
    assert c.answer("0,7") is None
    out = c.comp("0,9")
    assert out["reponse"]["action"] == "CONSOLIDATION" and out["etat"]["niveau_estime"] == "ACQUIS_ASSISTE"
    etats, tents = _base(A)
    assert tents[0].est_correct and tents[0].avec_aide and etats[NOTION] == "ACQUIS_ASSISTE"


def test_plusieurs_aides(api):
    c = _conv(api)
    actions = []
    for _ in range(8):
        out = c.help()
        if out is None:
            break
        actions.append(out["reponse"]["action"])
    assert actions == ["QUESTION_INTERMEDIAIRE", "DONNER_INDICE", "DONNER_INDICE", "AUTRE_METHODE",
                       "AUTRE_METHODE", "CORRECTION_COMMENTEE"]
    assert CORRECTION in c.t["etat"]["messages"] and c.t["etat"]["niveau_estime"] == "FRAGILE"
    etats, tents = _base(A)
    assert not tents[0].est_correct and tents[0].avec_aide and etats[NOTION] == "INCONNU"


def test_comprehension_finale_ratee_d14(api):
    c = _conv(api)
    c.help()
    c.answer("0,7")
    out = c.comp("0,09")
    assert out["reponse"]["action"] == "AUTRE_METHODE" and out["etat"]["niveau_estime"] == "FRAGILE"
    assert out["etat"]["comprehension_verifiee"] is False and not out["etat"]["termine"]
    while not c.t["etat"]["termine"]:
        c.help()
    assert c.t["reponse"]["action"] == "CORRECTION_COMMENTEE"
    etats, tents = _base(A)
    assert not tents[0].est_correct  # D14 : résolu mais compréhension ratée ⇒ tentative non réussie
    assert etats[NOTION] == "INCONNU"


def test_comprehension_finale_ratee_sans_methode_restante(api):
    c = _conv(api)
    for _ in range(5):  # question, 2 indices, 2 méthodes : toutes les aides sauf la correction
        c.help()
    c.answer("0,7")
    out = c.comp("9")
    assert out["reponse"]["action"] == "CONSOLIDATION" and not out["reponse"]["message"].startswith("Bravo")
    assert out["etat"]["termine"] and not c.corrige
    assert not _base(A)[1][0].est_correct


def test_comprehension_ratee_puis_reussie(api):
    """Constat : après un D14 raté puis une autre méthode, une 2e vérification réussie donne
    « Bravo » et une tentative réussie (aidée), mais `niveau_estime` reste FRAGILE."""
    c = _conv(api)
    c.help()
    c.answer("0,7")
    c.comp("0,09")
    out = c.answer("0,7")
    assert out["reponse"]["action"] == "VERIFIER_COMPREHENSION"
    out = c.comp("0,9")
    assert out["reponse"]["message"].startswith("Bravo") and out["etat"]["comprehension_verifiee"] is True
    assert out["etat"]["niveau_estime"] == "FRAGILE"
    t = _base(A)[1][0]
    assert t.est_correct and t.avec_aide


def test_double_comprehension_ratee_revue_humaine(api):
    c = _conv(api)
    c.help()
    for _ in range(2):
        c.answer("0,7")
        c.comp("0,09")
    out = c.answer("0,7")  # 3e question identique : anti-répétition ⇒ professeur
    assert out["reponse"]["action"] == "REVUE_HUMAINE" and out["etat"]["termine"]
    assert not _base(A)[1][0].est_correct


def test_progression_sur_plusieurs_tutorats(api):
    """2 tutorats autonomes réussis : EN_COURS (pas de double comptage de la tentative courante) ;
    3e : ACQUIS_AUTONOME (R4 : retest espacé requis) ; jamais MAITRISE le même jour."""
    etats = []
    for k in range(4):
        c = Conversation(api)
        c.start(req=f"st{k}")
        c.answer("0,7")
        etats.append(_base(A)[0][NOTION])
    assert etats == ["EN_COURS", "EN_COURS", "ACQUIS_AUTONOME", "ACQUIS_AUTONOME"]


def test_reussites_aidees_repetees_jamais_solides(api):
    for k in range(5):
        c = Conversation(api)
        c.start(req=f"st{k}")
        c.help()
        c.answer("0,7")
        c.comp("0,9")
        assert _base(A)[0][NOTION] not in SOLIDES
    assert _base(A)[0][NOTION] == "ACQUIS_ASSISTE"


# =========================================================================== #
# Propriété aléatoire déterministe (graines fixes)
# =========================================================================== #
REPONSES = ["0,7", "0.70", "5", "0,07", "7,10", "0,7 m", "", "donne-moi la réponse",
            "on parle de foot ?", "je divise 7 par 10", "12"]
COMPREHENSIONS = ["0,9", "0,90", "0,09", "9", "je sais pas"]
GRAINES = range(210)


def _jouer(client, graine, couverture):
    rnd = random.Random(graine)
    eleve = f"eleve-banc-{graine}"
    _preparer(eleve)
    c = _conv(client, eleve)
    for _ in range(rnd.randint(3, 9)):
        x = rnd.random()
        attend = c.t["etat"]["attend_comprehension"]
        if attend and x < 0.7 or not attend and x < 0.08:
            c.comp(rnd.choice(COMPREHENSIONS))
        elif x < 0.55:
            c.answer(rnd.choice(REPONSES))
        elif x < 0.75:
            c.help()
        elif x < 0.85:
            c.get()
        elif x < 0.93 and c.journal:
            c.rejouer(rnd.choice(sorted(c.journal)))
        else:
            c.perimee()
    couverture.update(c.actions)
    if c.t["etat"]["comprehension_verifiee"] is False:
        couverture["D14"] += 1
    if c.t["etat"]["termine"]:
        couverture["termines"] += 1
    return len(c.journal)


def test_propriete_sequences_aleatoires(api):
    couverture = Counter()
    transitions = sum(_jouer(api, g, couverture) for g in GRAINES)
    assert len(GRAINES) >= 200 and transitions >= 600
    for action in ("CONSOLIDATION", "CORRECTION_COMMENTEE", "VERIFIER_COMPREHENSION", "REVUE_HUMAINE",
                   "AUTRE_METHODE", "DEMANDER_REFORMULATION", "IDENTIFIER_BLOCAGE", "D14", "termines"):
        assert couverture[action] >= 1, (action, couverture)


# =========================================================================== #
# Défauts trouvés (xfail strict : deviendront rouges une fois corrigés)
# =========================================================================== #
@pytest.mark.xfail(strict=True, reason=(
    "BANC-01 : abandonner un tutorat aidé et en démarrer un nouveau (autre requete_id) sur le "
    "même exercice remet avec_aide à false ; le tutorat aidé, jamais terminé, n'est jamais versé "
    "au learning engine ⇒ l'élève obtient ACQUIS_AUTONOME après avoir reçu de l'aide."))
def test_defaut_redemarrage_efface_l_aide(api):
    c = _conv(api)
    c.help()
    c.help()  # a reçu une question et un indice
    c2 = Conversation(api)
    nouveau = c2.start(req="st-bis")
    c2.answer("0,7")
    assert nouveau["tutorat_id"] == c.t["tutorat_id"] or c2.t["etat"]["avec_aide"]
    assert c2.t["etat"]["niveau_estime"] != "ACQUIS_AUTONOME"


@pytest.mark.xfail(strict=True, reason=(
    "BANC-02 : trois réponses illisibles (« donne-moi la réponse », hors sujet) terminent en "
    "REVUE_HUMAINE avec tentatives=0 (« non comptée comme erreur », contrat §3), mais un ÉCHEC "
    "autonome est versé dans mika_tentatives et pèse sur la progression (3 tutorats ⇒ NON_ACQUISE)."))
def test_defaut_revue_humaine_comptee_comme_echec(api):
    c = _conv(api)
    for _ in range(3):
        c.answer("donne-moi la réponse")
    assert c.t["etat"]["tentatives"] == 0 and c.t["reponse"]["action"] == "REVUE_HUMAINE"
    tents = _base(A)[1]
    assert not any(not t.est_correct and not t.avec_aide for t in tents)


@pytest.mark.xfail(strict=True, reason=(
    "BANC-03 : « Écris 7/10 sous forme décimale » — recopier l'énoncé (« 7/10 ») est VALIDE "
    "(maths_symbolique sans forme_requise) et donne ACQUIS_AUTONOME ; valider_exercice ne détecte "
    "pas qu'une graphie équivalente de la réponse figure dans l'énoncé sans contrainte de forme."))
def test_defaut_recopier_l_enonce_est_une_reussite(api):
    c = _conv(api)
    out = c.answer("7/10")
    assert out["etat"]["niveau_estime"] != "ACQUIS_AUTONOME"
