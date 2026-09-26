"""
Simulation à blanc, rapport, métriques, quarantaine, comparaison avant/après (lot 6).
Lots SYNTHÉTIQUES uniquement (harnais) : aucun artefact réel n'est fabriqué.
"""

import json

from app.curriculum.depot import DepotContenu
from app.curriculum.harnais_import import generer_lot
from app.curriculum.rapport_import import en_markdown, simuler


def _arbo(p):
    return sorted(str(x.relative_to(p)) for x in p.rglob("*")) if p.exists() else []


def test_simulation_valide_n_ecrit_rien(tmp_path):
    lot = generer_lot(tmp_path / "lot")
    avant_lot, avant_depot = _arbo(lot.dossier), _arbo(tmp_path / "depot")
    r = simuler(lot.dossier, lot.sha_manifest, depot=tmp_path / "depot", autoriser_fictif=True)
    assert r["mode"] == "SIMULATION" and r["statut"] == "VALIDATED" and r["publiable"]
    m = r["metriques"]
    assert m["notions"] == 12 and m["notions_par_statut_preuve"] == {"PROVEN": 12} and m["generables"] == 12
    assert m["opaques_par_role"] == {"MANIFEST_VERIFIE": 1, "c02": 1, "c02_6": 1, "extraction_v3": 1}
    assert r["quarantaine"] == [] and r["comparaison"]["notions"]["ajoutes"][0] == "notion:synthetique:n0"
    assert _arbo(lot.dossier) == avant_lot and _arbo(tmp_path / "depot") == avant_depot


def test_simulation_hors_mode_test_met_tout_en_quarantaine(tmp_path):
    lot = generer_lot(tmp_path / "lot")
    r = simuler(lot.dossier, lot.sha_manifest)
    assert r["statut"] == "REJECTED" and not r["publiable"]
    assert len(r["quarantaine"]) == 12 and r["quarantaine"][0]["statut_preuve"] == "QUARANTINED"
    assert r["metriques"]["anomalies_par_code"] == {"SOURCE_FICTIVE_HORS_TEST": 1}


def test_quarantaine_avec_raisons(tmp_path):
    lot = generer_lot(tmp_path / "lot", defauts=["provenance_falsifiee"])
    r = simuler(lot.dossier, lot.sha_manifest, autoriser_fictif=True)
    q = {x["notion_id"]: x for x in r["quarantaine"]}
    assert q["notion:synthetique:n0"]["raisons"] == ["HASH_EXTRAIT_INCOHERENT"]
    assert len(q) == 1


def test_lot_en_echec_rapport_minimal(tmp_path):
    lot = generer_lot(tmp_path / "lot", defauts=["sha_incorrect"])
    r = simuler(lot.dossier, lot.sha_manifest, autoriser_fictif=True)
    assert r["statut"] == "FAILED" and "metriques" not in r
    assert r["fichiers"]["C02/resultats.bin"] == {"etat": "FAILED", "raison": "empreinte_differente"}


def test_comparaison_avant_apres(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    a = generer_lot(tmp_path / "a", n_notions=10, lot_id="lot-synthetique-a")
    depot.publier(a.dossier, a.sha_manifest)
    b = generer_lot(tmp_path / "b", n_notions=12, lot_id="lot-synthetique-b", defauts=["provenance_falsifiee"])
    r = simuler(b.dossier, b.sha_manifest, depot=tmp_path / "depot", autoriser_fictif=True)
    c = r["comparaison"]
    assert c["notions"]["ajoutes"] == ["notion:synthetique:n10", "notion:synthetique:n11"]
    assert c["notions"]["retires"] == [] and c["notions"]["modifies"] == ["notion:synthetique:n0"]
    assert c["changements_de_preuve"] == [{"notion_id": "notion:synthetique:n0", "avant": "PROVEN",
                                           "apres": "QUARANTINED"}]
    assert not c["identique_au_lot_actif"]


def test_import_repete_detecte(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    a = generer_lot(tmp_path / "a", lot_id="lot-synthetique-a")
    depot.publier(a.dossier, a.sha_manifest)
    b = generer_lot(tmp_path / "b", lot_id="lot-synthetique-bis")  # même contenu, autre identifiant
    r = simuler(b.dossier, b.sha_manifest, depot=tmp_path / "depot", autoriser_fictif=True)
    assert r["comparaison"]["identique_au_lot_actif"] and r["avertissements"] == ["LOT_IDENTIQUE_AU_LOT_ACTIF"]


def test_rapport_deterministe(tmp_path):
    lot = generer_lot(tmp_path / "lot", defauts=["mapping_contradictoire"])
    r1 = simuler(lot.dossier, lot.sha_manifest, autoriser_fictif=True)
    r2 = simuler(lot.dossier, lot.sha_manifest, autoriser_fictif=True)
    assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)
    assert "Quarantaine" in en_markdown(r1)


def test_outil_simuler_puis_publier(tmp_path, capsys):
    from tools.import_lot import main

    lot = generer_lot(tmp_path / "lot")
    base = ["--dossier", str(lot.dossier), "--sha", lot.sha_manifest, "--autoriser-fictif"]
    assert main(["simuler", *base, "--sortie", str(tmp_path / "r")]) == 0
    assert (tmp_path / "r" / "rapport_import.json").exists() and (tmp_path / "r" / "rapport_import.md").exists()
    assert main(["publier", *base, "--depot", str(tmp_path / "depot")]) == 2  # --confirmer manquant
    assert not (tmp_path / "depot" / "ACTIF.json").exists()
    assert main(["publier", *base, "--depot", str(tmp_path / "depot"), "--confirmer"]) == 0
    assert (tmp_path / "depot" / "ACTIF.json").exists()
    mauvais = generer_lot(tmp_path / "m", defauts=["document_altere"])
    assert main(["simuler", "--dossier", str(mauvais.dossier), "--sha", mauvais.sha_manifest]) == 1
    assert main(["publier", "--dossier", str(mauvais.dossier), "--sha", mauvais.sha_manifest, "--depot",
                 str(tmp_path / "depot"), "--confirmer"]) == 1
