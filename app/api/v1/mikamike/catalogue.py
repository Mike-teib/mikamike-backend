"""
catalogue.py — Référentiel minimal d'exercices (source de vérité des réponses).

Remplace la « simulation statique » du mock : au lieu de coder en dur `x = 3`
dans l'endpoint, la correction s'appuie sur ce catalogue (réponses acceptées,
compétence visée, exercice prérequis pour la remédiation). Les compétences
correspondent au graphe de prérequis du learning_engine.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional


def normaliser_reponse(rep: str) -> str:
    """Normalisation tolérante : espaces, casse, virgule décimale."""
    return (rep or "").strip().lower().replace(" ", "").replace(",", ".")


# exercice_id -> métadonnées
EXERCICES: Dict[str, dict] = {
    "exo-maths-algebre-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "equations_1er_degre",
        "enonce": "Résous : x + 4 = 7",
        "reponses_acceptees": ["x=3", "3"],
        "explication_concept": (
            "Pour isoler x, soustrais 4 des deux côtés : x = 7 - 4 = 3."
        ),
        "exercice_prerequis": "exo-maths-calcul-litteral-1",
    },
    "exo-maths-calcul-litteral-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "calcul_litteral",
        "enonce": "Réduis : 3x + 2x",
        "reponses_acceptees": ["5x"],
        "explication_concept": "On additionne les termes en x : 3x + 2x = 5x.",
        "exercice_prerequis": "exo-maths-priorites-1",
    },
    "exo-maths-priorites-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "priorites_operatoires",
        "enonce": "Calcule : 2 + 3 × 4",
        "reponses_acceptees": ["14"],
        "explication_concept": "La multiplication est prioritaire : 3×4=12, puis +2 = 14.",
        "exercice_prerequis": "exo-maths-priorites-1",  # marche de base
    },
    "exo-maths-fractions-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "fractions",
        "enonce": "Simplifie : 4/8",
        "reponses_acceptees": ["1/2", "0.5"],
        "explication_concept": "On divise numérateur et dénominateur par 4 : 4/8 = 1/2.",
        "exercice_prerequis": "exo-maths-priorites-1",
    },
}

# compétence -> exercice « d'entrée » recommandé pour cette compétence
_COMPETENCE_VERS_EXO: Dict[str, str] = {
    meta["competence"]: exo_id for exo_id, meta in EXERCICES.items()
}


def get_exercice(exercice_id: str) -> Optional[dict]:
    return EXERCICES.get(exercice_id)


def est_correct_chaine(exercice_id: str, reponse: str) -> bool:
    """Correcteur HISTORIQUE (comparaison de chaînes normalisées). Sert de référence à l'audit R6."""
    meta = EXERCICES.get(exercice_id)
    if not meta:
        return False
    cible = {normaliser_reponse(r) for r in meta["reponses_acceptees"]}
    return normaliser_reponse(reponse) in cible


def correction_symbolique_active() -> bool:
    """MIKA_CORRECTION_SYMBOLIQUE = on (défaut, décision D5) | off (retour au correcteur historique)."""
    return (os.getenv("MIKA_CORRECTION_SYMBOLIQUE") or "on").strip().lower() != "off"


def est_correct(exercice_id: str, reponse: str) -> bool:
    """Décision D5 : les réponses déjà acceptées le restent (aucune donnée officielle modifiée) ;
    on accepte EN PLUS les seules équivalences symboliques DÉMONTRÉES (fond ET forme certains,
    décision ACCEPTER de `app.curriculum.equivalence`). Tout cas ambigu (NEEDS_HUMAN_REVIEW)
    reste refusé automatiquement : il relève d'une revue humaine."""
    if est_correct_chaine(exercice_id, reponse):
        return True
    meta = EXERCICES.get(exercice_id)
    if not meta or not correction_symbolique_active() or not (reponse or "").strip():
        return False
    from app.curriculum.equivalence import Decision, classer

    try:
        ligne = classer(meta.get("enonce", ""), list(meta["reponses_acceptees"]), reponse, False)
    except Exception:  # fail-closed : aucune erreur du vérificateur ne vaut « correct »
        return False
    return ligne.decision == Decision.ACCEPTER


def exercice_pour_competence(competence: str) -> Optional[str]:
    return _COMPETENCE_VERS_EXO.get(competence)


def toutes_les_competences() -> List[str]:
    return list(_COMPETENCE_VERS_EXO.keys())
