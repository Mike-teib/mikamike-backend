"""
technologie.py — Contrôles déterministes pour Sciences & technologie.

Système / fonction / énergie / chaîne d'information / chaîne d'énergie /
matériaux / impact environnemental / représentation technique.

Les découpages fonctionnels par défaut ci-dessous sont l'usage courant en
technologie au collège ; ils restent PARAMÉTRABLES (chaque exercice validé peut
fournir le découpage exact de sa source) et doivent être confirmés contre le
programme importé (cf. CLOUD_DATA_MODEL.md).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Mapping, Optional, Sequence, Tuple

from app.curriculum.verifiers.base import Resultat, invalide, revue, valide
from app.curriculum.verifiers.physique import GrandeurInvalide, analyser_grandeur

CHAINE_INFORMATION_DEFAUT: Tuple[str, ...] = ("acquerir", "traiter", "communiquer")
CHAINE_ENERGIE_DEFAUT: Tuple[str, ...] = ("alimenter", "distribuer", "convertir", "transmettre")
CYCLE_DE_VIE_DEFAUT: Tuple[str, ...] = (
    "extraction", "fabrication", "distribution", "utilisation", "fin de vie",
)
VUES_NORMALISEES = frozenset({"face", "dessus", "gauche", "droite", "dessous", "arriere", "perspective"})


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", t).split())


def verifier_chaine(blocs_eleve: Sequence[str], attendue: Sequence[str]) -> Resultat:
    """Les blocs fonctionnels doivent être exactement ceux attendus, dans l'ordre."""
    if not blocs_eleve:
        return invalide("reponse_vide")
    e = [_norm(b) for b in blocs_eleve]
    a = [_norm(b) for b in attendue]
    if set(e) - set(a):
        return invalide(*(f"bloc_inattendu:{b}" for b in sorted(set(e) - set(a))))
    if set(a) - set(e):
        return invalide(*(f"bloc_manquant:{b}" for b in sorted(set(a) - set(e))))
    if e != a:
        return invalide("ordre_des_blocs_incorrect")
    return valide("chaine_correcte")


def verifier_affectation(affectation: Mapping[str, str], cle: Mapping[str, str]) -> Resultat:
    """Composant → fonction (ex. « capteur » → « acquerir ») selon la clé de l'exercice."""
    if not affectation:
        return invalide("reponse_vide")
    cle_n = {_norm(k): _norm(v) for k, v in cle.items()}
    erreurs = []
    for comp, fonction in affectation.items():
        c = _norm(comp)
        if c not in cle_n:
            return revue(f"composant_hors_cle:{comp}")
        if cle_n[c] != _norm(fonction):
            erreurs.append(f"mauvaise_fonction:{comp}")
    manquants = sorted(set(cle_n) - {_norm(c) for c in affectation})
    if erreurs:
        return invalide(*erreurs)
    if manquants:
        return invalide(*(f"composant_non_affecte:{m}" for m in manquants))
    return valide("affectation_correcte")


def verifier_bilan_energetique(
    energie_absorbee: str,
    energie_utile: str,
    rendement_annonce: Optional[float] = None,
    *,
    tolerance: float = 0.01,
) -> Resultat:
    """Conservation : utile ≤ absorbée ; rendement η = utile / absorbée ∈ [0, 1]."""
    try:
        ga, gu = analyser_grandeur(energie_absorbee), analyser_grandeur(energie_utile)
    except GrandeurInvalide as exc:
        return revue(str(exc))
    if not ga.unite_texte or not gu.unite_texte:
        return invalide("unite_manquante")
    if ga.unite.dim != gu.unite.dim:
        return invalide("dimension_incorrecte")
    ea, eu = ga.valeur * ga.unite.facteur, gu.valeur * gu.unite.facteur
    if ea <= 0 or eu < 0:
        return invalide("energie_non_positive")
    if eu > ea * (1 + 1e-9):
        return invalide("energie_utile_superieure_a_absorbee")
    eta = eu / ea
    if rendement_annonce is not None:
        r = rendement_annonce / 100 if rendement_annonce > 1 else rendement_annonce
        if not 0 <= r <= 1:
            return invalide("rendement_hors_bornes")
        if abs(r - eta) > tolerance:
            return invalide("rendement_incorrect")
    return valide(f"rendement={eta:.3f}")


def verifier_classement_materiaux(affectation: Mapping[str, str], cle: Mapping[str, str]) -> Resultat:
    """Matériau → famille (métaux, matières plastiques, céramiques, composites, organiques…)."""
    return verifier_affectation(affectation, cle)


def verifier_cycle_de_vie(etapes: Sequence[str], attendu: Sequence[str] = CYCLE_DE_VIE_DEFAUT) -> Resultat:
    return verifier_chaine(etapes, attendu)


def verifier_vues(vues: Dict[str, str], attendues: Dict[str, str]) -> Resultat:
    """Représentation technique : nom de vue normalisé → identifiant de dessin attendu."""
    inconnues = [v for v in vues if _norm(v).replace("vue de ", "").strip() not in VUES_NORMALISEES]
    if inconnues:
        return revue(*(f"vue_inconnue:{v}" for v in inconnues))
    norm = {_norm(k).replace("vue de ", "").strip(): v for k, v in vues.items()}
    att = {_norm(k).replace("vue de ", "").strip(): v for k, v in attendues.items()}
    if norm != att:
        return invalide("vues_incorrectes")
    return valide("vues_correctes")
