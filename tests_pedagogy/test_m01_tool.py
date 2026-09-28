"""Outil de non-régression M01 : corpus synthétiques [FICTIF], jamais de données réelles."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import M01_346_COMPARISON_TOOL as m01  # noqa: E402


def _row(i, text, level="6E", chapter="Nombres", source="SRC", page="3"):
    return {"notion_id": f"M01-{i:03d}", "text": text, "level": level, "chapter": chapter,
            "source_id": source, "page": page}


def _write(path: Path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


@pytest.fixture()
def corpus(tmp_path):
    pub = [_row(i, f"[FICTIF] Notion numéro {i} sur les nombres entiers") for i in range(346)]
    pub[1] = _row(1, "[FICTIF] Utiliser la fraction 1/10 pour un dixième")
    pub[2] = _row(2, "[FICTIF] Écrire 10⁻³ sous forme décimale")
    pub[3] = _row(3, "[FICTIF] Calculer 3 × 4 = 12")
    pub[4] = _row(4, "[FICTIF] Aire du carré de côté 5")
    rex = [dict(r) for r in pub]
    rex[1] = _row(1, "[FICTIF] Utiliser la fraction 0,1 pour un dixième")   # formule changée (1/10 → 0,1)
    rex[2] = _row(2, "[FICTIF] Écrire 10^{-3} sous forme décimale")          # même math, notation LaTeX
    rex[3] = _row(3, "[FICTIF] Calculer 3 × 5 = 15")                          # formule modifiée
    rex[4] = _row(4, "[FICTIF] Aire du carré de côté 5", chapter="Grandeurs")  # réaffectée
    rex[5] = _row(5, rex[5]["text"], source="SRC-2")                          # source différente
    rex[6] = _row(6, "[FICTIF] Notion numéro 6 sur les nombres décimaux")     # texte modifié
    del rex[7]                                                                # absente
    rex.append(_row(999, "[FICTIF] Nouvelle notion ré-extraite"))
    p, r = tmp_path / "pub.jsonl", tmp_path / "rex.jsonl"
    _write(p, pub)
    _write(r, rex)
    return tmp_path, p, r


def test_classement_complet(corpus):
    _, p, r = corpus
    mp = m01._parse_map(None)
    res = m01.compare(m01.load_corpus(p, mp), m01.load_corpus(r, mp))
    st = {row["published_id"]: row["status"] for row in res["rows"]}
    assert st["M01-001"] == "FORMULE_MODIFIEE"
    assert st["M01-003"] == "FORMULE_MODIFIEE"
    assert st["M01-004"] == "NOTION_REAFFECTEE"
    assert st["M01-005"] == "SOURCE_DIFFERENTE"
    assert st["M01-006"] == "TEXTE_MODIFIE"
    assert st["M01-007"] == "NOTION_ABSENTE"
    assert st["M01-000"] == "IDENTIQUE"
    assert res["published_count"] == 346 and res["warnings"] == []
    assert res["new_in_reextraction"] == ["M01-999"]
    assert sum(res["counts"].values()) == 346


def test_notation_degradee_detectee():
    old, new = "Écrire 10⁻³ et x² ≤ 5", "Écrire 10-3 et x2 <= 5"
    assert "EXPOSANT_PERDU" in m01.notation_degradation(old, new)
    assert "SYMBOLE_MODIFIE:≤" in m01.notation_degradation(old, new)
    p = {"id": "a", "text": "[FICTIF] Écrire 10⁻³", "level": "", "domain": "", "chapter": "", "source": "", "page": ""}
    r = dict(p, text="[FICTIF] Écrire 10^{-3}")
    assert m01.classify(p, r) != ["NOTATION_DEGRADEE"]  # même math, LaTeX : pas de dégradation de sens
    r2 = dict(p, text="[FICTIF] Écrire 10 -3")
    assert "FORMULE_MODIFIEE" in m01.classify(p, r2)


def test_rapport_et_lecture_seule(corpus):
    tmp, p, r = corpus
    avant = (p.read_bytes(), r.read_bytes())
    out = tmp / "out"
    assert m01.main(["--published", str(p), "--reextracted", str(r), "--out-dir", str(out)]) == 0
    assert (p.read_bytes(), r.read_bytes()) == avant
    md = (out / "M01_346_COMPARISON_REPORT.md").read_text(encoding="utf-8")
    assert "COMPARAISON EFFECTUÉE" in md and "{{" not in md and "M01-007" in md
    data = json.loads((out / "M01_346_COMPARISON_REPORT.json").read_text(encoding="utf-8"))
    assert data["counts"]["NOTION_ABSENTE"] == 1


def test_effectif_inattendu_signale(tmp_path):
    p, r = tmp_path / "p.json", tmp_path / "r.json"
    p.write_text(json.dumps([_row(i, f"[FICTIF] n {i}") for i in range(10)]), encoding="utf-8")
    r.write_text(json.dumps({"notions": [_row(i, f"[FICTIF] n {i}") for i in range(10)]}), encoding="utf-8")
    mp = m01._parse_map(None)
    res = m01.compare(m01.load_corpus(p, mp), m01.load_corpus(r, mp))
    assert res["warnings"] and "EFFECTIF_INATTENDU" in res["warnings"][0]


def test_corpus_absent_aucune_comparaison(tmp_path):
    out = tmp_path / "out"
    code = subprocess.run([sys.executable, str(ROOT / "M01_346_COMPARISON_TOOL.py"),
                           "--published", str(tmp_path / "absent.jsonl"), "--reextracted", str(tmp_path / "x.jsonl"),
                           "--out-dir", str(out)], capture_output=True, text=True)
    assert code.returncode == 2 and "CORPUS_ABSENT" in code.stderr
    assert not out.exists()


def test_csv_et_mapping(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("code,libelle,niveau\nA1,[FICTIF] Addition,6E\n", encoding="utf-8")
    rows = m01.load_corpus(p, m01._parse_map("id=code,text=libelle"))
    assert rows == [{"id": "A1", "text": "[FICTIF] Addition", "level": "6E", "domain": "", "chapter": "",
                     "source": "", "page": ""}]


@pytest.mark.parametrize("contenu,code", [
    ('[{"notion_id": "a", "text": "x"}, {"notion_id": "a", "text": "y"}]', "ID_DUPLIQUE"),
    ('[{"notion_id": "a"}]', "TEXTE_ABSENT"),
    ("pas du json", "CORPUS_ILLISIBLE"),
])
def test_corpus_invalides(tmp_path, contenu, code):
    p = tmp_path / "c.json"
    p.write_text(contenu, encoding="utf-8")
    with pytest.raises(m01.CorpusError, match=code):
        m01.load_corpus(p, m01._parse_map(None))
