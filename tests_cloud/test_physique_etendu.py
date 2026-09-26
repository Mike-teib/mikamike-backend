"""
Validateurs Physique-Chimie (lot 14) : unité obligatoire dès que la grandeur est dimensionnée,
incertitudes, ordre de grandeur, conversions, constantes, chiffres significatifs ambigus.
"""

import time

import pytest

from app.curriculum.verifiers.base import Verdict as V
from app.curriculum.verifiers.dispatch import verifier
from app.curriculum.verifiers.physique import verifier_grandeur
from app.curriculum.verifiers.physique_etendu import (
    CONSTANTES,
    analyser_mesure,
    verifier_constante,
    verifier_conversion,
    verifier_incertitude,
    verifier_ordre_de_grandeur,
)
from app.curriculum.verifiers.physique import analyser_unite


# --- une valeur numérique seule ne valide jamais une grandeur dimensionnée ---------------------
@pytest.mark.parametrize("attendue", ["2,5 kg", "3,0e8 m/s", "12 km/h", "0,10 mol/L", "298 K", "4,2 J",
                                      "1,0 × 10^5 Pa", "50 Hz", "230 V"])
@pytest.mark.parametrize("unite_requise", [True, False])
def test_valeur_seule_jamais_valide(attendue, unite_requise):
    nombre = attendue.split(" ")[0] if "×" not in attendue else "1,0 × 10^5"
    assert verifier_grandeur(attendue, nombre, unite_requise=unite_requise).verdict == V.INVALID


@pytest.mark.parametrize("tol", [0, -0.01, 0.5, 10])
def test_tolerance_hors_bornes_refusee(tol):
    assert verifier_grandeur("2,5 kg", "2,5 kg", tolerance_relative=tol).verdict == V.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("att,rep,verdict", [
    ("20 m/s", "72 km/h", V.INVALID), ("20 m/s", "20 m.s-1", V.VALID), ("20 m/s", "20 m/s", V.VALID),
    ("298 K", "25 °C", V.INVALID), ("1,5 kg", "1500 g", V.INVALID),
])
def test_unite_imposee(att, rep, verdict):
    assert verifier_grandeur(att, rep, unite_imposee=True).verdict == verdict
    assert verifier_grandeur(att, rep).verdict == V.VALID  # sans consigne d'unité : équivalent accepté


@pytest.mark.parametrize("rep,cs,verdict", [
    ("1200 m", 2, V.NEEDS_HUMAN_REVIEW), ("1200 m", 3, V.NEEDS_HUMAN_REVIEW), ("1200 m", 4, V.VALID),
    ("1200 m", 5, V.INVALID), ("1,2 × 10^3 m", 2, V.VALID), ("1,20 × 10^3 m", 2, V.INVALID),
    ("1200,0 m", 2, V.INVALID),
])
def test_chiffres_significatifs_ambigus(rep, cs, verdict):
    assert verifier_grandeur("1200 m", rep, chiffres_significatifs_requis=cs).verdict == verdict


# --- incertitudes ------------------------------------------------------------------------------
@pytest.mark.parametrize("rep,verdict,raison", [
    ("(3,02 ± 0,05) m", V.VALID, None),
    ("3,02 ± 0,05 m", V.VALID, None),
    ("3,02 +/- 0,05 m", V.VALID, None),
    ("(3,02 ± 0,06) m", V.VALID, None),                     # arrondi par excès (0,0512 → 0,06)
    ("(3,021 ± 0,051) m", V.VALID, None),                   # 2 chiffres significatifs
    ("(302 ± 5) cm", V.VALID, None),                        # autre unité de même dimension
    ("(3,02 ± 0,0512) m", V.INVALID, "incertitude_trop_de_chiffres_significatifs"),
    ("(3,021 ± 0,05) m", V.INVALID, "valeur_et_incertitude_incoherentes"),
    ("(3,02 ± 0,07) m", V.INVALID, "incertitude_incorrecte"),
    ("(3,05 ± 0,05) m", V.INVALID, "valeur_incorrecte"),
    ("(3,02 ± 0,05)", V.INVALID, "unite_manquante"),
    ("(3,02 ± 0,05) s", V.INVALID, "dimension_incorrecte"),
    ("(3,02 ± 0) m", V.INVALID, "incertitude_non_positive"),
    ("3,02 m", V.INVALID, "incertitude_manquante"),
    ("environ 3 m", V.NEEDS_HUMAN_REVIEW, None),
    ("", V.INVALID, "reponse_vide"),
])
def test_incertitude(rep, verdict, raison):
    r = verifier_incertitude("3,0214 ± 0,0512 m", rep)
    assert r.verdict == verdict, r
    if raison:
        assert raison in r.raisons


def test_incertitude_puissance_de_dix():
    att = "(2,99792 ± 0,00041) × 10^8 m/s"
    assert verifier_incertitude(att, "(2,9979 ± 0,0004) × 10^8 m/s").verdict == V.VALID
    assert verifier_incertitude(att, "(2,9979 ± 0,0005) × 10^8 m/s").verdict == V.VALID   # par excès
    assert verifier_incertitude(att, "(299,79 ± 0,04) × 10^6 m/s").verdict == V.VALID
    assert verifier_incertitude(att, "(2,9979 ± 0,0004) × 10^7 m/s").verdict == V.INVALID
    # sans parenthèses, la puissance de dix est ambiguë ⇒ jamais validée
    assert verifier_incertitude(att, "2,9979 ± 0,0004 × 10^8 m/s").verdict != V.VALID


@pytest.mark.parametrize("texte", ["(1 ± 0,1) °C", "(" + "1" * 200 + " ± 1) m", "(1 ± 1) × 10^99 m"])
def test_mesure_refusee(texte):
    with pytest.raises(ValueError):
        analyser_mesure(texte)


# --- ordre de grandeur -------------------------------------------------------------------------
@pytest.mark.parametrize("att,rep,verdict", [
    ("3,0e8 m/s", "10^8 m/s", V.VALID),
    ("3,0e8 m/s", "10^9 m/s", V.INVALID),
    ("3,0e8 m/s", "10⁸ m/s", V.VALID),
    ("3,0e8 m/s", "1e8 m/s", V.VALID),
    ("3,0e8 m/s", "10^5 km/s", V.VALID),                   # 3,0 × 10^5 km/s
    ("3,0e8 m/s", "10^8", V.INVALID),                      # unité manquante
    ("3,0e8 m/s", "10^8 m", V.INVALID),
    ("3,0e8 m/s", "3 × 10^8 m/s", V.INVALID),              # pas une puissance de dix
    ("7,0e-3 m", "10^-2 m", V.VALID),                      # a ≥ 5 ⇒ n + 1
    ("7,0e-3 m", "10^-3 m", V.INVALID),
    ("4,0e2 J", "10^2 J", V.NEEDS_HUMAN_REVIEW),           # √10 ≤ a < 5 : conventions divergentes
    ("4,0e2 J", "10^3 J", V.NEEDS_HUMAN_REVIEW),
    ("4,0e2 J", "10^5 J", V.INVALID),
    ("6,0e23", "10^24", V.VALID),                          # sans dimension
    ("25 °C", "10^1 °C", V.NEEDS_HUMAN_REVIEW),
])
def test_ordre_de_grandeur(att, rep, verdict):
    assert verifier_ordre_de_grandeur(att, rep).verdict == verdict


# --- conversions -------------------------------------------------------------------------------
@pytest.mark.parametrize("dep,cible,rep,verdict", [
    ("72 km/h", "m/s", "20 m/s", V.VALID),
    ("72 km/h", "m/s", "20 m.s-1", V.VALID),
    ("72 km/h", "m/s", "20", V.INVALID),
    ("72 km/h", "m/s", "72 km/h", V.INVALID),              # équivalent mais pas dans l'unité cible
    ("72 km/h", "m/s", "0,02 km/s", V.INVALID),
    ("72 km/h", "m/s", "20 km/s", V.INVALID),              # bon nombre, mauvaise unité (même dimension)
    ("72 km/h", "m/s", "25 m/s", V.INVALID),
    ("1,5 L", "mL", "1500 mL", V.VALID),
    ("1,5 L", "m3", "1,5e-3 m3", V.VALID),
    ("2 kWh", "J", "7,2 × 10^6 J", V.VALID),
    ("250 mg", "g", "0,25 g", V.VALID),
    ("250 mg", "g", "2,5 g", V.INVALID),
    ("1 h", "s", "3600 s", V.VALID),
    ("72 km/h", "kg", "20 kg", V.NEEDS_HUMAN_REVIEW),      # consigne incohérente
    ("25 °C", "K", "298,15 K", V.NEEDS_HUMAN_REVIEW),      # température absolue : revue
])
def test_conversions(dep, cible, rep, verdict):
    assert verifier_conversion(dep, cible, rep).verdict == verdict


# --- constantes --------------------------------------------------------------------------------
@pytest.mark.parametrize("nom,rep,verdict", [
    ("c", "3,00 × 10^8 m/s", V.VALID),
    ("c", "2,998 × 10^8 m/s", V.VALID),
    ("c", "2,99 × 10^8 m/s", V.INVALID),                   # troncature
    ("c", "3,00 × 10^8", V.INVALID),                       # unité manquante
    ("c", "3,00 × 10^8 m", V.INVALID),
    ("c", "3 × 10^8 m/s", V.INVALID),                      # précision insuffisante (1 CS < 3)
    ("c", "3,00 × 10^5 km/s", V.VALID),
    ("N_A", "6,02 × 10^23 mol-1", V.VALID),
    ("N_A", "6,02 × 10^23", V.INVALID),
    ("e", "1,60 × 10^-19 C", V.VALID),
    ("h", "6,63 × 10^-34 J.s", V.VALID),
    ("h", "6,62 × 10^-34 J.s", V.INVALID),
    ("R", "8,31 J.mol-1.K-1", V.VALID),
    ("G", "6,67 × 10^-11 N.m2.kg-2", V.VALID),
    ("g", "9,81 m/s2", V.VALID),
    ("g", "9,81 N/kg", V.VALID),                           # même dimension
    ("g", "9,78 m/s2", V.VALID),                           # valeur locale plausible (< 0,5 %)
    ("g", "9,72 m/s2", V.NEEDS_HUMAN_REVIEW),
    ("g", "10,0 m/s2", V.INVALID),
    ("inconnue", "1 m", V.NEEDS_HUMAN_REVIEW),
])
def test_constantes(nom, rep, verdict):
    assert verifier_constante(nom, rep).verdict == verdict


def test_table_des_constantes_coherente():
    for nom, k in CONSTANTES.items():
        analyser_unite(k.unite)  # toutes les unités sont analysables
        assert float(k.valeur) > 0 and k.origine
        assert verifier_constante(nom, f"{float(k.valeur):.4e} {k.unite}".replace("e", " × 10^")).verdict == V.VALID
    # R est bien N_A × k_B (valeur exacte déclarée exacte)
    from decimal import Decimal
    assert Decimal(CONSTANTES["N_A"].valeur) * Decimal(CONSTANTES["k_B"].valeur) == Decimal(CONSTANTES["R"].valeur)


def test_dispatch_physique_unite_imposee():
    assert verifier("physique_grandeur", "20 m/s", "72 km/h", {"unite_imposee": True}).verdict == V.INVALID
    assert verifier("physique_grandeur", "20 m/s", "20", {"unite_requise": False}).verdict == V.INVALID


@pytest.mark.parametrize("appel", [
    lambda: verifier_incertitude("(1 ± 0,1) m", "(" + "9" * 110 + " ± 1) m"),
    lambda: verifier_ordre_de_grandeur("1 m", "10^" + "9" * 500 + " m"),
    lambda: verifier_conversion("1 m", "km", "1" * 99 + " km"),
    lambda: verifier_constante("c", "9" * 99 + " m/s"),
])
def test_entrees_hostiles_bornees(appel):
    t = time.perf_counter()
    r = appel()
    assert time.perf_counter() - t < 1 and r.verdict in (V.NEEDS_HUMAN_REVIEW, V.INVALID)


def test_dispatch_incertitude_et_ordre_de_grandeur():
    assert verifier("physique_incertitude", "(3,02 ± 0,05) m", "(302 ± 5) cm").verdict == V.VALID
    assert verifier("physique_incertitude", "(3,02 ± 0,05) m", "3,02 m").verdict == V.INVALID
    p = {"valeur": "3,0e8 m/s"}
    assert verifier("physique_ordre_de_grandeur", "10^8 m/s", "10^8 m/s", p).verdict == V.VALID
    assert verifier("physique_ordre_de_grandeur", "10^8 m/s", "10^9 m/s", p).verdict == V.INVALID
    # attendue incohérente ou convention ambiguë : non publiable (auto-vérification ≠ VALID)
    assert verifier("physique_ordre_de_grandeur", "10^9 m/s", "10^9 m/s", p).verdict == V.NEEDS_HUMAN_REVIEW
    q = {"valeur": "4,0e2 J"}
    assert verifier("physique_ordre_de_grandeur", "10^2 J", "10^2 J", q).verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier("physique_ordre_de_grandeur", "10^8 m/s", "10^8 m/s", {}).verdict == V.NEEDS_HUMAN_REVIEW
    assert verifier("physique_ordre_de_grandeur", "10^8 m/s", "10^8 m/s",
                    dict(p, autre=1)).verdict == V.NEEDS_HUMAN_REVIEW
