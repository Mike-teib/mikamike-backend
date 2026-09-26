"""
Performance / mémoire du pipeline d'import sur corpus SYNTHÉTIQUE volumineux (lot 8, session 3).

Mesures relatives (rapports de temps / mémoire entre deux tailles) pour rester robustes aux
variations de la machine de CI : on vérifie la FORME de la croissance (linéaire, pas O(N²)),
pas une durée absolue.
"""

import time
import tracemalloc

import pytest

from app.curriculum import importers
from app.curriculum.harnais_import import executer_pipeline, generer_lot

PETIT, GRAND = 1500, 6000  # facteur 4


def _mesure(dossier, sha):
    tracemalloc.start()
    t = time.perf_counter()
    res = importers.importer(dossier, sha256_manifest=sha, autoriser_fictif=True)
    duree = time.perf_counter() - t
    pic = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert res.statut == "VALIDATED"
    return duree, pic


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    d = tmp_path_factory.mktemp("corpus")
    return {n: generer_lot(d / f"n{n}", n_notions=n, n_chapitres=40) for n in (PETIT, GRAND)}


def test_croissance_lineaire_temps_et_memoire(corpus):
    t_p, m_p = _mesure(corpus[PETIT].dossier, corpus[PETIT].sha_manifest)
    t_g, m_g = _mesure(corpus[GRAND].dossier, corpus[GRAND].sha_manifest)
    # Linéaire ⇒ ×4 ; quadratique ⇒ ×16. Seuils larges (bruit de CI) mais qui excluent O(N²).
    assert t_g / t_p < 8, (t_p, t_g)
    assert m_g / m_p < 5.5, (m_p, m_g)
    # Coût mémoire par notion borné (objets validés conservés pour l'intégrité croisée).
    assert m_g / GRAND < 16_000, m_g


def test_generation_en_flux_memoire_bornee(tmp_path):
    tracemalloc.start()
    generer_lot(tmp_path / "flux", n_notions=GRAND, n_chapitres=40)
    pic = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert pic < 3 * 1024 * 1024, pic  # le générateur écrit ligne à ligne : pas de liste de 6000 objets


def test_lecture_jsonl_en_flux(corpus, monkeypatch):
    """Le registre M01 est lu ligne à ligne (jamais `read()` du fichier entier)."""
    lu_entier = []
    orig = importers.Path.read_text

    def espion(self, *a, **k):
        if self.suffix == ".jsonl":
            lu_entier.append(self.name)
        return orig(self, *a, **k)

    monkeypatch.setattr(importers.Path, "read_text", espion)
    lot = corpus[PETIT]
    assert importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True).statut == "VALIDATED"
    assert lu_entier == []


def test_checkpoint_ecrit_une_fois_par_fichier(corpus, tmp_path, monkeypatch):
    """Écriture du checkpoint en O(fichiers), pas en O(lignes) (sinon O(N²) en E/S)."""
    appels = []
    orig = importers._ecrire_checkpoint
    monkeypatch.setattr(importers, "_ecrire_checkpoint", lambda c, e: appels.append(1) or orig(c, e))
    lot = corpus[GRAND]
    importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True,
                       checkpoint=tmp_path / "ck.json")
    import json

    n_fichiers = len(json.loads((lot.dossier / "IMPORT_MANIFEST.json").read_text("utf-8"))["fichiers"])
    assert len(appels) == n_fichiers  # une écriture par fichier du lot, pas par ligne


def test_reprise_sur_gros_corpus(corpus, tmp_path, monkeypatch):
    lot = corpus[GRAND]
    ck = tmp_path / "ck.json"
    orig = importers.sha256_fichier

    def coupure(chemin):
        if chemin.name == "mapping.jsonl":
            raise KeyboardInterrupt
        return orig(chemin)

    monkeypatch.setattr(importers, "sha256_fichier", coupure)
    with pytest.raises(KeyboardInterrupt):
        importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True, checkpoint=ck)
    monkeypatch.setattr(importers, "sha256_fichier", orig)
    res = importers.importer(lot.dossier, sha256_manifest=lot.sha_manifest, autoriser_fictif=True, checkpoint=ck)
    assert res.statut == "VALIDATED" and len(res.referentiel.notions) == GRAND
    assert res.fichiers["M01_notions.jsonl"]["reprise"] == "true"
    assert res.fichiers["mapping.jsonl"]["reprise"] == "false"


def test_pipeline_complet_gros_corpus(corpus):
    lot = corpus[GRAND]
    t = time.perf_counter()
    rap = executer_pipeline(lot.dossier, lot.sha_manifest)
    assert rap.statut == "VALIDATED" and rap.backlog["total"]["NOTIONS_TOTAL"] == GRAND
    assert time.perf_counter() - t < 60  # garde-fou large (≈ 2 s mesurées en local)
