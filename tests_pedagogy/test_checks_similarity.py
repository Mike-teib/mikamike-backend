"""checks.similarity : normalisation, empreintes exacte / gabarit, Jaccard 3-grammes."""

from pedagogy.checks.similarity import (
    exact_fingerprint,
    jaccard,
    normalize_text,
    shingles,
    similarity,
    template_fingerprint,
)


def test_normalisation():
    assert normalize_text("  Calculer   3 x + 2 = 8 ") == normalize_text("calculer 3 x+2=8")
    assert normalize_text("L’eau") == "l'eau"


def test_empreinte_exacte():
    assert exact_fingerprint("[FICTIF] Calculer 2+3", "5") == exact_fingerprint("[fictif]  calculer 2 + 3", "5")
    assert exact_fingerprint("[FICTIF] Calculer 2+3", "5") != exact_fingerprint("[FICTIF] Calculer 2+3", "6")
    assert len(exact_fingerprint("a")) == 64


def test_empreinte_gabarit_masque_les_nombres():
    assert template_fingerprint("Résoudre 3x + 2 = 8") == template_fingerprint("Résoudre 5x + 1 = 11")
    assert template_fingerprint("Résoudre 3x + 2 = 8") != template_fingerprint("Développer 3x + 2 = 8")
    assert template_fingerprint("Calculer 0,5 + 1,25") == template_fingerprint("Calculer 7 + 3")


def test_jaccard_3grammes():
    a = "[FICTIF] Une voiture parcourt 150 km en 2 h. Calculer sa vitesse moyenne."
    b = "[FICTIF] Une voiture parcourt 150 km en 2 h. Calculer sa vitesse moyenne en km/h."
    c = "[FICTIF] Quel gaz est rejeté par les végétaux à la lumière ?"
    assert similarity(a, a) == 1.0
    assert similarity(a, b) > 0.7
    assert similarity(a, c) < 0.1
    assert jaccard(frozenset(), frozenset()) == 1.0
    assert shingles("deux mots") == frozenset({"deux mots"})
    assert shingles("") == frozenset()
