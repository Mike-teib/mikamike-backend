"""
Harnais d'import sur lots SYNTHÉTIQUES (app/curriculum/harnais_import.py, IMPORT_TEST_HARNESS_REPORT.md).

Aucun artefact réel n'est utilisé ni inventé : sources `fictive=True`, contenus marqués
[SYNTHÉTIQUE]. Pipeline : manifest → C02 → C02-6 → C02-6.1 → M01 → Extraction V3 → PDF →
provenance → mapping → backlog.
"""

import json
import shutil

import pytest

from app.curriculum import importers
from app.curriculum.depot import PROFONDEUR_HISTORIQUE, DepotContenu, DepotInvalide
from app.curriculum.harnais_import import DEFAUTS, ETAPES, MARQUE, executer_pipeline, generer_lot


@pytest.fixture()
def lot(tmp_path):
    return generer_lot(tmp_path / "lot")


# --------------------------------------------------------------------------- #
# Pipeline nominal
# --------------------------------------------------------------------------- #
def test_pipeline_nominal_toutes_les_etapes(lot):
    rap = executer_pipeline(lot.dossier, lot.sha_manifest)
    assert rap.statut == "VALIDATED", rap.etapes
    noms = [e[0] for e in rap.etapes]
    assert noms == ["manifest", *ETAPES, "provenance", "mapping", "backlog"]
    assert all(e[1] in ("OK", "DONE") for e in rap.etapes), rap.etapes
    assert rap.backlog["total"]["PROVEN"] == lot.n_notions  # en mode TEST (source fictive autorisée)
    assert all(n.chapitre_id for n in rap.resultat.referentiel.notions)  # mapping appliqué
    roles = {o.get("role") for o in rap.resultat.opaques}
    assert {"c02", "c02_6", "extraction_v3"} <= roles  # formats inconnus : restés OPAQUES


def test_ordre_du_pipeline_respecte(lot):
    m = json.loads((lot.dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))
    assert [f["role"] for f in m["fichiers"]] == list(ETAPES)
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    assert list(res.fichiers) == [f["chemin"] for f in m["fichiers"]]  # traitement séquentiel, dans l'ordre


def test_lot_synthetique_refuse_hors_mode_test(lot):
    """S3-15 : un lot à source fictive n'est jamais VALIDATED (donc jamais publiable) en production."""
    rap = executer_pipeline(lot.dossier, lot.sha_manifest, autoriser_fictif=False)
    assert rap.statut == "REJECTED"
    assert "SOURCE_FICTIVE_HORS_TEST" in {a.code for a in rap.resultat.anomalies}
    assert rap.backlog["total"]["NEED_EXERCISE"] == 0
    res = DepotContenu(lot.dossier.parent / "depot").publier(lot.dossier, lot.sha_manifest)
    assert res.statut == "REJECTED" and not (lot.dossier.parent / "depot" / "ACTIF.json").exists()


def test_tout_est_marque_synthetique(lot):
    for f in lot.dossier.rglob("*"):
        if f.is_file() and f.suffix in (".jsonl", ".json", ".bin", ".pdf") and f.name != "IMPORT_MANIFEST.json":
            brut = f.read_bytes()
            assert MARQUE.encode() in brut or b"synthetique" in brut or not brut, f.name


# --------------------------------------------------------------------------- #
# Défauts injectés : chacun est arrêté à la BONNE étape
# --------------------------------------------------------------------------- #
ATTENDU = {
    "sha_incorrect": ("FAILED", "c02", "empreinte_differente"),
    "fichier_manquant": ("FAILED", "mapping_chapitre_notion", "fichier_manquant"),
    "fichier_non_liste": ("FAILED", "manifest", "fichiers_non_listes"),
    "doublon_notion": ("FAILED", "m01_maths_cycle3", "notion_dupliquee"),
    "doublon_manifest": ("FAILED", "manifest", "fichier_liste_deux_fois"),
    "doublon_contenu": ("FAILED", "c02_6_1", "schema_invalide"),
    "mauvais_role": ("FAILED", "manifest", "role_incompatible"),
    "document_altere": ("FAILED", "source_pdf", "empreinte_differente"),
    "json_invalide": ("FAILED", "extraction_v3", ""),
    "provenance_falsifiee": ("REJECTED", "provenance", "HASH_EXTRAIT_INCOHERENT"),
    "mapping_contradictoire": ("REJECTED", "mapping", "MAPPING_CONTRADICTOIRE"),
    "mapping_notion_inconnue": ("REJECTED", "mapping", "MAPPING_NOTION_INCONNUE"),
    "chapitrage_lexical": ("REJECTED", "mapping", "RATTACHEMENT_NON_PROUVE"),
    "chapitrage_contradictoire": ("REJECTED", "mapping", "RATTACHEMENT_CONTRADICTOIRE"),
}


def test_chaque_defaut_a_un_attendu():
    assert set(ATTENDU) == DEFAUTS


@pytest.mark.parametrize("defaut", sorted(DEFAUTS))
def test_defaut_arrete_a_la_bonne_etape(tmp_path, defaut):
    statut, etape, raison = ATTENDU[defaut]
    lot = generer_lot(tmp_path / defaut, defauts=[defaut])
    rap = executer_pipeline(lot.dossier, lot.sha_manifest)
    assert rap.statut == statut, rap.etapes
    detail = next(d for n, e, d in rap.etapes if n == etape and e in ("FAILED", "ANOMALIE"))
    assert raison in detail
    # Aucune autre étape n'échoue « par contagion » (diagnostic précis).
    autres = [e for e in rap.etapes if e[1] in ("FAILED", "ANOMALIE") and e[0] != etape]
    assert autres == [], autres


@pytest.mark.parametrize("defaut", sorted(DEFAUTS))
def test_defaut_jamais_publie(tmp_path, defaut):
    lot = generer_lot(tmp_path / defaut, defauts=[defaut])
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    try:
        res = depot.publier(lot.dossier, lot.sha_manifest)
        assert res.statut != "VALIDATED"
    except DepotInvalide:
        pass
    assert depot.actif() is None and not (tmp_path / "depot" / "lots").exists() or \
        not any((tmp_path / "depot" / "lots").iterdir())


def test_manifest_regenere_apres_falsification_refuse(lot):
    # L'attaquant modifie C02 ET régénère le manifest : l'empreinte épinglée hors bande le trahit.
    (lot.dossier / "C02" / "resultats.bin").write_bytes(b"falsifie")
    m = json.loads((lot.dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))
    m["fichiers"][0]["sha256"] = importers.sha256_fichier(lot.dossier / "C02" / "resultats.bin")
    (lot.dossier / "IMPORT_MANIFEST.json").write_text(json.dumps(m), "utf-8")
    rap = executer_pipeline(lot.dossier, lot.sha_manifest)
    assert rap.statut == "FAILED" and rap.etat("manifest") == "FAILED"


# --------------------------------------------------------------------------- #
# Import partiel, reprise, idempotence
# --------------------------------------------------------------------------- #
def test_import_partiel_jamais_valide(tmp_path, lot):
    """Un seul fichier FAILED ⇒ tout le lot FAILED : les étapes réussies ne sont pas publiées."""
    (lot.dossier / "mapping.jsonl").write_text("", "utf-8")  # contenu modifié ⇒ empreinte différente
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True,
                             checkpoint=tmp_path / "ck.json")
    assert res.statut == "FAILED" and res.referentiel is None
    etats = {k: v["etat"] for k, v in res.fichiers.items()}
    assert etats["mapping.jsonl"] == "FAILED" and list(etats.values()).count("DONE") == len(ETAPES) - 1


def test_reprise_apres_interruption(tmp_path, lot, monkeypatch):
    ck = tmp_path / "ck.json"
    orig = importers.sha256_fichier

    def coupure(chemin):
        if chemin.name == "bo_synthetique.pdf":
            raise KeyboardInterrupt("coupure simulee")
        return orig(chemin)

    monkeypatch.setattr(importers, "sha256_fichier", coupure)
    with pytest.raises(KeyboardInterrupt):
        importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True, checkpoint=ck)
    etat = json.loads(ck.read_text("utf-8"))
    assert len(etat) == 5 and all(v["etat"] == "DONE" for v in etat.values())  # 5 étapes avant le PDF
    monkeypatch.setattr(importers, "sha256_fichier", orig)
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True, checkpoint=ck)
    assert res.statut == "VALIDATED"
    assert [v["reprise"] for v in res.fichiers.values()].count("true") == 5


def test_checkpoint_d_un_autre_contenu_ignore(tmp_path, lot):
    ck = tmp_path / "ck.json"
    ck.write_text(json.dumps({"C02/resultats.bin": {"etat": "DONE", "sha256": "0" * 64}}), "utf-8")
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True, checkpoint=ck)
    assert res.statut == "VALIDATED" and res.fichiers["C02/resultats.bin"]["reprise"] == "false"


def test_import_idempotent(lot):
    r1 = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    r2 = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    assert r1.statut == r2.statut == "VALIDATED"
    assert r1.referentiel == r2.referentiel and r1.anomalies == r2.anomalies and r1.opaques == r2.opaques


# --------------------------------------------------------------------------- #
# Dépôt : publication idempotente, reprise, rollback, historique borné (S3-16)
# --------------------------------------------------------------------------- #
def test_republication_du_lot_actif_sans_effet(tmp_path, lot):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    assert depot.publier(lot.dossier, lot.sha_manifest).statut == "VALIDATED"
    actif = depot.actif()
    with pytest.raises(DepotInvalide, match="lot_deja_publie"):  # 2e fois : refus, rien ne bouge
        depot.publier(lot.dossier, lot.sha_manifest)
    assert depot.actif() == actif
    lignes = (tmp_path / "depot" / "HISTORIQUE.jsonl").read_text("utf-8").splitlines()
    assert len(lignes) == 1


def test_publication_coupee_puis_reprise(tmp_path, lot, monkeypatch):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    monkeypatch.setattr(DepotContenu, "_activer", lambda *a, **k: (_ for _ in ()).throw(OSError("coupure")))
    with pytest.raises(OSError):
        depot.publier(lot.dossier, lot.sha_manifest)
    assert depot.actif() is None and any((tmp_path / "depot" / "lots").iterdir())  # copié, pas activé
    monkeypatch.undo()
    assert depot.publier(lot.dossier, lot.sha_manifest).statut == "VALIDATED"
    assert depot.actif()["lot"].startswith("lot-synthetique-1")
    assert depot.charger_actif().statut == "VALIDATED"


def test_reprise_refusee_si_copie_alteree(tmp_path, lot, monkeypatch):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    monkeypatch.setattr(DepotContenu, "_activer", lambda *a, **k: (_ for _ in ()).throw(OSError("coupure")))
    with pytest.raises(OSError):
        depot.publier(lot.dossier, lot.sha_manifest)
    monkeypatch.undo()
    copie = next((tmp_path / "depot" / "lots").iterdir())
    (copie / "C02" / "resultats.bin").write_bytes(b"altere sur le disque de destination")
    with pytest.raises(DepotInvalide, match="copie_existante_invalide"):
        depot.publier(lot.dossier, lot.sha_manifest)
    assert depot.actif() is None


def test_rollback_multi_niveaux_et_historique_borne(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    noms = []
    for i in range(PROFONDEUR_HISTORIQUE + 5):
        lot = generer_lot(tmp_path / f"l{i}", n_notions=2, lot_id=f"lot-synthetique-{i}", graine=str(i))
        depot.publier(lot.dossier, lot.sha_manifest)
        noms.append(depot.actif()["lot"])
    etat, profondeur = depot.actif(), 0
    while etat.get("precedent"):
        etat, profondeur = etat["precedent"], profondeur + 1
    assert profondeur == PROFONDEUR_HISTORIQUE
    assert depot.rollback() == noms[-2]
    assert depot.rollback() == noms[-3]
    assert depot.charger_actif().statut == "VALIDATED"


def test_actif_json_profondement_imbrique_refus_controle(tmp_path):
    racine = tmp_path / "depot"
    racine.mkdir()
    (racine / "ACTIF.json").write_text('{"lot": "x", "sha256_manifest": "0", "precedent": ' * 5000 + "null" + "}" * 5000,
                                       "utf-8")
    with pytest.raises(DepotInvalide):
        DepotContenu(racine).actif()


def test_rollback_vers_lot_altere_refuse(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    l1 = generer_lot(tmp_path / "l1", lot_id="lot-synthetique-a", graine="a")
    l2 = generer_lot(tmp_path / "l2", lot_id="lot-synthetique-b", graine="b")
    depot.publier(l1.dossier, l1.sha_manifest)
    depot.publier(l2.dossier, l2.sha_manifest)
    prec = tmp_path / "depot" / "lots" / depot.actif()["precedent"]["lot"]
    shutil.rmtree(prec / "C02")
    with pytest.raises(DepotInvalide, match="lot_precedent_invalide"):
        depot.rollback()
    assert depot.actif()["lot"].startswith("lot-synthetique-b")  # rien n'a bougé


@pytest.mark.parametrize("defaut", ["mapping_contradictoire", "mapping_notion_inconnue", "chapitrage_contradictoire"])
def test_s4_01_notion_touchee_par_anomalie_d_import_non_generable(tmp_path, defaut):
    """S4-01 : une anomalie relevée par l'IMPORTEUR (mapping, chapitrage) doit retirer sa notion
    des générables (avant : seules les anomalies de verifier_integrite étaient déduites)."""
    lot = generer_lot(tmp_path / defaut, defauts=[defaut])
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    touchees = {a.objet_id for a in res.anomalies}
    assert touchees and not (touchees & res.integrite.generables)
