"""
Garde de publication (lot 30) : READY_FOR_PUBLICATION ≠ PUBLISHED, chaque condition isolée.
Données FICTIVES (fixtures du dépôt) ; « production » simulée avec une source non fictive
dont le document (synthétique) est fourni dans le lot.
"""

import dataclasses

import pytest

from app.curriculum.depot import DepotContenu
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.ids import sha256_octets
from app.curriculum.importers import importer
from app.curriculum.publication import (
    EtatPublication as E,
    PublicationRefusee,
    RegistrePublication,
    catalogue_publie,
    evaluer,
)
from app.curriculum.structure import Anomalie
from tests_cloud.test_import_v2_integrite import PDF, _exo, _lot

EXO, QUIZ = "exo:fictif:v2-1", "quiz:fictif:v2-1"


def _ref_non_fictif():
    ref = referentiel_fictif()
    src = ref.sources[0].model_copy(update={"fictive": False, "sha256_document": sha256_octets(PDF)})
    return ref.model_copy(update={"sources": (src,)})


@pytest.fixture()
def res_prod(tmp_path):
    sha = _lot(tmp_path / "lot", ref=_ref_non_fictif())
    res = importer(tmp_path / "lot", sha256_manifest=sha)
    assert res.statut == "VALIDATED", res.anomalies
    return res


def test_contenu_valide_pret_mais_pas_publie(res_prod):
    ev = evaluer(res_prod)
    assert ev[EXO].etat == E.READY_FOR_PUBLICATION and ev[EXO].raisons == ()
    assert ev[QUIZ].etat == E.READY_FOR_PUBLICATION


def test_publication_explicite_puis_catalogue(res_prod, tmp_path):
    reg = RegistrePublication(tmp_path / "depot")
    assert catalogue_publie(res_prod, reg).exercices == {}  # rien n'est servi avant publication
    ev = reg.publier(res_prod, EXO, "operateur.mike")
    assert ev.etat == E.PUBLISHED
    assert evaluer(res_prod, reg.publies())[EXO].etat == E.PUBLISHED
    assert evaluer(res_prod, reg.publies())[QUIZ].etat == E.READY_FOR_PUBLICATION
    cat = catalogue_publie(res_prod, reg)
    assert set(cat.exercices) == {EXO} and cat.obtenir(EXO)
    ligne = (tmp_path / "depot" / "PUBLICATIONS.jsonl").read_text("utf-8")
    assert "operateur.mike" in ligne and '"action": "publier"' in ligne


def test_contenu_modifie_redevient_seulement_pret(res_prod, tmp_path):
    reg = RegistrePublication(tmp_path / "depot")
    reg.publier(res_prod, EXO, "operateur.mike")
    modifie = dataclasses.replace(res_prod, exercices=[res_prod.exercices[0].model_copy(update={"difficulte": 3})])
    assert evaluer(modifie, reg.publies())[EXO].etat == E.READY_FOR_PUBLICATION


def test_retrait(res_prod, tmp_path):
    reg = RegistrePublication(tmp_path / "depot")
    reg.publier(res_prod, EXO, "operateur.mike")
    reg.retirer(EXO, "operateur.mike")
    assert evaluer(res_prod, reg.publies())[EXO].etat == E.READY_FOR_PUBLICATION


def _variante(res, **kw):
    return dataclasses.replace(res, **kw)


def _ref_modifiee(res, notion_update=None, chapitre_update=None):
    ref = res.referentiel
    notions = tuple(n.model_copy(update=notion_update) if n.id == res.exercices[0].notion_id and notion_update else n
                    for n in ref.notions)
    chapitres = tuple(c.model_copy(update=chapitre_update) if chapitre_update else c for c in ref.chapitres)
    return ref.model_copy(update={"notions": notions, "chapitres": chapitres})


@pytest.mark.parametrize("cas,raison", [
    ("lot_rejete", "LOT_NON_VALIDE"),
    ("source_fictive", "SOURCE_NON_PROUVEE"),
    ("document_absent", "SOURCE_NON_PROUVEE"),
    ("notion_non_generable", "NOTION_NON_PROUVEE"),
    ("texte_tronque", "TEXTE_NON_SAIN"),
    ("enonce_tronque", "TEXTE_NON_SAIN"),
    ("sans_chapitre", "CHAPITRE_NON_PROUVE"),
    ("chapitre_ambigu", "CHAPITRE_NON_PROUVE"),
    ("anomalie_structure", "STRUCTURE_INVALIDE"),
    ("reponse_invérifiable", "VALIDATION_ECHOUEE"),
    ("plan_manquant", "PLAN_MANQUANT"),
])
def test_chaque_condition_bloque(res_prod, cas, raison, tmp_path):
    r = res_prod
    if cas == "lot_rejete":
        r = _variante(r, statut="REJECTED")
    elif cas == "source_fictive":
        src = r.referentiel.sources[0].model_copy(update={"fictive": True})
        r = _variante(r, referentiel=r.referentiel.model_copy(update={"sources": (src,)}))
    elif cas == "document_absent":
        r = _variante(r, documents={})
    elif cas == "notion_non_generable":
        r = _variante(r, integrite=r.integrite._replace(generables=frozenset()))
    elif cas == "texte_tronque":
        r = _variante(r, referentiel=_ref_modifiee(r, {"texte": "[FICTIF] Utiliser l'écriture fractionnaire des"}))
    elif cas == "enonce_tronque":
        r = _variante(r, exercices=[r.exercices[0].model_copy(update={"enonce": "Écris 7/10 sous la forme des"})])
    elif cas == "sans_chapitre":
        r = _variante(r, referentiel=_ref_modifiee(r, {"chapitre_id": None}))
    elif cas == "chapitre_ambigu":
        r = _variante(r, referentiel=_ref_modifiee(r, chapitre_update={"ambigu": True}))
    elif cas == "anomalie_structure":
        r = _variante(r, anomalies=[Anomalie("TEST", r.exercices[0].notion_id, "")])
    elif cas == "reponse_invérifiable":
        r = _variante(r, exercices=[r.exercices[0].model_copy(update={"type_verification": "inconnu"})])
    elif cas == "plan_manquant":
        r = _variante(r, plans={})
    ev = evaluer(r)[EXO]
    assert ev.etat == E.BLOQUE and raison in ev.raisons, ev
    with pytest.raises(PublicationRefusee, match="contenu_non_pret"):
        RegistrePublication(tmp_path / "d").publier(r, EXO, "operateur.mike")


def test_fixture_fictive_bloquee_hors_mode_test(tmp_path):
    sha = _lot(tmp_path / "lot")
    res = importer(tmp_path / "lot", sha256_manifest=sha, autoriser_fictif=True)
    assert evaluer(res)[EXO].etat == E.BLOQUE  # sans autoriser_fictif : jamais publiable
    assert evaluer(res, autoriser_fictif=True)[EXO].etat == E.READY_FOR_PUBLICATION


@pytest.mark.parametrize("operateur", ["", "Mike Toumerte", "a", "x" * 70, "op;rm -rf"])
def test_operateur_nomme_obligatoire(res_prod, tmp_path, operateur):
    with pytest.raises(PublicationRefusee, match="operateur_invalide"):
        RegistrePublication(tmp_path / "d").publier(res_prod, EXO, operateur)


def test_journal_corrompu_refuse(res_prod, tmp_path):
    reg = RegistrePublication(tmp_path / "d")
    reg.publier(res_prod, EXO, "operateur.mike")
    with reg.fichier.open("a", encoding="utf-8") as f:
        f.write("{corrompu\n")
    with pytest.raises(PublicationRefusee, match="corrompu"):
        reg.publies()


def test_depot_puis_publication_de_bout_en_bout(tmp_path):
    sha = _lot(tmp_path / "lot", ref=_ref_non_fictif(), exos=[_exo()])
    depot = DepotContenu(tmp_path / "depot")
    assert depot.publier(tmp_path / "lot", sha).statut == "VALIDATED"
    res = depot.charger_actif()
    reg = RegistrePublication(tmp_path / "depot")
    reg.publier(res, EXO, "operateur.mike")
    assert set(catalogue_publie(res, reg).exercices) == {EXO}


def test_outil_operateur(tmp_path, capsys):
    from tools.publication import main

    sha = _lot(tmp_path / "lot", ref=_ref_non_fictif())
    DepotContenu(tmp_path / "depot").publier(tmp_path / "lot", sha)
    d = str(tmp_path / "depot")
    assert main(["etat", "--depot", d]) == 0 and "READY_FOR_PUBLICATION" in capsys.readouterr().out
    assert main(["publier", EXO, "--depot", d]) == 2
    assert main(["publier", EXO, "--depot", d, "--operateur", "operateur.mike"]) == 0
    assert "PUBLISHED" in capsys.readouterr().out
    assert main(["publier", "inconnu", "--depot", d, "--operateur", "operateur.mike"]) == 1
    assert main(["etat", "--depot", str(tmp_path / "vide")]) == 1
