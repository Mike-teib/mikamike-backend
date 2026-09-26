"""
Qualité du texte extrait — détecteurs session 4 (lot 7) : cas défectueux ET témoins sains.
Une heuristique ne fait que BLOQUER : elle ne rend jamais une notion PROVEN (dernier test).
"""

import pytest

from app.curriculum.model import StatutTexte as S
from app.curriculum.text_quality import analyser_texte

UTILISABLES = {S.TEXT_EXACT, S.TEXT_RECOVERED}


@pytest.mark.parametrize("texte,anomalie,statut", [
    ("Écrire la fraction 1\n10 sous forme décimale.", "fraction_aplatie", S.FORMULA_CORRUPTED),
    ("Lire la fraction 3 4 à voix haute.", "fraction_aplatie", S.FORMULA_CORRUPTED),
    ("NOMBRES ET CALCULS Comparer des nombres entiers.", "titre_absorbe", S.COLUMN_CONTAMINATION),
    ("ESPACE ET GÉOMÉTRIE Reconnaître un triangle rectangle.", "titre_absorbe", S.COLUMN_CONTAMINATION),
    ("Résoudre un prob1ème de proportionnalité.", "ocr_incoherent", S.FORMULA_CORRUPTED),
    ("Utiliser la l0gique d'un algorithme simple.", "ocr_incoherent", S.FORMULA_CORRUPTED),
    ("Comparer des fractions | Connaissances associées.", "cellules_tableau_fusionnees", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions\tde même dénominateur.", "cellules_tableau_fusionnees", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions de même\n12\ndénominateur.", "numero_de_page_parasite", S.COLUMN_CONTAMINATION),
    ("Comparer des fractions simples. Comparer des fractions simples.", "phrase_dupliquee", S.AMBIGUOUS),
    ("Comparer des fr‮actions simples.", "unicode_anormal", S.FORMULA_CORRUPTED),
    ("Résoudre un еxercice de calcul.", "unicode_anormal", S.FORMULA_CORRUPTED),  # « е » cyrillique
    ("Comparer des\x07 fractions simples.", "unicode_anormal", S.FORMULA_CORRUPTED),
])
def test_defaut_detecte(texte, anomalie, statut):
    r = analyser_texte(texte)
    assert anomalie in r.anomalies and r.statut == statut and r.statut not in UTILISABLES


@pytest.mark.parametrize("texte", [
    "Utiliser l'écriture fractionnaire 1/10 et 1/100 pour les nombres décimaux.",
    "La fraction 3/4 se lit trois quarts.",
    "Le quotient de 12 par 4 est égal à 3.",
    "Connaître la formule de l'eau H2O et du dioxyde de carbone CO2.",
    "Écrire l'équation de réaction avec Na2SO4 en solution aqueuse.",
    "Calculer le PGCD PPCM de deux entiers.",
    "Calculer 3 × 4 + 2 et justifier les priorités opératoires.",
    "Connaître les tables de multiplication de 2 à 9.",
    "Utiliser x² + 2x + 1 = (x + 1)² pour factoriser.",
    "Mesurer une longueur de 12 cm avec une règle graduée.",
])
def test_temoins_sains_non_bloques(texte):
    r = analyser_texte(texte)
    assert r.statut in UTILISABLES, (r.statut, r.anomalies)


def test_heuristique_ne_rend_jamais_prouve():
    """Un texte parfaitement sain SANS preuve source reste NOT_EVIDENCED : la qualité du texte
    peut seulement bloquer, jamais prouver (preuve source > structure > heuristique)."""
    from app.curriculum.fixtures import referentiel_fictif
    from app.curriculum.model import StatutPreuve
    from app.curriculum.provenance import evaluer_preuve

    idx = referentiel_fictif().index()
    n = idx.notions["notion:fictif:sans-preuve"].model_copy(
        update={"texte": "Comparer des fractions de même dénominateur.", "statut_texte": S.TEXT_EXACT})
    assert analyser_texte(n.texte).statut == S.TEXT_EXACT
    assert evaluer_preuve(n, None, autoriser_fictif=True).statut == StatutPreuve.NOT_EVIDENCED


def test_texte_d_une_page_voisine_detecte_par_la_source():
    extrait = "Comparer, ranger et encadrer des fractions de même dénominateur."
    r = analyser_texte("Reconnaître et nommer les solides usuels.", extrait_source=extrait)
    assert "absent_de_la_source" in r.anomalies and r.statut == S.SOURCE_NOT_EVIDENCED
