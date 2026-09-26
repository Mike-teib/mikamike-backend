"""
Session 5 — migrations de la release candidate : TOUTES les têtes ensemble.

1. Matrice : pour chaque couple de révisions de départ (mika × billing, de `base` à head), les deux
   bases sont montées ensemble à head ; le schéma final est identique aux modèles, les données
   insérées au départ sont conservées, et l'application démarre en `MIKA_DB_INIT=check` puis sert
   un parcours réel (inscription, vérification, soumission d'exercice, dashboard).
2. Rollback du runbook : une base créée et remplie PAR L'API à head est ramenée au schéma de la
   PR #5 (b0003), puis remontée : comptes, liens et tentatives conservés ; perte documentée
   (verifications_email, jeton_version) seulement.
3. Reprise : un upgrade complet interrompu au milieu de la chaîne billing reprend jusqu'à head.

Chaque scénario : sous-processus, SQLite jetables (aucune base réelle).
"""

import pytest

from tests_cloud.test_migrations_validation import _cli, _py

MIKA = ["base", "m0001_baseline", "m0002_index_tentatives", "m0003_tutorat"]
BILLING = ["base", "b0001_baseline", "b0002_liens_compte_eleve", "b0003_invitations_lien",
           "b0004_verif_email_revocation"]

MATRICE = """
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData
from app.db.registre import metadatas

def diffs(c):
    md = MetaData()
    for x in metadatas(c):
        for t in x.tables.values():
            t.to_metadata(md)
    with engines()[c].connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        return [str(d) for d in compare_metadata(ctx, md)]

depart = {"mika": DEPART_MIKA, "billing": DEPART_BILLING}
for c, rev in depart.items():
    if rev != "base":
        m.upgrade(c, rev)
if depart["mika"] != "base":
    remplir_mika()
if depart["billing"] != "base":
    remplir_billing()
avant = {"mika": empreinte("mika", HIST_MIKA) if depart["mika"] != "base" else None,
         "billing": empreinte("billing", ["comptes", "abonnements"]) if depart["billing"] != "base" else None}
for c in ("mika", "billing"):
    m.upgrade(c)
apres = {"mika": empreinte("mika", HIST_MIKA) if depart["mika"] != "base" else None,
         "billing": empreinte("billing", ["comptes", "abonnements"]) if depart["billing"] != "base" else None}

import os
os.environ.update({"MIKA_DB_INIT": "check", "MIKA_AUTH_MODE": "off", "MIKA_EMAIL_TRANSPORT": "faux"})
from fastapi.testclient import TestClient
import main
from app.core.courriel import boite_de_test
parcours = {}
with TestClient(main.app) as c:
    r = c.post("/api/v1/comptes/inscription", json={"email": "matrice@example.com", "mot_de_passe": "motdepasse-matrice-1"})
    parcours["inscription"] = r.status_code
    jeton = boite_de_test().derniers("matrice@example.com")[-1].metadonnees["jeton"]
    parcours["verification"] = c.post("/api/v1/comptes/verification-email/confirmer", json={"jeton": jeton}).status_code
    r = c.post("/api/v1/exercices/soumettre", json={"exercice_id": "exo-maths-algebre-1",
               "student_pseudo_id": "eleve-matrice", "reponse": "3"})
    parcours["soumettre"] = r.status_code
    parcours["progression"] = r.json().get("progression", {}).get("moteur")
    parcours["dashboard"] = c.get("/api/v1/parents/dashboard/eleve-matrice").status_code
print(json.dumps({"diffs": {c: diffs(c) for c in ("mika", "billing")}, "etat": m.etat(),
                  "avant": avant, "apres": apres, "parcours": parcours}))
"""


@pytest.mark.parametrize("depart_billing", BILLING)
@pytest.mark.parametrize("depart_mika", MIKA)
def test_matrice_toutes_les_tetes_ensemble(tmp_path, depart_mika, depart_billing):
    out = _py(tmp_path, MATRICE.replace("DEPART_MIKA", repr(depart_mika)).replace("DEPART_BILLING", repr(depart_billing)))
    assert out["diffs"] == {"mika": [], "billing": []}
    for c in ("mika", "billing"):
        assert out["etat"][c]["courante"] == out["etat"][c]["head"]
    assert out["avant"] == out["apres"]  # données présentes au départ conservées
    assert out["parcours"] == {"inscription": 201, "verification": 200, "soumettre": 200,
                               "progression": "historique", "dashboard": 200}


def test_rollback_runbook_vers_pr5_puis_retour_donnees_conservees(tmp_path):
    assert _cli(tmp_path, "upgrade")[0] == 0
    out = _py(tmp_path, """
        import os
        os.environ.update({"MIKA_DB_INIT": "check", "MIKA_AUTH_MODE": "off", "MIKA_EMAIL_TRANSPORT": "faux"})
        from fastapi.testclient import TestClient
        import main
        with TestClient(main.app) as c:
            for i in range(3):
                assert c.post("/api/v1/comptes/inscription", json={"email": f"rb{i}@example.com",
                              "mot_de_passe": "motdepasse-rollback-1"}).status_code == 201
            for i in range(5):
                assert c.post("/api/v1/exercices/soumettre", json={"exercice_id": "exo-maths-algebre-1",
                              "student_pseudo_id": "eleve-rb", "reponse": str(i)}).status_code == 200
        from sqlalchemy import text
        with engines()["billing"].begin() as conn:
            conn.execute(text("UPDATE comptes SET jeton_version = 3 WHERE email = 'rb0@example.com'"))
        print(json.dumps({"billing": empreinte("billing", ["comptes", "abonnements"]),
                          "mika": empreinte("mika", HIST_MIKA),
                          "verifs": engines()["billing"].connect().execute(text("SELECT COUNT(*) FROM verifications_email")).scalar()}))
    """)
    assert out["verifs"] == 3
    code, _, err = _cli(tmp_path, "downgrade", "billing", "b0003_invitations_lien")
    assert code == 0, err
    rb = _py(tmp_path, """
        print(json.dumps({"tables": tables("billing"), "billing": empreinte("billing", ["comptes", "abonnements"]),
                          "mika": empreinte("mika", HIST_MIKA), "rev": m.courante("billing")}))
    """)
    assert rb["rev"] == "b0003_invitations_lien" and "verifications_email" not in rb["tables"]
    assert (rb["billing"], rb["mika"]) == (out["billing"], out["mika"])
    assert _cli(tmp_path, "upgrade")[0] == 0
    retour = _py(tmp_path, """
        from sqlalchemy import text
        with engines()["billing"].connect() as conn:
            versions = sorted(r[0] for r in conn.execute(text("SELECT jeton_version FROM comptes")))
        print(json.dumps({"billing": empreinte("billing", ["comptes", "abonnements"]),
                          "mika": empreinte("mika", HIST_MIKA), "versions": versions, "etat": m.etat()}))
    """)
    assert (retour["billing"], retour["mika"]) == (out["billing"], out["mika"])
    # Perte documentée du rollback : jeton_version remis à 0 (tous les jetons émis avant restent
    # valables jusqu'à expiration) — RUNBOOK : forcer une rotation de MIKA_JWT_SECRET si besoin.
    assert retour["versions"] == [0, 0, 0]


def test_upgrade_complet_interrompu_dans_la_derniere_tete_puis_reprise(tmp_path):
    """Coupure dans b0004 (tête la plus récente) en partant de b0002 : chaque révision est
    ATOMIQUE — b0003, entièrement appliquée, reste validée ; b0004 est annulée sans trace
    (aucune table partielle) ; données intactes ; relancer reprend jusqu'à head."""
    out = _py(tmp_path, """
        from alembic.operations import Operations
        m.upgrade("mika")
        m.upgrade("billing", "b0002_liens_compte_eleve")
        remplir_billing()
        avant = [m.courante("billing"), tables("billing"), empreinte("billing", ["comptes", "abonnements"])]
        orig = Operations.create_table
        def coupure(self, nom, *a, **k):
            if nom == "verifications_email":
                raise RuntimeError("coupure simulee")
            return orig(self, nom, *a, **k)
        Operations.create_table = coupure
        try:
            m.upgrade("billing")
            coupee = False
        except RuntimeError:
            coupee = True
        Operations.create_table = orig
        pendant = [m.courante("billing"), tables("billing"), empreinte("billing", ["comptes", "abonnements"])]
        m.upgrade("billing")
        print(json.dumps({"coupee": coupee, "avant": avant, "pendant": pendant, "etat": m.etat(),
                          "apres": empreinte("billing", ["comptes", "abonnements"])}))
    """)
    assert out["coupee"] is True
    assert out["pendant"][0] == "b0003_invitations_lien"
    assert out["pendant"][1] == sorted(out["avant"][1] + ["invitations_lien"])  # rien de b0004
    assert out["pendant"][2] == out["avant"][2]
    assert out["etat"]["billing"]["courante"] == out["etat"]["billing"]["head"]
    assert out["apres"] == out["avant"][2]
