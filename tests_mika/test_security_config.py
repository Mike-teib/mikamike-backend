"""
Tests fail-closed de la configuration des secrets (app/core/security_config.py).

Ces tests NE contiennent aucun secret réel. Le littéral historique n'est jamais
écrit en clair : il est reconstruit par concaténation, donc il n'apparaît pas
comme chaîne contiguë dans ce fichier.
"""

from pathlib import Path

import pytest

from app.core.security_config import (
    SecretConfigError,
    get_jwt_secret,
    get_pseudo_secret,
)

# Littéral historique reconstruit (jamais écrit en clair d'un bloc).
_HISTORIQUE = "mikamike_secret_key" + "_2026"


def test_1_jwt_absent_refuse(monkeypatch):
    monkeypatch.delenv("MIKA_JWT_SECRET", raising=False)
    with pytest.raises(SecretConfigError):
        get_jwt_secret()


def test_2_pseudo_absent_refuse(monkeypatch):
    monkeypatch.delenv("MIKA_PSEUDO_SECRET", raising=False)
    with pytest.raises(SecretConfigError):
        get_pseudo_secret()


def test_3_valeur_vide_refusee(monkeypatch):
    monkeypatch.setenv("MIKA_JWT_SECRET", "   ")
    with pytest.raises(SecretConfigError):
        get_jwt_secret()


def test_4_valeur_faible_refusee(monkeypatch):
    # trop courte
    monkeypatch.setenv("MIKA_PSEUDO_SECRET", "court")
    with pytest.raises(SecretConfigError):
        get_pseudo_secret()
    # littéral historique
    monkeypatch.setenv("MIKA_PSEUDO_SECRET", _HISTORIQUE)
    with pytest.raises(SecretConfigError):
        get_pseudo_secret()
    # générique
    monkeypatch.setenv("MIKA_JWT_SECRET", "changeme")
    with pytest.raises(SecretConfigError):
        get_jwt_secret()


def test_5_secrets_valides_chargent_app(monkeypatch):
    monkeypatch.setenv("MIKA_PSEUDO_SECRET", "un-vrai-secret-de-test-suffisamment-long-01")
    monkeypatch.setenv("MIKA_JWT_SECRET", "un-autre-secret-de-test-distinct-et-long-02")
    assert get_pseudo_secret() == "un-vrai-secret-de-test-suffisamment-long-01"
    assert get_jwt_secret() == "un-autre-secret-de-test-distinct-et-long-02"
    import main  # importé avec des secrets de test valides (posés en conftest)
    assert main.app is not None


def test_6_erreur_ne_revele_pas_le_secret(monkeypatch):
    faible = _HISTORIQUE
    monkeypatch.setenv("MIKA_PSEUDO_SECRET", faible)
    with pytest.raises(SecretConfigError) as exc:
        get_pseudo_secret()
    assert faible not in str(exc.value)


def test_7_litteral_historique_absent_du_code_executable():
    root = Path(__file__).resolve().parents[1]
    cibles = [root / "main.py"]
    for d in ("app", "paiement_comptes"):
        cibles += list((root / d).rglob("*.py"))
    fautifs = [
        str(f.relative_to(root))
        for f in cibles
        if f.is_file() and _HISTORIQUE in f.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not fautifs, f"littéral historique présent dans le code : {fautifs}"


def test_8_pseudo_et_jwt_sont_distincts(monkeypatch):
    # Aucun repli de l'un sur l'autre : JWT absent est refusé même si le pseudo est présent.
    monkeypatch.setenv("MIKA_PSEUDO_SECRET", "pseudo-secret-de-test-assez-long-aaa")
    monkeypatch.delenv("MIKA_JWT_SECRET", raising=False)
    with pytest.raises(SecretConfigError):
        get_jwt_secret()
