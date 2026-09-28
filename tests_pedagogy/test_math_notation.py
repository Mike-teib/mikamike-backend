"""checks.math_notation : intégrité LaTeX/Unicode et préservation source → sortie."""

import pytest

from pedagogy.checks.math_notation import (
    apply_preserving_math,
    integrity_anomalies,
    is_notation_ok,
    latex_to_plain,
    preservation_anomalies,
    protect,
    restore,
)


# --------------------------------------------------------------------------- #
# Exemples exigés
# --------------------------------------------------------------------------- #
def test_fraction_1_10_convertie_en_0_1_est_signalee():
    src = "[FICTIF] Dans le texte source, on prend 1/10 du volume."
    out = "[FICTIF] Dans le texte source, on prend 0,1 du volume."
    assert "FRACTION_CONVERTED:1/10" in preservation_anomalies(src, out)
    assert "FRACTION_CONVERTED:1/10" in preservation_anomalies(src, out.replace("0,1", "0.1"))


def test_perte_d_exposant_x2():
    assert "EXPONENT_LOST" in preservation_anomalies("Calculer x^2 + 1", "Calculer x2 + 1")
    assert "EXPONENT_LOST" in preservation_anomalies("Calculer x² + 1", "Calculer x2 + 1")


def test_perte_d_exposant_10_moins_3():
    assert "EXPONENT_LOST" in preservation_anomalies("m = 10^{-3} kg", "m = 10-3 kg")
    assert "EXPONENT_LOST" in preservation_anomalies("$m = 10^{-3}$ kg", "$m = 10{-3}$ kg")
    assert "EXPONENT_LOST" in preservation_anomalies("m = 10⁻³ kg", "m = 10-3 kg")
    assert preservation_anomalies("m = 10^{-3} kg", "m = 10^{-3} kg") == []


def test_parentheses_modifiees():
    assert "PARENTHESES_CHANGED" in preservation_anomalies("Développer (a + b)(a - b)", "Développer a + b(a - b)")
    assert "PARENTHESES_CHANGED" in preservation_anomalies("f(x) = 2(x+1)", "f(x) = 2x+1")


@pytest.mark.parametrize("src,out,code", [
    ("Utiliser 1/100", "Utiliser 1 100", "FRACTION_LOST:1/100"),
    ("$\\frac{1}{2}$", "$1 2$", "LATEX_FRAC_LOST"),
    ("Calculer √2 × 3", "Calculer 2 × 3", "ROOT_LOST"),
    ("$\\sqrt{2}$", "$2$", "ROOT_LOST"),
    ("Si x ≤ 3 alors", "Si x < 3 alors", "SYMBOL_CHANGED"),
    ("a = b", "a b", "OPERATOR_CHANGED"),
    ("$u_{n+1}$", "$un+1$", "SUBSCRIPT_LOST"),
    ("π r²", "� r²", "NEW_INTEGRITY:REPLACEMENT_CHAR"),
    ("$x$", "$x", "NEW_INTEGRITY:DOLLAR_UNBALANCED"),
])
def test_alterations(src, out, code):
    assert code in preservation_anomalies(src, out)


def test_texte_identique_sans_anomalie():
    t = "Calculer (a + b)² = a² + 2ab + b², puis 1/10 de 10^3, $\\frac{3}{4}$ et √2 ≤ 2"
    assert preservation_anomalies(t, t) == []


# --------------------------------------------------------------------------- #
# Intégrité d'un texte seul
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,code", [
    ("Soit $x = 2", "DOLLAR_UNBALANCED"),
    ("Soit \\(x = 2", "LATEX_DELIM_UNBALANCED"),
    ("$\\frac{1}{2$", "BRACES_UNBALANCED"),
    ("$(a+b$", "MATH_BRACKETS_UNBALANCED"),
    ("$\\frac{1}$", "FRAC_INCOMPLETE"),
    ("$\\frac$", "FRAC_INCOMPLETE"),
    ("$\\sqrt$", "SQRT_INCOMPLETE"),
    ("$x^$", "SCRIPT_DANGLING"),
    ("$x_{}$ et $y^ = 2$", "SCRIPT_DANGLING"),
    ("Calculer frac{1}{2}", "LATEX_BACKSLASH_LOST"),
    ("a times b", "LATEX_BACKSLASH_LOST"),
    ("Valeur : 3�", "REPLACEMENT_CHAR"),
    ("Symbole  perdu", "PRIVATE_USE_CHAR"),
    ("texte\x07", "CONTROL_CHAR"),
])
def test_integrite_defauts(text, code):
    assert code in integrity_anomalies(text)


@pytest.mark.parametrize("text", [
    "[FICTIF] Calculer $\\frac{3}{4} + \\frac{1}{2}$.",
    "Soit $x \\in ]2 ; 5[$ un réel.",
    "$\\frac12$ et $\\sqrt[3]{8}$ et $\\sqrt 2$",
    "Le prix passe de 10 $ à 12 $.".replace("$", "\\$"),
    "Développer $(x+1)^2$ puis $u_{n}$ et $10^{-3}$",
    "La température est de 20 °C ; x² + 1 ≥ 1 ; 1/2 + 1/3 = 5/6.",
    "$$\\int_0^1 x \\, dx = \\frac{1}{2}$$",
    "Les temps de parcours sont 2 h et 3 h.",
])
def test_integrite_textes_corrects(text):
    assert integrity_anomalies(text) == []
    assert is_notation_ok(text)


# --------------------------------------------------------------------------- #
# Transformation protégée & conversion linéaire
# --------------------------------------------------------------------------- #
def test_transformation_sans_toucher_aux_maths():
    source = "Calculer   1/10   de (x+1)^2  et  x² ≤ 3"
    out = apply_preserving_math(source, lambda t: " ".join(t.split()).upper())
    assert "1/10" in out and "(x+1)^2" in out and "x² ≤ 3" in out
    assert preservation_anomalies(source, out) == []


def test_jeton_altere_detecte():
    masked, exprs = protect("Calculer 1/10 de 20")
    assert exprs
    with pytest.raises(ValueError):
        restore(masked.replace("⁣", ""), exprs)


def test_latex_to_plain():
    assert latex_to_plain("$\\frac{3}{4} \\times 10^{-3}$") == "((3)/(4)) × 10^(-3)"
    assert latex_to_plain("\\sqrt{x}") == "sqrt(x)"
    assert latex_to_plain("\\dfrac{\\frac{1}{2}}{3}") == "((((1)/(2)))/(3))"
    assert latex_to_plain("sans latex 1/2") == "sans latex 1/2"
