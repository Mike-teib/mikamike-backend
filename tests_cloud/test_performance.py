"""
Performance (lot F) : on mesure des GRANDEURS DÉTERMINISTES (nombre de requêtes SQL, nombre de
calculs, pic mémoire) plutôt que des chronos fragiles. Les rares bornes de temps sont larges.
"""

import json
import time
import tracemalloc

from sqlalchemy import event

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal, engine
from app.curriculum import audit, dedup
from app.curriculum.exercices import BanqueExercices, Exercice
from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.importers import MAX_LIGNE, ecrire_manifest, importer, sha256_fichier
from app.curriculum.text_quality import analyser_texte


def _exo(i: int, notion="notion:fictif:fractions-decimales") -> Exercice:
    n = referentiel_fictif().index().notions["notion:fictif:fractions-decimales"]
    return Exercice(id=f"exo:fictif:perf-{i}", notion_id=notion, matiere=n.matiere, niveau=n.niveau,
                    programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=1,
                    objectif_pedagogique="[FICTIF] perf", prerequis=n.prerequis,
                    enonce=f"[FICTIF] Question {i} : combien font {i} et {i + 1} ensemble ?",
                    reponse_attendue=str(2 * i + 1), type_verification="maths_symbolique",
                    source_sha256_extrait=n.preuve.sha256_extrait)


# --------------------------------------------------------------------------- #
# SQL : pas de N+1, agrégation en base
# --------------------------------------------------------------------------- #
def _compter_selects(fn):
    n = {"select": 0}

    def ecoute(conn, cursor, statement, *a):
        if statement.lstrip().upper().startswith("SELECT"):
            n["select"] += 1

    event.listen(engine, "before_cursor_execute", ecoute)
    try:
        out = fn()
    finally:
        event.remove(engine, "before_cursor_execute", ecoute)
    return out, n["select"]


def test_dashboard_nombre_de_requetes_constant(client):
    db = SessionLocal()
    try:
        for i in range(600):
            db.add(crud.TentativeExercice(eleve_hmac="h" * 16, exercice_id=f"e{i % 7}", matiere="maths",
                                          niveau="5e", competence=f"c{i % 30}", est_correct=i % 3 == 0))
        db.commit()
        stats, selects = _compter_selects(lambda: crud.agreger_dashboard(db, "h" * 16))
    finally:
        db.close()
    assert stats["exercices_tentes"] == 600 and len(stats["competences"]) == 30
    assert selects == 2  # GROUP BY + états, indépendamment du nombre de tentatives/compétences


def test_serie_de_succes_s_arrete_a_la_premiere_rupture(client):
    db = SessionLocal()
    try:
        for i in range(300):
            db.add(crud.TentativeExercice(eleve_hmac="s" * 16, exercice_id="e", competence="c",
                                          est_correct=i >= 297))
        db.commit()
        n, selects = _compter_selects(lambda: crud.compter_succes_consecutifs(db, "s" * 16, "c"))
    finally:
        db.close()
    assert n == 3 and selects == 1


# --------------------------------------------------------------------------- #
# Déduplication : calculs par item, pas par paire
# --------------------------------------------------------------------------- #
def test_audit_calcule_les_3grammes_une_fois_par_item(monkeypatch):
    appels = {"n": 0}
    original = dedup._shingles

    def compte(t, n=3):
        appels["n"] += 1
        return original(t, n)

    monkeypatch.setattr(dedup, "_shingles", compte)
    items = [_exo(i) for i in range(60)]  # 60 items sur UNE notion = 1770 paires
    audit.auditer(referentiel_fictif(), items, [])
    assert appels["n"] == 60


def test_banque_indexee_candidats_bornes():
    banque = BanqueExercices(_exo(i) for i in range(2000))
    # Gabarits identiques (nombres masqués) ⇒ tous candidats sur le gabarit ; un énoncé distinct
    # n'en a aucun : la recherche ne parcourt jamais toute la banque.
    distinct = _exo(5).model_copy(update={"id": "exo:fictif:autre", "enonce": "[FICTIF] Énoncé sans rapport."})
    assert banque.candidats(distinct) == []
    assert len(banque) == 2000


# --------------------------------------------------------------------------- #
# Import : lecture en flux, mémoire bornée
# --------------------------------------------------------------------------- #
def test_document_source_hache_sans_chargement(tmp_path):
    gros = tmp_path / "doc.bin"
    with gros.open("wb") as f:
        f.truncate(64 * 1024 * 1024)  # 64 Mo (fichier creux)
    tracemalloc.start()
    sha256_fichier(gros)
    _, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert pic < 8 * 1024 * 1024


def test_ligne_geante_refusee_sans_lecture_complete(tmp_path):
    (tmp_path / "n.jsonl").write_text('{"x": "' + "a" * (20 * MAX_LIGNE) + '"}\n', "utf-8")
    ecrire_manifest(tmp_path, {"n.jsonl": "registre_notions"})
    tracemalloc.start()
    res = importer(tmp_path)
    _, pic = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert res.statut == "FAILED"
    assert pic < 12 * MAX_LIGNE  # ≈ une ligne bornée, pas les 20 Mo


def test_registre_volumineux_en_flux(tmp_path):
    n = referentiel_fictif().index().notions["notion:fictif:comparer-fractions"]
    with (tmp_path / "n.jsonl").open("w", encoding="utf-8") as f:
        for i in range(5000):
            f.write(json.dumps(n.model_copy(update={"id": f"notion:fictif:n{i}", "texte": f"[FICTIF] Notion {i}."})
                               .model_dump(mode="json")) + "\n")
    ecrire_manifest(tmp_path, {"n.jsonl": "registre_notions"})
    t = time.perf_counter()
    res = importer(tmp_path)
    assert time.perf_counter() - t < 60  # borne large (≈ quelques secondes)
    assert res.statut == "REJECTED"  # programme/chapitre absents : attendu, mais tout est lu
    assert len(res.referentiel.notions) == 5000


# --------------------------------------------------------------------------- #
# Texte / regex : pas de comportement catastrophique
# --------------------------------------------------------------------------- #
def test_analyse_de_texte_pire_cas():
    pires = [" ".join(f"mot{i}" for i in range(330))[:2000], "a " * 1000, "((((" * 500,
             "x" * 2000, "Bulletin officiel " * 110, "=" * 2000, "é" * 2000]
    t = time.perf_counter()
    for p in pires:
        analyser_texte(p)
    assert time.perf_counter() - t < 5
