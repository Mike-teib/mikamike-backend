"""Backlog (Phase 19), audit dédup (18), import strict (20), reprise/checkpoint (23), perf (22)."""

import json
import time
from pathlib import Path

import pytest

from app.curriculum.audit import auditer
from app.curriculum.backlog import calculer_backlog, en_markdown
from app.curriculum.exercices import Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.importers import ecrire_manifest, importer
from app.curriculum.legacy import migrer_existant
from app.curriculum.model import Matiere, Niveau, Notion, Referentiel
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.structure import valider_referentiel


def _exo(idx, i, enonce, rep, nid="notion:fictif:fractions-decimales"):
    n = idx.notions[nid]
    return Exercice(
        id=f"exo:fictif:e{i}", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
        programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=2,
        objectif_pedagogique="[FICTIF] objectif", prerequis=n.prerequis, enonce=enonce,
        reponse_attendue=rep, type_verification="maths_symbolique",
        source_sha256_extrait=n.preuve.sha256_extrait if n.preuve else "0" * 64,
    )


def _quiz(idx):
    n = idx.notions["notion:fictif:fractions-decimales"]
    return QuestionQuiz(id="quiz:fictif:q1", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                        enonce="Écriture décimale de 3/10 ?", choix=("0,3", "3,10", "0,03"),
                        index_correct=0, reponse_reference="3/10", type_verification="maths_symbolique",
                        explication="trois dixièmes")


# --------------------------------------------------------------------------- #
# Backlog
# --------------------------------------------------------------------------- #
def test_backlog_existant_tout_attend_une_source():
    bl = calculer_backlog(Referentiel(notions=migrer_existant().notions))
    t = bl["total"]
    assert t["NOTIONS_TOTAL"] == 42 and t["PROVEN"] == 0 and t["WAITING_SOURCE"] == 42
    assert t["NEED_EXERCISE"] == 0  # aucune génération autorisée sans preuve
    assert sum(v["NOTIONS_TOTAL"] for v in bl["par_matiere"].values()) == 42


def test_backlog_fixtures_mode_test():
    ref = referentiel_fictif()
    idx = ref.index()
    exos = [_exo(idx, 1, "Écris 7/10 en décimal.", "0,7")]
    bl = calculer_backlog(ref, exos, [_quiz(idx)], autoriser_fictif=True)
    t = bl["total"]
    assert t["NOTIONS_TOTAL"] == 3 and t["OPTIONAL"] == 1      # optionnelle exclue
    assert t["PROVEN"] == 2 and t["NOT_EVIDENCED"] == 1
    assert t["WITH_EXERCISE"] == 1 and t["WITH_QUIZ"] == 1 and t["WITH_BOTH"] == 1
    assert t["NEED_EXERCISE"] == 1 and t["NEED_QUIZ"] == 1      # comparer-fractions
    assert t["WAITING_SOURCE"] == 1 and t["WAITING_ORACLE"] == 0
    assert bl["par_chapitre"]["chap:fictif:fractions-6e"]["NOTIONS_TOTAL"] == 3


def test_backlog_waiting_oracle():
    ref = referentiel_fictif()
    idx = ref.index()
    non_verifiable = _exo(idx, 2, "Explique ce qu'est un dixième.", "une partie sur dix")
    bl = calculer_backlog(ref, [non_verifiable], autoriser_fictif=True)
    assert bl["total"]["WAITING_ORACLE"] == 1


def test_backlog_reproductible_et_markdown():
    ref = Referentiel(notions=migrer_existant().notions)
    a, b = calculer_backlog(ref), calculer_backlog(ref)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    md = en_markdown(a)
    assert "| NOTIONS_TOTAL | 42 |" in md and "par matiere" in md


# --------------------------------------------------------------------------- #
# Audit de déduplication
# --------------------------------------------------------------------------- #
def test_audit_dedup_complet():
    ref = referentiel_fictif()
    idx = ref.index()
    exos = [
        _exo(idx, 1, "Écris 7/10 sous forme décimale.", "0,7"),
        _exo(idx, 2, "Écris  7/10 sous forme décimale.", "0,7"),                  # exact
        _exo(idx, 3, "Écris 3/10 sous forme décimale.", "0,3"),                   # même gabarit
        _exo(idx, 4, "Écris 7/10 sous forme décimale s'il te plaît.", "0,7"),     # quasi-doublon
        _exo(idx, 5, "Écris 9/10 en décimal.", "0,9", nid="notion:fictif:sans-preuve"),
    ]
    au = auditer(ref, exos, seuil=0.5)
    assert ["exo:fictif:e1", "exo:fictif:e2"] in au["exact_duplicates"]
    assert any({"exo:fictif:e1", "exo:fictif:e3"} <= set(g) for g in au["same_notion_question"])
    assert any({"exo:fictif:e1", "exo:fictif:e3"} <= set(g) for g in au["same_answer_structure"])
    assert any({a, b} == {"exo:fictif:e1", "exo:fictif:e4"} for a, b, _ in au["near_duplicates"])


def test_audit_orphelins():
    ref = referentiel_fictif()
    idx = ref.index()
    orphelin = _exo(idx, 9, "Calcule 2 + 2.", "4").model_copy(update={"notion_id": "notion:inexistante"})
    au = auditer(ref, [orphelin])
    assert {"type": "contenu_notion_inconnue", "id": "exo:fictif:e9", "notion_id": "notion:inexistante"} \
        in au["orphan_content"]
    au2 = auditer(Referentiel(notions=migrer_existant().notions))
    assert au2["totaux"]["orphan_content"] == 42  # notions sans chapitre


# --------------------------------------------------------------------------- #
# Import strict + checkpoint
# --------------------------------------------------------------------------- #
def _preparer(tmp_path: Path, avec_opaque=True) -> Path:
    d = tmp_path / "artefacts"
    d.mkdir()
    ref = referentiel_fictif()
    base = ref.model_copy(update={"notions": ()})
    (d / "referentiel.json").write_text(base.model_dump_json(), "utf-8")
    with (d / "registre.jsonl").open("w", encoding="utf-8") as f:
        for n in ref.notions:
            f.write(n.model_copy(update={"chapitre_id": None}).model_dump_json() + "\n")
    with (d / "mapping.jsonl").open("w", encoding="utf-8") as f:
        for n in ref.notions:
            f.write(json.dumps({"notion_id": n.id, "chapitre_id": n.chapitre_id}) + "\n")
    types = {"referentiel.json": "referentiel", "registre.jsonl": "registre_notions",
             "mapping.jsonl": "mapping_notion_chapitre"}
    if avec_opaque:
        (d / "rapport_C02.txt").write_text("rapport d'audit fictif\n", "utf-8")
        types["rapport_C02.txt"] = "opaque"
    ecrire_manifest(d, types)
    return d


def test_import_valide_avec_mapping(tmp_path):
    d = _preparer(tmp_path)
    res = importer(d, checkpoint=tmp_path / "ck.json")
    assert res.statut == "VALIDATED", (res.fichiers, res.anomalies)
    assert all(n.chapitre_id for n in res.referentiel.notions)
    assert res.opaques == [{"chemin": "rapport_C02.txt", "sha256": res.opaques[0]["sha256"],
                            "statut": "OPAQUE_A_MAPPER"}]
    assert valider_referentiel(res.referentiel) == []


def test_import_reprise_sans_retraitement(tmp_path):
    d = _preparer(tmp_path)
    ck = tmp_path / "ck.json"
    importer(d, checkpoint=ck)
    res2 = importer(d, checkpoint=ck)
    assert all(f["reprise"] == "true" for f in res2.fichiers.values())
    assert res2.statut == "VALIDATED"


def test_import_fichier_altere_failed_puis_reprise(tmp_path):
    d = _preparer(tmp_path)
    ck = tmp_path / "ck.json"
    original = (d / "mapping.jsonl").read_text("utf-8")
    (d / "mapping.jsonl").write_text(original + "\n", "utf-8")  # altération
    res = importer(d, checkpoint=ck)
    assert res.statut == "FAILED"
    assert res.fichiers["mapping.jsonl"] == {"etat": "FAILED", "raison": "empreinte_differente"}
    assert json.loads(ck.read_text())["registre.jsonl"]["etat"] == "DONE"
    (d / "mapping.jsonl").write_text(original, "utf-8")  # correction
    res2 = importer(d, checkpoint=ck)
    assert res2.statut == "VALIDATED"
    assert res2.fichiers["registre.jsonl"]["reprise"] == "true"
    assert res2.fichiers["mapping.jsonl"]["reprise"] == "false"


def test_import_fichier_non_liste_refuse(tmp_path):
    d = _preparer(tmp_path)
    (d / "intrus.json").write_text("{}", "utf-8")
    assert importer(d).statut == "FAILED"


def test_import_manifest_absent_ou_chemin_hors_dossier(tmp_path):
    d = tmp_path / "vide"
    d.mkdir()
    assert importer(d).statut == "FAILED"
    d2 = _preparer(tmp_path)
    m = json.loads((d2 / "IMPORT_MANIFEST.json").read_text())
    m["fichiers"][0]["chemin"] = "../../etc/passwd"
    (d2 / "IMPORT_MANIFEST.json").write_text(json.dumps(m))
    res = importer(d2)
    assert res.statut == "FAILED" and "chemin_hors_dossier" in res.fichiers["IMPORT_MANIFEST.json"]["raison"]


@pytest.mark.parametrize("ligne,raison", [
    ('{"id": "notion:x:y", "nom": "Dupont"}', "cle_personnelle"),
    ('{"texte": "contact parent@example.com"}', "email_detecte"),
    ('{"texte": "appeler le ' + "06 " + '12 34 56 78"}', "telephone_detecte"),  # construit : pas de motif littéral
    ("pas du json", "json_invalide"),
])
def test_import_donnees_personnelles_ou_invalides(tmp_path, ligne, raison):
    d = tmp_path / "a"
    d.mkdir()
    (d / "registre.jsonl").write_text(ligne + "\n", "utf-8")
    ecrire_manifest(d, {"registre.jsonl": "registre_notions"})
    res = importer(d)
    assert res.statut == "FAILED"
    assert raison in res.fichiers["registre.jsonl"]["raison"]


def test_import_schema_invalide_tout_ou_rien(tmp_path):
    d = tmp_path / "a"
    d.mkdir()
    ok = referentiel_fictif().notions[0].model_dump_json()
    (d / "registre.jsonl").write_text(ok + "\n" + '{"id": "notion:x:y"}\n', "utf-8")
    ecrire_manifest(d, {"registre.jsonl": "registre_notions"})
    res = importer(d)
    assert res.statut == "FAILED" and res.referentiel is None


def test_import_mapping_incoherent_rejete(tmp_path):
    d = _preparer(tmp_path, avec_opaque=False)
    with (d / "mapping.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"notion_id": "notion:fictif:comparer-fractions", "chapitre_id": "chap:inexistant"}) + "\n")
    ecrire_manifest(d, {"referentiel.json": "referentiel", "registre.jsonl": "registre_notions",
                        "mapping.jsonl": "mapping_notion_chapitre"})
    res = importer(d)
    assert res.statut == "REJECTED"
    assert any(a.code == "MAPPING_CHAPITRE_INCONNU" for a in res.anomalies)


# --------------------------------------------------------------------------- #
# Performance (benchmarks légers, bornes larges pour la CI)
# --------------------------------------------------------------------------- #
def test_perf_validation_5000_notions_et_chaine_longue():
    ref = referentiel_fictif()
    prog, chap = ref.programmes[0], ref.chapitres[0]
    notions = []
    for i in range(5000):
        notions.append(Notion(
            id=f"notion:bench:n{i}", programme_id=prog.id, chapitre_id=chap.id, niveau=Niveau.SIXIEME,
            matiere=Matiere.MATHEMATIQUES, texte=f"[FICTIF] Notion de charge numéro {i} bien formée",
            prerequis=(f"notion:bench:n{i - 1}",) if i else (),
        ))
    gros = ref.model_copy(update={"notions": tuple(notions)})
    t0 = time.perf_counter()
    anomalies = valider_referentiel(gros)  # chaîne de 5000 prérequis : pas de RecursionError
    duree = time.perf_counter() - t0
    assert anomalies == []
    assert duree < 20, duree
