"""checks.physics : grandeurs, unités, dimensions, chiffres significatifs, homogénéité, bornes."""

import pytest

from pedagogy.checks.physics import (
    DIMENSIONLESS,
    PHYSICAL_BOUNDS,
    QuantityError,
    check_homogeneity,
    check_physical_plausibility,
    check_quantity,
    find_quantity_in_text,
    format_significant,
    parse_quantity,
    parse_unit,
    physical_bound_violations,
    significant_figures,
    units_implied_by_text,
)
from pedagogy.checks.verdict import Verdict

V, I, R = Verdict.VALID, Verdict.INVALID, Verdict.NEEDS_HUMAN_REVIEW


@pytest.mark.parametrize("expected,answer,verdict", [
    ("3,0e8 m/s", "3,0 × 10^8 m/s", V),
    ("3,0e8 m/s", "3,0.10⁸ m·s⁻¹", V),
    ("0,25 kg", "250 g", V),
    ("0,25 kg", "250", I),            # unité manquante
    ("0,25 kg", "250 m", I),          # dimension
    ("20 m/s", "72 km/h", V),
    ("20 m/s", "72 km", I),
    ("0,10 mol/L", "100 mmol/L", V),
    ("1200 m", "1 200 m", V),
    ("0,25 kg", "$2{,}5 \\times 10^{-1}$ kg", V),
    ("25 °C", "298,15 K", V),
    ("2 Bq", "2 s^-1", V),
    ("2 jours", "48 h", V),
    ("1 an", "365,25 jours", V),
    ("180 °", "3,141592653589793 rad", V),
    ("12 €", "12 euros", V),
    ("5 m", "5 furlongs", R),         # unité inconnue
    ("5 m", "cinq mètres", R),
    ("5 m", "", I),
    ("5 m", "5,2 m", I),
])
def test_check_quantity(expected, answer, verdict):
    assert check_quantity(expected, answer).verdict == verdict


def test_tolerance_et_chiffres_significatifs():
    assert check_quantity("9,81 m/s^2", "9,8 m/s^2", tolerance_relative=0.01).verdict == V
    assert check_quantity("9,81 m/s^2", "9,8 m/s^2", tolerance_relative=0.0001).verdict == I
    assert check_quantity("9,81 m/s^2", "9,81 m/s^2", tolerance_relative=0).verdict == V
    assert check_quantity("0,250 kg", "0,25 kg", required_sig_figs=3).verdict == I
    assert check_quantity("0,250 kg", "0,250 kg", required_sig_figs=3).verdict == V
    assert check_quantity("1200 m", "1200 m", required_sig_figs=2).verdict == R  # zéros finaux ambigus
    assert check_quantity("3e8 m/s", "300000000 m/s", scientific_notation=True).verdict == I
    assert check_quantity("3e8 m/s", "3 × 10^8 m/s", scientific_notation=True).verdict == V
    assert check_quantity("20 m/s", "72 km/h", unit_imposed=True).verdict == I
    assert check_quantity("5 m", "5 m", tolerance_relative=0.9).verdict == R


def test_unites_et_significatifs():
    assert parse_unit("kg·m^-2").dim == (-2, 1, 0, 0, 0, 0, 0)
    assert parse_unit("joules").dim == parse_unit("J").dim
    assert parse_unit("Bq").dim == parse_unit("s^-1").dim
    assert parse_unit("jour").dim == parse_unit("h").dim
    assert parse_unit("€").dim == DIMENSIONLESS
    assert parse_unit("").dim == DIMENSIONLESS
    with pytest.raises(QuantityError):
        parse_unit("xyz")
    with pytest.raises(QuantityError):
        parse_quantity("1e999 m")
    assert significant_figures("0,00250") == 3
    assert format_significant(0.25, 3) == "0,250"
    assert format_significant(3e8, 2) == "3,0 × 10^8"


def test_unites_annoncees_par_l_enonce():
    implied = [t for t, _ in units_implied_by_text(
        "Calculer la vitesse en m/s puis l'énergie en joules. En l’absence de frottement, en effet…")]
    assert implied == ["m/s", "joules"]
    assert [t for t, _ in units_implied_by_text("rectangle en A", ignore_single_capitals=True)] == []
    assert [t for t, _ in units_implied_by_text("Exprimer I en A.")] == ["A"]


@pytest.mark.parametrize("q,context,violated", [
    ("4,0 × 10^8 m/s", "", True), ("-4,0e8 m/s", "", True), ("3,0e8 m/s", "", False),
    ("-5 K", "", True), ("-300 °C", "", True), ("-20 °C", "", False),
    ("0 kg", "", True), ("-2 g", "", True), ("2 g", "", False),
    ("-0,1 mol/L", "", True), ("0,1 mol/L", "", False), ("-3 g/L", "", True),
    ("1,2", "Le rendement du moteur", True), ("120 %", "rendement", True), ("35 %", "rendement", False),
    ("15", "Le pH de la solution diluée", True), ("-1", "pH", True), ("7", "pH", False),
    ("15", "un nombre sans contexte", False),
    ("illisible", "", False),
])
def test_bornes_physiques(q, context, violated):
    assert bool(check_physical_plausibility(q, context)) is violated


def test_table_des_bornes():
    names = {b.name for b in PHYSICAL_BOUNDS}
    for key in ("vitesse", "temperature", "masse", "concentration", "rendement", "pH"):
        assert any(key in n for n in names)
    assert physical_bound_violations(1.0, (1, 0, -1, 0, 0, 0, 0)) == []


def test_recherche_grandeur_dans_texte():
    assert find_quantity_in_text("20 m/s", "donc v = 72/3,6 = 20 m/s.")
    assert find_quantity_in_text("75 km/h", "v = 150 / 2 = 75")          # nombre seul, unité de l'attendu
    assert not find_quantity_in_text("20 m/s", "donc v = 21 m/s")
    assert find_quantity_in_text("0,0015 kg", "m = 1,5 × 10^-3 kg")


@pytest.mark.parametrize("formula,units,verdict", [
    ("E = m*c^2", {"E": "J", "m": "kg", "c": "m/s"}, V),
    ("E = m*c", {"E": "J", "m": "kg", "c": "m/s"}, I),
    ("v = d/t", {"v": "m/s", "d": "m", "t": "s"}, V),
    ("v = d + t", {"v": "m/s", "d": "m", "t": "s"}, I),
    ("E = m*g*h", {"E": "J", "m": "kg", "g": "N/kg", "h": "m"}, V),
    ("x = exp(t)", {"x": "m", "t": "s"}, I),
    ("E = m*c^2", {"E": "J", "m": "kg"}, R),                 # variable non déclarée
    ("E = __import__('os')", {"E": "J"}, R),
    ("E = m.n", {"E": "J", "m": "kg"}, R),
])
def test_homogeneite(formula, units, verdict):
    assert check_homogeneity(formula, units).verdict == verdict
