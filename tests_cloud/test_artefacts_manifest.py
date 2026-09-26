"""
Session 5 — ARTIFACTS_REQUIRED_MANIFEST.json : cohérent avec l'importeur, aucune donnée inventée,
outil de présence (WAITING_FOR_ARTIFACT sur ce seul lot, sans bloquer le reste).
"""

import json
import re

import pytest

from app.curriculum.harnais_import import generer_lot
from app.curriculum.importers import ROLES
from tools import artefacts

REQUIS = json.loads(artefacts.REQUIS.read_text("utf-8"))
ATTENDUS = {"C02", "C02-6", "C02-6.1", "M01", "EXTRACTION_V3", "PDF_OFFICIELS"}
CHAMPS = {"id", "nom", "version", "sha256_attendu", "format", "role_manifest", "types_admis",
          "chemin_recommande", "importeur", "validation", "sortie", "bloquant_si_absent", "statut"}


def test_tous_les_artefacts_attendus_et_champs_complets():
    assert {a["id"] for a in REQUIS["artefacts"]} == ATTENDUS
    for a in REQUIS["artefacts"]:
        assert set(a) == CHAMPS, a["id"]


@pytest.mark.parametrize("a", REQUIS["artefacts"] + REQUIS["complements_attendus"], ids=lambda a: a["id"])
def test_roles_et_types_alignes_sur_l_importeur(a):
    for role in artefacts._roles(a):
        assert role in ROLES, role
        assert set(a["types_admis"]) == set(ROLES[role]), (a["id"], role)


def test_aucune_empreinte_inventee():
    for a in REQUIS["artefacts"]:
        sha = a["sha256_attendu"]
        assert sha is None or re.fullmatch(r"[0-9a-f]{64}", sha)
        assert a["statut"] == "WAITING_FOR_ARTIFACT"  # rien n'est dans le dépôt


def test_aucun_artefact_reel_dans_le_depot():
    racine = artefacts.RACINE
    suspects = [p for p in racine.rglob("*") if ".venv" not in p.parts and ".git" not in p.parts
                and p.suffix.lower() in (".pdf", ".xlsx") and "tests" not in p.name]
    assert suspects == []


def test_dossier_absent_tout_en_attente(tmp_path, capsys):
    assert artefacts.main(["verifier", "--dossier", str(tmp_path)]) == 4
    sortie = json.loads(capsys.readouterr().out)
    assert {v["statut"] for v in sortie["artefacts"].values()} == {"WAITING_FOR_ARTIFACT"}


def test_lot_synthetique_roles_reconnus(tmp_path, capsys):
    generer_lot(tmp_path / "lot")
    code = artefacts.main(["verifier", "--dossier", str(tmp_path / "lot")])
    res = json.loads(capsys.readouterr().out)["artefacts"]
    for ident in ("C02", "C02-6", "C02-6.1", "M01", "EXTRACTION_V3", "PDF_OFFICIELS"):
        assert res[ident]["statut"] == "PRESENT", (ident, res[ident])
    assert code == 0


def test_empreinte_epinglee_differente(tmp_path, capsys):
    generer_lot(tmp_path / "lot")
    requis = json.loads(json.dumps(REQUIS))
    requis["artefacts"][0]["sha256_attendu"] = "0" * 64
    p = tmp_path / "requis.json"
    p.write_text(json.dumps(requis))
    assert artefacts.main(["verifier", "--dossier", str(tmp_path / "lot"), "--requis", str(p)]) == 3
    assert json.loads(capsys.readouterr().out)["artefacts"]["C02"]["statut"] == "SHA_DIFFERENT"


def test_usage_invalide():
    assert artefacts.main(["importer"]) == 2
