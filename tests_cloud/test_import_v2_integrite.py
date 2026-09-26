"""
Import v2 (IMPORT_CONTRACT.md), intégrité croisée, backlog hiérarchique, dépôt/rollback.
Toutes les données sont FICTIVES (fixtures « [FICTIF] », domaine example.invalid).
"""

import json
import shutil
from pathlib import Path

import pytest

from app.curriculum.backlog import calculer_backlog, en_markdown
from app.curriculum.depot import DepotContenu, DepotInvalide, catalogue_depuis_import
from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.ids import sha256_octets, sha256_texte
from app.curriculum.importers import ecrire_manifest_v2, importer, sha256_fichier
from app.curriculum.integrite import IntegriteNonDemontree, exiger_integrite, verifier_integrite
from app.curriculum.model import SourceOfficielle, StatutTexte
from app.curriculum.pedagogie.tuteur import PlanGuidage
from app.curriculum.quiz import QuestionQuiz

N1 = "notion:fictif:comparer-fractions"
N2 = "notion:fictif:fractions-decimales"
N3 = "notion:fictif:sans-preuve"
PDF = b"%PDF-1.4\n% [FICTIF] document de test, aucun contenu officiel\n"


def _exo(nid=N2, **kw):
    n = referentiel_fictif().index().notions[nid]
    base = dict(id="exo:fictif:v2-1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                programme_id=n.programme_id, chapitre_id=n.chapitre_id or "chap:fictif:fractions-6e",
                difficulte=2, objectif_pedagogique="[FICTIF] objectif", prerequis=tuple(n.prerequis),
                enonce="Écris 7/10 sous forme décimale.", reponse_attendue="0,7",
                type_verification="maths_symbolique", indices=("Lis la fraction.",),
                source_sha256_extrait=n.preuve.sha256_extrait if n.preuve else "0" * 64)
    base.update(kw)
    return Exercice(**base)


def _quiz(**kw):
    n = referentiel_fictif().index().notions[N1]
    base = dict(id="quiz:fictif:v2-1", notion_id=N1, matiere=n.matiere, niveau=n.niveau,
                enonce="[FICTIF] Quelle fraction est la plus grande ?", choix=("3/7", "2/7", "1/7"),
                index_correct=0, reponse_reference="3/7", type_verification="maths_symbolique",
                explication="[FICTIF] Même dénominateur : on compare les numérateurs.")
    base.update(kw)
    return QuestionQuiz(**base)


PLAN = PlanGuidage(questions_intermediaires=("Que représente le 10 ?",),
                   question_comprehension="Et 9/10 ?", reponse_comprehension="0,9",
                   correction_commentee="7/10 = 0,7.")


def _lot(dossier: Path, ref=None, exos=None, quiz=None, plans=None, *, pdf=PDF, extra=None,
         lot_id="lot-fictif-1") -> str:
    dossier.mkdir(parents=True, exist_ok=True)
    ref = ref or referentiel_fictif()
    exos = [_exo()] if exos is None else exos
    quiz = [_quiz()] if quiz is None else quiz
    plans = {"exo:fictif:v2-1": PLAN} if plans is None else plans
    (dossier / "ref.json").write_text(ref.model_dump_json(), "utf-8")
    (dossier / "contenus.jsonl").write_text("".join(
        json.dumps({"kind": "exercice", "data": e.model_dump(mode="json")}) + "\n" for e in exos) + "".join(
        json.dumps({"kind": "quiz", "data": q.model_dump(mode="json")}) + "\n" for q in quiz), "utf-8")
    (dossier / "plans.jsonl").write_text("".join(
        json.dumps({"exercice_id": k, "plan": p.model_dump(mode="json")}) + "\n" for k, p in plans.items()), "utf-8")
    (dossier / "sources").mkdir(exist_ok=True)
    (dossier / "sources" / "programme.pdf").write_bytes(pdf)
    (dossier / "SHA256_SOURCE.txt").write_text(f"{sha256_octets(pdf)}  sources/programme.pdf\n", "utf-8")
    (dossier / "c02_6_1.bin").write_bytes(b"[FICTIF] artefact C02-6.1 opaque")
    fichiers = {"ref.json": ("referentiel", "referentiel"), "contenus.jsonl": ("index_contenus", "index_exercices"),
                "plans.jsonl": ("plans_guidage", "plans_guidage"),
                "sources/programme.pdf": ("source_document", "source_pdf"),
                "SHA256_SOURCE.txt": ("manifest_sha256", "manifest_sha256"),
                "c02_6_1.bin": ("opaque", "c02_6_1"), **(extra or {})}
    return ecrire_manifest_v2(dossier, fichiers, lot_id=lot_id, producteur="[FICTIF] tests", date="2026-09-26")


def _manifest(d: Path) -> dict:
    return json.loads((d / "IMPORT_MANIFEST.json").read_text("utf-8"))


def _reecrire(d: Path, data: dict) -> str:
    (d / "IMPORT_MANIFEST.json").write_text(json.dumps(data), "utf-8")
    return sha256_fichier(d / "IMPORT_MANIFEST.json")


def _codes(res):
    return {a.code for a in res.anomalies}


# --------------------------------------------------------------------------- #
# Lot sain
# --------------------------------------------------------------------------- #
def test_lot_v2_sain_valide(tmp_path):
    sha = _lot(tmp_path / "lot")
    res = importer(tmp_path / "lot", sha256_manifest=sha, autoriser_fictif=True)
    assert res.statut == "VALIDATED", res.anomalies
    assert res.manifest["lot_id"] == "lot-fictif-1" and "exo:fictif:v2-1" in res.plans
    assert res.documents == {"sources/programme.pdf": sha256_octets(PDF)}
    assert {o["statut"] for o in res.opaques} == {"OPAQUE_A_MAPPER", "MANIFEST_VERIFIE"}
    assert res.integrite.demontree and N1 in res.integrite.generables and N3 not in res.integrite.generables


def test_lot_fictif_jamais_valide_hors_mode_test(tmp_path):
    sha = _lot(tmp_path / "lot")
    res = importer(tmp_path / "lot", sha256_manifest=sha)
    assert res.statut == "REJECTED"
    assert "EXERCICE_INVALIDE" in _codes(res) and not res.integrite.generables


def test_catalogue_du_tuteur_depuis_un_import(tmp_path):
    sha = _lot(tmp_path / "lot")
    cat = catalogue_depuis_import(importer(tmp_path / "lot", sha256_manifest=sha, autoriser_fictif=True),
                                  autoriser_fictif=True)
    ex, plan = cat.obtenir("exo:fictif:v2-1")
    assert ex.reponse_attendue == "0,7" and plan.reponse_comprehension == "0,9"


# --------------------------------------------------------------------------- #
# Manifest : épinglage, altération, SHA, tailles, rôles
# --------------------------------------------------------------------------- #
def test_manifest_v2_non_epingle_refuse(tmp_path):
    _lot(tmp_path / "lot")
    res = importer(tmp_path / "lot", autoriser_fictif=True)
    assert res.statut == "FAILED" and "non_epinglee" in res.fichiers["IMPORT_MANIFEST.json"]["raison"]


def test_manifest_altere_puis_regenere_refuse(tmp_path):
    d = tmp_path / "lot"
    sha = _lot(d)
    (d / "c02_6_1.bin").write_bytes(b"[FICTIF] artefact FALSIFIE")
    # L'attaquant régénère un manifest cohérent… mais l'empreinte épinglée hors bande diffère.
    data = _manifest(d)
    for f in data["fichiers"]:
        if f["chemin"] == "c02_6_1.bin":
            f["sha256"], f["taille"] = sha256_fichier(d / "c02_6_1.bin"), (d / "c02_6_1.bin").stat().st_size
    _reecrire(d, data)
    res = importer(d, sha256_manifest=sha, autoriser_fictif=True)
    assert res.statut == "FAILED" and res.fichiers["IMPORT_MANIFEST.json"]["raison"] == "empreinte_manifest_differente"


def test_sha_incorrect_fichier(tmp_path):
    d = tmp_path / "lot"
    sha = _lot(d)
    (d / "c02_6_1.bin").write_bytes(b"[FICTIF] modifie apres manifest")
    res = importer(d, sha256_manifest=sha, autoriser_fictif=True)
    assert res.statut == "FAILED" and res.fichiers["c02_6_1.bin"]["raison"] == "empreinte_differente"


def test_taille_incoherente(tmp_path):
    d = tmp_path / "lot"
    _lot(d)
    data = _manifest(d)
    data["fichiers"][0]["taille"] += 1
    res = importer(d, sha256_manifest=_reecrire(d, data), autoriser_fictif=True)
    assert res.statut == "FAILED" and "taille_differente" in json.dumps(res.fichiers)


@pytest.mark.parametrize("modif,raison", [
    (lambda m: m["fichiers"][0].update(role="role_inconnu"), "role_incompatible"),
    (lambda m: [f.update(role="c02") for f in m["fichiers"] if f["type"] == "source_document"], "role_incompatible"),
    (lambda m: m.update(lot_id="../evil"), "lot_id_invalide"),
    (lambda m: m.update(date="hier"), "date_invalide"),
    (lambda m: m.update(extra=1), "entete_manifest_v2_invalide"),
    (lambda m: m["fichiers"][0].update(taille="12"), "taille_manifest_invalide"),
    (lambda m: m["fichiers"][0].update(taille=True), "taille_manifest_invalide"),
    (lambda m: m["fichiers"][0].update(chemin="../../etc/passwd"), "chemin_hors_dossier"),
])
def test_manifest_v2_invalide(tmp_path, modif, raison):
    d = tmp_path / "lot"
    _lot(d)
    data = _manifest(d)
    modif(data)
    res = importer(d, sha256_manifest=_reecrire(d, data), autoriser_fictif=True)
    assert res.statut == "FAILED" and raison in res.fichiers["IMPORT_MANIFEST.json"]["raison"]


def test_manifest_sha256_du_corpus_incoherent(tmp_path):
    d = tmp_path / "lot"
    _lot(d)
    (d / "SHA256_SOURCE.txt").write_text("0" * 64 + "  sources/programme.pdf\n", "utf-8")
    data = _manifest(d)
    for f in data["fichiers"]:
        if f["chemin"] == "SHA256_SOURCE.txt":
            f["sha256"], f["taille"] = sha256_fichier(d / f["chemin"]), (d / f["chemin"]).stat().st_size
    res = importer(d, sha256_manifest=_reecrire(d, data), autoriser_fictif=True)
    assert res.statut == "FAILED" and "manifest_sha256_incoherent" in res.fichiers["SHA256_SOURCE.txt"]["raison"]


def test_symlink_hors_lot_refuse(tmp_path):
    d = tmp_path / "lot"
    _lot(d)
    secret = tmp_path / "hors_lot.txt"
    secret.write_text("[FICTIF] hors lot", "utf-8")
    (d / "lien.txt").symlink_to(secret)
    data = _manifest(d)
    data["fichiers"].append({"chemin": "lien.txt", "sha256": sha256_fichier(secret),
                             "taille": secret.stat().st_size, "type": "opaque", "role": "rapport"})
    res = importer(d, sha256_manifest=_reecrire(d, data), autoriser_fictif=True)
    assert res.statut == "FAILED" and "chemin_hors_dossier" in res.fichiers["IMPORT_MANIFEST.json"]["raison"]


# --------------------------------------------------------------------------- #
# Intégrité croisée
# --------------------------------------------------------------------------- #
def _source_reelle(ref, pdf=PDF):
    """Variante NON fictive de la source (toujours example.invalid) pour tester le contrôle documentaire."""
    src = ref.sources[0].model_copy(update={"fictive": False, "sha256_document": sha256_octets(pdf)})
    return ref.model_copy(update={"sources": (src,)})


def test_document_source_absent(tmp_path):
    ref = _source_reelle(referentiel_fictif(), pdf=b"%PDF autre document")
    sha = _lot(tmp_path / "lot", ref=ref)
    res = importer(tmp_path / "lot", sha256_manifest=sha)
    assert "SOURCE_DOCUMENT_ABSENT" in _codes(res) and not res.integrite.generables


def test_document_source_present_prouve(tmp_path):
    sha = _lot(tmp_path / "lot", ref=_source_reelle(referentiel_fictif()))
    res = importer(tmp_path / "lot", sha256_manifest=sha)
    assert "SOURCE_DOCUMENT_ABSENT" not in _codes(res)
    assert res.statut == "VALIDATED", res.anomalies


def _ref_modifie(nid, **maj):
    ref = referentiel_fictif()
    notions = tuple(n.model_copy(update=maj) if n.id == nid else n for n in ref.notions)
    return ref.model_copy(update={"notions": notions})


def test_texte_tronque_declare_exact(tmp_path):
    ref = _ref_modifie(N1, texte="[FICTIF] Comparer, ranger et encadrer des", statut_texte=StatutTexte.TEXT_EXACT)
    rap = verifier_integrite(ref, autoriser_fictif=True)
    assert any(a.code == "TEXTE_DECLARE_INCOHERENT" and a.objet_id == N1 for a in rap.anomalies)
    assert N1 not in rap.generables


def test_source_falsifiee_hash_extrait(tmp_path):
    n1 = referentiel_fictif().index().notions[N1]
    ref = _ref_modifie(N1, preuve=n1.preuve.model_copy(update={"extrait": n1.preuve.extrait + " [ajout]"}))
    rap = verifier_integrite(ref, autoriser_fictif=True)
    assert any(a.code == "HASH_EXTRAIT_INCOHERENT" for a in rap.anomalies) and N1 not in rap.generables


def test_preuve_d_un_autre_programme():
    ref = referentiel_fictif()
    autre = SourceOfficielle(id="src:fictif:autre", titre="[FICTIF] autre", editeur="tests",
                             url="https://example.invalid/autre.pdf", date_publication="2026-01-01",
                             sha256_document="2" * 64, fictive=True)
    n1 = ref.index().notions[N1]
    ref = ref.model_copy(update={"sources": ref.sources + (autre,), "notions": tuple(
        n.model_copy(update={"preuve": n1.preuve.model_copy(update={"source_id": autre.id, "url": autre.url})})
        if n.id == N1 else n for n in ref.notions)})
    rap = verifier_integrite(ref, autoriser_fictif=True)
    assert any(a.code == "PREUVE_SOURCE_AUTRE_PROGRAMME" for a in rap.anomalies)


def test_programme_hors_rentree():
    rap = verifier_integrite(referentiel_fictif(), rentree=2020, autoriser_fictif=True)
    assert any(a.code == "PROGRAMME_HORS_RENTREE" for a in rap.anomalies)
    assert not any(a.code == "PROGRAMME_HORS_RENTREE" for a in
                   verifier_integrite(referentiel_fictif(), rentree=2026, autoriser_fictif=True).anomalies)


@pytest.mark.parametrize("exo,raison", [
    (lambda: _exo(chapitre_id="chap:fictif:autre"), "chapitre_incoherent"),
    (lambda: _exo(programme_id="prog:fictif:autre"), "programme_incoherent"),
    (lambda: _exo(niveau="5e"), "niveau_incoherent"),
    (lambda: _exo(matiere="svt"), "matiere_incoherente"),
    (lambda: _exo(notion_id="notion:fictif:inconnue"), "notion_inconnue"),
    (lambda: _exo(N3), "notion_non_autorisee"),
    (lambda: _exo(source_sha256_extrait="f" * 64), "source_incoherente"),
    (lambda: _exo(enonce="Écris 7/10 sous forme décimale : 0,7."), "reponse_fuite_dans_enonce"),
])
def test_contenu_exercice_incoherent(exo, raison):
    rap = verifier_integrite(referentiel_fictif(), [exo()], autoriser_fictif=True)
    assert any(a.code == "EXERCICE_INVALIDE" and raison in a.detail for a in rap.anomalies), rap.anomalies
    assert not rap.demontree


def test_quiz_incoherent():
    rap = verifier_integrite(referentiel_fictif(), [], [_quiz(niveau="5e"), _quiz(id="quiz:fictif:v2-2",
                             choix=("3/7", "6/14", "1/7"))], autoriser_fictif=True)
    details = {a.detail for a in rap.anomalies if a.code == "QUIZ_INVALIDE"}
    assert "NIVEAU_INCOHERENT" in details and "DOUBLE_BONNE_REPONSE" in details


def test_duplicata_id_bloque_tout_le_lot():
    rap = verifier_integrite(referentiel_fictif(), [_exo(), _exo()], autoriser_fictif=True)
    assert any(a.code == "CONTENU_ID_DUPLIQUE" for a in rap.anomalies) and rap.generables == frozenset()


def test_duplicata_de_contenu():
    rap = verifier_integrite(referentiel_fictif(), [_exo(), _exo(id="exo:fictif:v2-copie")], autoriser_fictif=True)
    assert any("doublon_exact" in a.detail for a in rap.anomalies)


def test_plans_incoherents():
    fuite = PLAN.model_copy(update={"questions_intermediaires": ("La réponse est 0,7.",)})
    rap = verifier_integrite(referentiel_fictif(), [_exo()], plans={"exo:fictif:v2-1": fuite,
                                                                    "exo:fictif:absent": PLAN},
                             autoriser_fictif=True)
    codes = {(a.code, a.objet_id) for a in rap.anomalies}
    assert ("PLAN_SANS_EXERCICE", "exo:fictif:absent") in codes and ("PLAN_INVALIDE", "exo:fictif:v2-1") in codes


def test_exiger_integrite():
    with pytest.raises(IntegriteNonDemontree):
        exiger_integrite(verifier_integrite(referentiel_fictif(), [_exo(), _exo()], autoriser_fictif=True))
    exiger_integrite(verifier_integrite(referentiel_fictif(), [_exo()], autoriser_fictif=True))


def test_extrait_tronque_ne_prouve_pas():
    # Texte de notion plus long que l'extrait (extrait tronqué) ⇒ jamais PROVEN.
    n1 = referentiel_fictif().index().notions[N1]
    court = "[FICTIF] Comparer, ranger"
    ref = _ref_modifie(N1, preuve=n1.preuve.model_copy(update={"extrait": court, "sha256_extrait": sha256_texte(court)}))
    rap = verifier_integrite(ref, autoriser_fictif=True)
    assert N1 not in rap.generables


# --------------------------------------------------------------------------- #
# Backlog réel (hiérarchique, verrou d'intégrité, reproductible)
# --------------------------------------------------------------------------- #
def test_backlog_hierarchique_et_coherent():
    ref = referentiel_fictif()
    bl = calculer_backlog(ref, [_exo()], [_quiz()], autoriser_fictif=True)
    assert bl["integrite"]["demontree"]
    cle = "mathematiques / 6e / prog:fictif:mathematiques:cycle3:2025 / chap:fictif:fractions-6e"
    h = bl["par_hierarchie"][cle]
    assert h["NOTIONS_TOTAL"] == 3 and h["PROVEN"] == 2 and h["WAITING_SOURCE"] == 1
    assert h["WITH_EXERCISE"] == 1 and h["WITH_QUIZ"] == 1 and h["WITH_BOTH"] == 0
    assert h["NEED_EXERCISE"] == 1 and h["NEED_QUIZ"] == 1  # N1 sans exo, N2 sans quiz
    for groupe in [bl["total"], *bl["par_hierarchie"].values(), *bl["par_matiere"].values()]:
        assert groupe["PROVEN"] + groupe["NOT_EVIDENCED"] + groupe["AMBIGUOUS"] + groupe["QUARANTINED"] \
            == groupe["NOTIONS_TOTAL"]
        assert groupe["WAITING_SOURCE"] == groupe["NOTIONS_TOTAL"] - groupe["PROVEN"]
        assert groupe["WITH_BOTH"] <= min(groupe["WITH_EXERCISE"], groupe["WITH_QUIZ"])
    assert "Par matière / niveau / programme / chapitre" in en_markdown(bl)


def test_backlog_sans_integrite_aucune_generation():
    bl = calculer_backlog(referentiel_fictif(), [_exo(), _exo()], [], autoriser_fictif=True)
    assert not bl["integrite"]["demontree"] and bl["total"]["NEED_EXERCISE"] == 0 and bl["total"]["NEED_QUIZ"] == 0


def test_backlog_deterministe():
    a = calculer_backlog(referentiel_fictif(), [_exo()], [_quiz()], autoriser_fictif=True)
    b = calculer_backlog(referentiel_fictif(), [_exo()], [_quiz()], autoriser_fictif=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_backlog_waiting_oracle():
    # Réponse non vérifiable automatiquement (texte libre en SVT…) ⇒ WAITING_ORACLE.
    ex = _exo(type_verification="inconnu_x")
    bl = calculer_backlog(referentiel_fictif(), [ex], [], autoriser_fictif=True)
    assert bl["total"]["WAITING_ORACLE"] == 1


# --------------------------------------------------------------------------- #
# Dépôt : publication, rollback, altération
# --------------------------------------------------------------------------- #
def test_publication_rollback_et_alteration(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    sha1 = _lot(tmp_path / "l1", lot_id="lot-fictif-1")
    assert depot.publier(tmp_path / "l1", sha1).statut == "VALIDATED"
    sha2 = _lot(tmp_path / "l2", exos=[_exo(id="exo:fictif:v2-1", difficulte=3)], lot_id="lot-fictif-2")
    depot.publier(tmp_path / "l2", sha2)
    assert depot.actif()["lot"].startswith("lot-fictif-2")
    assert depot.charger_actif().exercices[0].difficulte == 3
    with pytest.raises(DepotInvalide):
        depot.publier(tmp_path / "l2", sha2)  # jamais écrasé
    assert depot.rollback().startswith("lot-fictif-1")
    assert depot.charger_actif().exercices[0].difficulte == 2
    # Altération du lot actif sur disque après publication ⇒ refus de servir.
    actif = tmp_path / "depot" / "lots" / depot.actif()["lot"]
    (actif / "c02_6_1.bin").write_bytes(b"[FICTIF] altere sur disque")
    with pytest.raises(DepotInvalide):
        depot.charger_actif()
    lignes = (tmp_path / "depot" / "HISTORIQUE.jsonl").read_text("utf-8").splitlines()
    assert [json.loads(x)["action"] for x in lignes] == ["activer", "activer", "rollback"]


def test_publication_d_un_lot_invalide_n_active_rien(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    sha = _lot(tmp_path / "l1", exos=[_exo(), _exo()])
    assert depot.publier(tmp_path / "l1", sha).statut == "REJECTED"
    assert depot.actif() is None and not (tmp_path / "depot" / "lots").exists()
    with pytest.raises(DepotInvalide):
        depot.rollback()


def test_actif_corrompu(tmp_path):
    (tmp_path / "depot").mkdir()
    (tmp_path / "depot" / "ACTIF.json").write_text("{", "utf-8")
    with pytest.raises(DepotInvalide):
        DepotContenu(tmp_path / "depot").charger_actif()


def test_copie_immuable_independante_de_la_source(tmp_path):
    depot = DepotContenu(tmp_path / "depot", autoriser_fictif=True)
    sha = _lot(tmp_path / "l1")
    depot.publier(tmp_path / "l1", sha)
    shutil.rmtree(tmp_path / "l1")  # la source disparaît : le lot publié reste servi
    assert depot.charger_actif().statut == "VALIDATED"


def test_notion_autorisee_mais_touchee_par_une_anomalie_non_generable():
    # Mutant « generation_malgre_anomalie » : N2 franchit le verrou de génération (prouvée,
    # texte sain) mais son exercice est incohérent ⇒ N2 exclue ; N1 (intacte) reste générable.
    from app.curriculum.provenance import autorisation_generation

    ref = referentiel_fictif()
    assert autorisation_generation(ref.index().notions[N2], ref.index(), autoriser_fictif=True).autorise
    rap = verifier_integrite(ref, [_exo(chapitre_id="chap:fictif:autre")], autoriser_fictif=True)
    assert N2 not in rap.generables and N1 in rap.generables
