"""Tests du scanner de secrets : détecte sans jamais afficher la valeur."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "secret_scan", Path(__file__).resolve().parent.parent / "tools" / "secret_scan.py"
)
secret_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(secret_scan)

# Valeurs construites dynamiquement : aucun motif littéral dans le dépôt.
FAUSSE_CLE_STRIPE = "sk_" + "live_" + "A1b2C3d4E5f6G7h8"
FAUSSE_URL_DB = "postgresql://" + "admin:" + "motdepasse@hote/base"
FAUX_TEL = "06 " + "12 34 56 78"


def test_detecte_cle_stripe_sans_la_revelee(capsys):
    dets = list(secret_scan.scanner_texte("f.py", f"KEY = '{FAUSSE_CLE_STRIPE}'"))
    assert [d.regle for d in dets] == ["stripe_live_key"]
    assert FAUSSE_CLE_STRIPE not in repr(dets)


def test_detecte_url_db_et_telephone():
    regles = {d.regle for d in secret_scan.scanner_texte("f", f"{FAUSSE_URL_DB}\ntel {FAUX_TEL}")}
    assert regles == {"db_url_with_password", "fr_phone_number"}


def test_pas_de_faux_positif_sur_code_normal():
    texte = "MIKA_DB_URL=sqlite:///./x.db\nversion = 0.612345678\nx = os.getenv('MIKA_JWT_SECRET')"
    assert list(secret_scan.scanner_texte("f", texte)) == []


def test_fichier_env_interdit():
    assert secret_scan.FICHIERS_INTERDITS.search("config/.env")
    assert secret_scan.FICHIERS_INTERDITS.search("mikamike.db")
    assert secret_scan.FICHIERS_INTERDITS.search(".env.production")
    assert not secret_scan.FICHIERS_INTERDITS.search("app/core/env.py")
    assert not secret_scan.FICHIERS_INTERDITS.search("README.md")


def test_arbre_courant_propre():
    assert secret_scan.scanner_arbre() == []
