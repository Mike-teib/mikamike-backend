"""
Chapitrage (lot 8) : un rattachement notion → chapitre n'est PROUVÉ que par la structure du
document source. Tests adversariaux : même mot dans deux chapitres, cellule de tableau, titre
de colonne, prérequis, annexe, sommaire, page multi-colonnes, autre document, hors zone.
"""

import json

import pytest

from app.curriculum import importers
from app.curriculum.chapitrage import PreuveChapitre, StructureDocument, Verdict as V, evaluer
from app.curriculum.harnais_import import generer_lot

SHA = "a" * 64
A, B = "chap:test:a", "chap:test:b"
STRUCT = StructureDocument.model_validate({
    "sha256_document": SHA, "sommaire_pages": [2], "annexes": [{"page_debut": 20, "page_fin": 25}],
    "zones_prerequis": [{"page": 4, "y0": 50, "y1": 150}],
    "chapitres": [
        {"chapitre_id": A, "page_debut": 3, "page_fin": 5, "colonnes": [{"page": 5, "x0": 0, "x1": 300}]},
        {"chapitre_id": B, "page_debut": 5, "page_fin": 8, "colonnes": [{"page": 5, "x0": 300, "x1": 600}]},
    ]})


def P(**kw):
    base = {"type": "section_pdf", "sha256_document": SHA, "page": 3, "bbox": [50, 200, 250, 220]}
    base.update(kw)
    return PreuveChapitre.model_validate(base)


@pytest.mark.parametrize("preuves,declare,verdict,ecartee", [
    ([P()], A, V.PROUVE, None),
    ([P(page=7)], B, V.PROUVE, None),
    # même mot dans deux chapitres : la proximité lexicale n'est jamais une preuve
    ([P(type="proximite_lexicale", page=3), P(type="proximite_lexicale", page=7)], A, V.NON_PROUVE,
     "preuve_lexicale_insuffisante"),
    ([P(type="tableau_officiel", cellule={"ligne": 2, "colonne": "Connaissances"})], A, V.PROUVE, None),
    ([P(type="tableau_officiel", cellule={"ligne": 0, "colonne": "Attendus de fin de cycle"})], A, V.NON_PROUVE,
     "preuve_titre_de_colonne"),
    ([P(type="tableau_officiel")], A, V.NON_PROUVE, "cellule_manquante"),
    ([P(page=4, bbox=[50, 60, 250, 100])], A, V.NON_PROUVE, "preuve_dans_les_prerequis"),
    ([P(page=4, bbox=[50, 300, 250, 320])], A, V.PROUVE, None),  # même page, hors zone de prérequis
    ([P(page=21)], A, V.NON_PROUVE, "preuve_en_annexe"),
    ([P(page=2)], A, V.NON_PROUVE, "preuve_dans_le_sommaire"),
    ([P(type="sommaire", page=2)], A, V.NON_PROUVE, "sommaire_seul"),
    ([P(page=5, bbox=[350, 100, 500, 120])], A, V.CONTRADICTOIRE, None),   # colonne de B
    ([P(page=5, bbox=[50, 100, 200, 120])], A, V.PROUVE, None),            # colonne de A
    ([P(page=5, bbox=[250, 100, 400, 120])], A, V.NON_PROUVE, "hors_zone_de_chapitre"),  # à cheval
    ([P(page=5, bbox=None)], A, V.NON_PROUVE, "coordonnees_requises_page_multicolonne"),
    ([P(), P(page=7)], A, V.AMBIGU, None),
    ([P(sha256_document="b" * 64)], A, V.NON_PROUVE, "autre_document"),
    ([P(page=15)], A, V.NON_PROUVE, "hors_zone_de_chapitre"),
    ([], A, V.DECLARE, None),
])
def test_rattachement(preuves, declare, verdict, ecartee):
    r = evaluer(declare, preuves, STRUCT)
    assert r.verdict == verdict, r
    if ecartee:
        assert ecartee in r.ecartees


def test_sans_structure_jamais_prouve():
    assert evaluer(A, [P()], None).verdict == V.NON_PROUVE


def test_structure_incoherente_refusee_a_l_import(tmp_path):
    lot = generer_lot(tmp_path / "lot")
    s = json.loads((lot.dossier / "structure.json").read_text("utf-8"))
    s["chapitres"][0]["page_fin"] = 0  # hors bornes (validation de schéma)
    (lot.dossier / "structure.json").write_text(json.dumps(s), "utf-8")
    m = json.loads((lot.dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))
    for f in m["fichiers"]:
        if f["chemin"] == "structure.json":
            f["sha256"] = importers.sha256_fichier(lot.dossier / "structure.json")
            f["taille"] = (lot.dossier / "structure.json").stat().st_size
    brut = json.dumps(m).encode()
    (lot.dossier / "IMPORT_MANIFEST.json").write_bytes(brut)
    import hashlib

    res = importers.importer(lot.dossier, sha256_manifest=hashlib.sha256(brut).hexdigest(), autoriser_fictif=True)
    assert res.statut == "FAILED" and res.fichiers["structure.json"]["etat"] == "FAILED"


def test_import_harnais_rattachements_prouves(tmp_path):
    lot = generer_lot(tmp_path / "lot")
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    assert res.statut == "VALIDATED" and set(res.rattachements.values()) == {"PROUVE"}


@pytest.mark.parametrize("defaut,code", [("chapitrage_lexical", "RATTACHEMENT_NON_PROUVE"),
                                         ("chapitrage_contradictoire", "RATTACHEMENT_CONTRADICTOIRE")])
def test_import_rattachement_non_prouve_rejete(tmp_path, defaut, code):
    lot = generer_lot(tmp_path / "lot", defauts=[defaut])
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True)
    assert res.statut == "REJECTED" and code in {a.code for a in res.anomalies}
    assert "notion:synthetique:n0" not in res.integrite.generables


def test_mapping_sans_preuve_reste_declare(tmp_path):
    from tests_cloud.test_import_v2_integrite import _lot

    sha = _lot(tmp_path / "lot")
    res = importers.importer(tmp_path / "lot", sha256_manifest=sha, autoriser_fictif=True)
    assert set(res.rattachements.values()) <= {"DECLARE", "NON_PROUVE"}
