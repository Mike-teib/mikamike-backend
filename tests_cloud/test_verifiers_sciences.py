"""Vérificateurs Physique-Chimie, SVT, Sciences & technologie, Enseignement scientifique."""

import pytest

from app.curriculum.model import Matiere, Niveau, Notion
from app.curriculum.verifiers.base import Verdict
from app.curriculum.verifiers.dispatch import verifier
from app.curriculum.verifiers.enseignement_scientifique import verifier_notion_es, verifier_rattachement
from app.curriculum.verifiers.physique import chiffres_significatifs, verifier_grandeur, verifier_homogeneite
from app.curriculum.verifiers.svt import (
    verifier_chaine_causale,
    verifier_classification,
    verifier_explication_causale,
    verifier_niveaux_organisation,
    verifier_prudence,
    verifier_vocabulaire,
)
from app.curriculum.verifiers.technologie import (
    CHAINE_ENERGIE_DEFAUT,
    CHAINE_INFORMATION_DEFAUT,
    verifier_affectation,
    verifier_bilan_energetique,
    verifier_chaine,
    verifier_cycle_de_vie,
    verifier_vues,
)

V, I, A, R = Verdict.VALID, Verdict.INVALID, Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW


# --------------------------------------------------------------------------- #
# Physique-Chimie
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("attendue,reponse,verdict", [
    ("3,0 × 10^8 m/s", "3,0.10⁸ m·s⁻¹", V),
    ("12 km/h", "3,333 m/s", V),
    ("2,5 kg", "2500 g", V),
    ("2,5 kg", "2,5", I),            # pas de résultat sans unité
    ("2,5 kg", "2,5 m", I),          # mauvaise dimension
    ("2,5 kg", "3 kg", I),
    ("0,10 mol/L", "0,10 mol.L-1", V),
    ("25 °C", "298,15 K", V),
    ("1 kWh", "3,6e6 J", V),
    ("5 N", "5 kg.m.s-2", V),
    ("10 mA", "0,01 A", V),
    ("1 A", "1 truc", R),
    ("1 A", "", I),
])
def test_grandeurs(attendue, reponse, verdict):
    assert verifier_grandeur(attendue, reponse).verdict == verdict


def test_notation_scientifique_et_chiffres_significatifs():
    assert verifier_grandeur("3,0e8 m/s", "300000000 m/s", notation_scientifique=True).verdict == I
    assert verifier_grandeur("3,0e8 m/s", "30 × 10^7 m/s", notation_scientifique=True).verdict == I
    assert verifier_grandeur("3,0e8 m/s", "3,0 × 10^8 m/s", notation_scientifique=True).verdict == V
    assert verifier_grandeur("3,0e8 m/s", "3e8 m/s", chiffres_significatifs_requis=2).verdict == I
    assert chiffres_significatifs("0,0450") == 3
    assert chiffres_significatifs("3,0") == 2


def test_unite_optionnelle_si_non_requise():
    assert verifier_grandeur("2,5", "2,5").verdict == V
    assert verifier_grandeur("2,5 kg", "2,5", unite_requise=False).verdict == I  # dimension quand même


@pytest.mark.parametrize("formule,unites,verdict", [
    ("E = m*c^2", {"E": "J", "m": "kg", "c": "m/s"}, V),
    ("E = m*c", {"E": "J", "m": "kg", "c": "m/s"}, I),
    ("U = R*I", {"U": "V", "R": "Ω", "I": "A"}, V),
    ("Ec = 1/2*m*v^2", {"Ec": "J", "m": "kg", "v": "m/s"}, V),
    ("x = d + t", {"x": "m", "d": "m", "t": "s"}, I),
    ("T = 2*pi*sqrt(l/g)", {"T": "s", "l": "m", "g": "m/s^2"}, V),
    ("x = exp(t)", {"x": "m", "t": "s"}, I),
    ("P = U*I", {"P": "W", "U": "V"}, R),                     # I non déclaré
    ("P = __import__('os')", {"P": "W"}, R),
])
def test_homogeneite(formule, unites, verdict):
    assert verifier_homogeneite(formule, unites).verdict == verdict


# --------------------------------------------------------------------------- #
# SVT
# --------------------------------------------------------------------------- #
def test_vocabulaire():
    assert verifier_vocabulaire("La mitose produit deux cellules filles", ["mitose", "cellule fille"]).verdict == V
    assert verifier_vocabulaire("La méiose produit des cellules", ["mitose"]).verdict == I
    assert verifier_vocabulaire("Le sang transporte le dioxygène", ["dioxygène"],
                                termes_errones=["sang"]).verdict == I
    assert verifier_vocabulaire("L'ADN polymérase copie", ["ADN"], termes_hors_niveau=["polymérase"]).verdict == A
    assert verifier_vocabulaire("", ["x"]).verdict == I


def test_chaine_causale_et_explication():
    att = ["infection", "anticorps", "neutralisation"]
    assert verifier_chaine_causale(["infection", "production d'anticorps", "neutralisation"], att).verdict == V
    assert verifier_chaine_causale(["neutralisation", "infection", "anticorps"], att).verdict == I
    assert verifier_chaine_causale(["infection", "neutralisation"], att).verdict == I
    ok = "L'évaporation augmente car la température augmente"
    assert verifier_explication_causale(ok, "température augmente", "évaporation augmente").verdict == V
    inverse = "L'évaporation augmente donc la température augmente"
    assert verifier_explication_causale(inverse, "température augmente", "évaporation augmente").verdict == I
    sans_lien = "La température augmente. L'évaporation augmente."
    assert verifier_explication_causale(sans_lien, "température augmente", "évaporation augmente").verdict == I


def test_niveaux_organisation_et_classification():
    assert verifier_niveaux_organisation(["molécules", "cellule", "tissu", "organe"]).verdict == V
    assert verifier_niveaux_organisation(["écosystème", "population", "organisme"]).verdict == V
    assert verifier_niveaux_organisation(["cellule", "molécule", "organe"]).verdict == I
    assert verifier_niveaux_organisation(["cellule", "galaxie"]).verdict == R
    cle = {"vertébrés": ["chat", "truite"], "invertébrés": ["escargot"]}
    assert verifier_classification({"vertébrés": ["chat", "truite"], "invertébrés": ["escargot"]}, cle).verdict == V
    assert verifier_classification({"vertébrés": ["chat"], "invertébrés": ["escargot", "truite"]}, cle).verdict == I
    assert verifier_classification({"vertébrés": ["chat", "truite"]}, cle).verdict == I


def test_prudence_sur_notion_ambigue():
    assert verifier_prudence("Cela arrive toujours", notion_ambigue=True).verdict == R
    assert verifier_prudence("Cela arrive souvent", notion_ambigue=True).verdict == V
    assert verifier_prudence("Cela arrive toujours", notion_ambigue=False).verdict == V


# --------------------------------------------------------------------------- #
# Sciences & technologie
# --------------------------------------------------------------------------- #
def test_chaines_information_energie():
    assert verifier_chaine(["Acquérir", "Traiter", "Communiquer"], CHAINE_INFORMATION_DEFAUT).verdict == V
    assert verifier_chaine(["Traiter", "Acquérir", "Communiquer"], CHAINE_INFORMATION_DEFAUT).verdict == I
    assert verifier_chaine(["alimenter", "convertir", "transmettre"], CHAINE_ENERGIE_DEFAUT).verdict == I
    assert verifier_chaine(["alimenter", "distribuer", "convertir", "transmettre", "voler"],
                           CHAINE_ENERGIE_DEFAUT).verdict == I


def test_affectation_composants():
    cle = {"capteur": "acquerir", "microcontroleur": "traiter", "moteur": "convertir"}
    assert verifier_affectation({"Capteur": "Acquérir", "microcontrôleur": "traiter", "moteur": "convertir"}, cle).verdict == V
    assert verifier_affectation({"capteur": "traiter", "microcontroleur": "traiter", "moteur": "convertir"}, cle).verdict == I
    assert verifier_affectation({"capteur": "acquerir"}, cle).verdict == I
    assert verifier_affectation({"licorne": "acquerir"}, cle).verdict == R


def test_bilan_energetique():
    assert verifier_bilan_energetique("100 J", "80 J", 0.8).verdict == V
    assert verifier_bilan_energetique("100 J", "80 J", 80).verdict == V
    assert verifier_bilan_energetique("100 J", "120 J").verdict == I
    assert verifier_bilan_energetique("100 J", "80 J", 0.9).verdict == I
    assert verifier_bilan_energetique("1 kWh", "3,6e6 J").verdict == V
    assert verifier_bilan_energetique("100", "80 J").verdict == I
    assert verifier_bilan_energetique("100 J", "80 m").verdict == I


def test_cycle_de_vie_et_vues():
    assert verifier_cycle_de_vie(["Extraction", "Fabrication", "Distribution", "Utilisation", "Fin de vie"]).verdict == V
    assert verifier_cycle_de_vie(["Fabrication", "Extraction", "Distribution", "Utilisation", "Fin de vie"]).verdict == I
    assert verifier_vues({"vue de face": "A", "vue de dessus": "B"}, {"face": "A", "dessus": "B"}).verdict == V
    assert verifier_vues({"vue de face": "B", "vue de dessus": "A"}, {"face": "A", "dessus": "B"}).verdict == I
    assert verifier_vues({"vue oblique": "A"}, {"face": "A"}).verdict == R


# --------------------------------------------------------------------------- #
# Enseignement scientifique
# --------------------------------------------------------------------------- #
def test_rattachement_pluridisciplinaire():
    pluri = {Matiere.PHYSIQUE_CHIMIE, Matiere.SVT}
    assert verifier_rattachement(Matiere.ENSEIGNEMENT_SCIENTIFIQUE, pluri).verdict == V
    assert verifier_rattachement(Matiere.SVT, pluri).verdict == I       # forcé dans une matière
    assert verifier_rattachement(Matiere.SVT, {Matiere.SVT}).verdict == V
    assert verifier_rattachement(Matiere.PHYSIQUE_CHIMIE, {Matiere.SVT}).verdict == I
    assert verifier_rattachement(Matiere.SVT, None).verdict == R


def test_notion_es_disciplines_conformes():
    n = Notion(id="notion:fictif:es", programme_id="prog:fictif:es", niveau=Niveau.PREMIERE,
               matiere=Matiere.ENSEIGNEMENT_SCIENTIFIQUE, texte="[FICTIF] Notion ES",
               disciplines_mobilisees=(Matiere.PHYSIQUE_CHIMIE, Matiere.SVT))
    assert verifier_notion_es(n, {Matiere.PHYSIQUE_CHIMIE, Matiere.SVT}).verdict == V
    assert verifier_notion_es(n, {Matiere.SVT}).verdict == I
    assert verifier_notion_es(n, {Matiere.SVT, Matiere.PHYSIQUE_CHIMIE, Matiere.MATHEMATIQUES}).verdict == I
    assert verifier_notion_es(n, None).verdict == R


# --------------------------------------------------------------------------- #
# Dispatcher : jamais VALID par défaut
# --------------------------------------------------------------------------- #
def test_dispatch_type_inconnu_et_parametres_invalides():
    assert verifier("inconnu", "1", "1").verdict == R
    assert verifier("physique_grandeur", "1 m", "1 m", {"parametre_invente": 1}).verdict == R
    assert verifier("texte_exact", "Mitose", " mitose ").verdict == V
    assert verifier("texte_exact", "Mitose", "Méiose").verdict == I
    assert verifier("texte_exact", "Mitose", "").verdict == I
