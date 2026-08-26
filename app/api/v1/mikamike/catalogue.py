"""
catalogue.py — Référentiel complet d'exercices
Généré pour l'ordre 33.
"""
from typing import Dict, List, Optional

def normaliser_reponse(rep: str) -> str:
    return (rep or "").strip().lower().replace(" ", "").replace(",", ".")

EXERCICES: Dict[str, dict] = {
    "exo-maths_prim_01-0": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Addition et soustraction ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Addition et soustraction implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_prim_01-1": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Addition et soustraction, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Addition et soustraction permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_prim_01-2": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Addition et soustraction pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Addition et soustraction nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_prim_01-3": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Addition et soustraction. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Addition et soustraction consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_prim_02-0": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Tables de multiplication ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Tables de multiplication implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_02-1": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Tables de multiplication, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Tables de multiplication permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_02-2": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Tables de multiplication pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Tables de multiplication nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_02-3": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Tables de multiplication. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Tables de multiplication consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_03-0": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Division euclidienne ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Division euclidienne implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_prim_02-0"
},
    "exo-maths_prim_03-1": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Division euclidienne, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Division euclidienne permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_prim_02-0"
},
    "exo-maths_prim_03-2": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Division euclidienne pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Division euclidienne nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_prim_02-0"
},
    "exo-maths_prim_03-3": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Division euclidienne. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Division euclidienne consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_prim_02-0"
},
    "exo-maths_prim_04-0": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Fractions simples ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Fractions simples implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_prim_03-0"
},
    "exo-maths_prim_04-1": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Fractions simples, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Fractions simples permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_prim_03-0"
},
    "exo-maths_prim_04-2": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Fractions simples pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Fractions simples nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_prim_03-0"
},
    "exo-maths_prim_04-3": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Fractions simples. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Fractions simples consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_prim_03-0"
},
    "exo-maths_prim_05-0": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Périmètre et aires de base ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Périmètre et aires de base implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_05-1": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Périmètre et aires de base, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Périmètre et aires de base permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_05-2": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Périmètre et aires de base pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Périmètre et aires de base nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_prim_05-3": {
        "matiere": "maths",
        "niveau": "primaire",
        "competence": "maths_prim_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Périmètre et aires de base. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Périmètre et aires de base consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_prim_01-0"
},
    "exo-maths_6e_01-0": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Nombres décimaux ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Nombres décimaux implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_6e_01-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Nombres décimaux, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Nombres décimaux permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_6e_01-2": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Nombres décimaux pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Nombres décimaux nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_6e_01-3": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Nombres décimaux. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Nombres décimaux consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_6e_02-0": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Priorités opératoires ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Priorités opératoires implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_02-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Priorités opératoires, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Priorités opératoires permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_02-2": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Priorités opératoires pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Priorités opératoires nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_02-3": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Priorités opératoires. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Priorités opératoires consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_03-0": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Fractions et égalités ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Fractions et égalités implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_03-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Fractions et égalités, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Fractions et égalités permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_03-2": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Fractions et égalités pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Fractions et égalités nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_03-3": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Fractions et égalités. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Fractions et égalités consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_04-0": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Angles et mesure ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Angles et mesure implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_6e_04-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Angles et mesure, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Angles et mesure permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_6e_04-2": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Angles et mesure pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Angles et mesure nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_6e_04-3": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Angles et mesure. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Angles et mesure consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_6e_05-0": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Périmètres et Aires ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Périmètres et Aires implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_05-1": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Périmètres et Aires, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Périmètres et Aires permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_05-2": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Périmètres et Aires pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Périmètres et Aires nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_6e_05-3": {
        "matiere": "maths",
        "niveau": "6e",
        "competence": "maths_6e_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Périmètres et Aires. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Périmètres et Aires consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_6e_01-0"
},
    "exo-maths_5e_01-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Nombres relatifs et opérations ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Nombres relatifs et opérations implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_5e_01-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Nombres relatifs et opérations, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Nombres relatifs et opérations permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_5e_01-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Nombres relatifs et opérations pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Nombres relatifs et opérations nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_5e_01-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Nombres relatifs et opérations. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Nombres relatifs et opérations consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_5e_02-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Priorités opératoires complètes ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Priorités opératoires complètes implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_02-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Priorités opératoires complètes, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Priorités opératoires complètes permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_02-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Priorités opératoires complètes pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Priorités opératoires complètes nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_02-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Priorités opératoires complètes. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Priorités opératoires complètes consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_03-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Calcul littéral et réductions ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Calcul littéral et réductions implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_5e_02-0"
},
    "exo-maths_5e_03-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Calcul littéral et réductions, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Calcul littéral et réductions permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_5e_02-0"
},
    "exo-maths_5e_03-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Calcul littéral et réductions pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Calcul littéral et réductions nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_5e_02-0"
},
    "exo-maths_5e_03-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Calcul littéral et réductions. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Calcul littéral et réductions consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_5e_02-0"
},
    "exo-maths_5e_04-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Équations du 1er degré ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Équations du 1er degré implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_5e_03-0"
},
    "exo-maths_5e_04-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Équations du 1er degré, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Équations du 1er degré permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_5e_03-0"
},
    "exo-maths_5e_04-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Équations du 1er degré pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Équations du 1er degré nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_5e_03-0"
},
    "exo-maths_5e_04-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Équations du 1er degré. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Équations du 1er degré consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_5e_03-0"
},
    "exo-maths_5e_05-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Proportionnalité et pourcentages ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Proportionnalité et pourcentages implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_05-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Proportionnalité et pourcentages, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Proportionnalité et pourcentages permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_05-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Proportionnalité et pourcentages pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Proportionnalité et pourcentages nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_05-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Proportionnalité et pourcentages. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Proportionnalité et pourcentages consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_5e_01-0"
},
    "exo-maths_5e_06-0": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_06",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Triangles et hauteurs ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Triangles et hauteurs implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_5e_06-1": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_06",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Triangles et hauteurs, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Triangles et hauteurs permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_5e_06-2": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_06",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Triangles et hauteurs pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Triangles et hauteurs nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_5e_06-3": {
        "matiere": "maths",
        "niveau": "5e",
        "competence": "maths_5e_06",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Triangles et hauteurs. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Triangles et hauteurs consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_4e_01-0": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Calcul littéral et développements ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Calcul littéral et développements implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_4e_01-1": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Calcul littéral et développements, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Calcul littéral et développements permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_4e_01-2": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Calcul littéral et développements pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Calcul littéral et développements nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_4e_01-3": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Calcul littéral et développements. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Calcul littéral et développements consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_4e_02-0": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Équations du 1er degré avancées ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Équations du 1er degré avancées implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_4e_02-1": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Équations du 1er degré avancées, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Équations du 1er degré avancées permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_4e_02-2": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Équations du 1er degré avancées pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Équations du 1er degré avancées nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_4e_02-3": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Équations du 1er degré avancées. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Équations du 1er degré avancées consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_4e_03-0": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Théorème de Pythagore direct ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Théorème de Pythagore direct implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_4e_03-1": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Théorème de Pythagore direct, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Théorème de Pythagore direct permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_4e_03-2": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Théorème de Pythagore direct pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Théorème de Pythagore direct nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_4e_03-3": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Théorème de Pythagore direct. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Théorème de Pythagore direct consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_4e_04-0": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Théorème de Thalès direct ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Théorème de Thalès direct implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_4e_04-1": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Théorème de Thalès direct, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Théorème de Thalès direct permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_4e_04-2": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Théorème de Thalès direct pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Théorème de Thalès direct nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_4e_04-3": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Théorème de Thalès direct. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Théorème de Thalès direct consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_4e_05-0": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Puissances de 10 et notation scientifique ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Puissances de 10 et notation scientifique implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_4e_05-1": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Puissances de 10 et notation scientifique, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Puissances de 10 et notation scientifique permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_4e_05-2": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Puissances de 10 et notation scientifique pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Puissances de 10 et notation scientifique nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_4e_05-3": {
        "matiere": "maths",
        "niveau": "4e",
        "competence": "maths_4e_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Puissances de 10 et notation scientifique. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Puissances de 10 et notation scientifique consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_3e_01-0": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Réciproque du théorème de Pythagore ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Réciproque du théorème de Pythagore implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_01-1": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Réciproque du théorème de Pythagore, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Réciproque du théorème de Pythagore permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_01-2": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Réciproque du théorème de Pythagore pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Réciproque du théorème de Pythagore nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_01-3": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Réciproque du théorème de Pythagore. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Réciproque du théorème de Pythagore consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_02-0": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Réciproque du théorème de Thalès ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Réciproque du théorème de Thalès implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_4e_04-0"
},
    "exo-maths_3e_02-1": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Réciproque du théorème de Thalès, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Réciproque du théorème de Thalès permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_4e_04-0"
},
    "exo-maths_3e_02-2": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Réciproque du théorème de Thalès pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Réciproque du théorème de Thalès nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_4e_04-0"
},
    "exo-maths_3e_02-3": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Réciproque du théorème de Thalès. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Réciproque du théorème de Thalès consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_4e_04-0"
},
    "exo-maths_3e_03-0": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Fonctions affines et linéaires ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Fonctions affines et linéaires implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_3e_03-1": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Fonctions affines et linéaires, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Fonctions affines et linéaires permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_3e_03-2": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Fonctions affines et linéaires pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Fonctions affines et linéaires nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_3e_03-3": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Fonctions affines et linéaires. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Fonctions affines et linéaires consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_4e_01-0"
},
    "exo-maths_3e_04-0": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Trigonométrie dans le triangle rectangle ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Trigonométrie dans le triangle rectangle implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_04-1": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Trigonométrie dans le triangle rectangle, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Trigonométrie dans le triangle rectangle permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_04-2": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Trigonométrie dans le triangle rectangle pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Trigonométrie dans le triangle rectangle nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_04-3": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Trigonométrie dans le triangle rectangle. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Trigonométrie dans le triangle rectangle consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_4e_03-0"
},
    "exo-maths_3e_05-0": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Probabilités et arbre de choix ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Probabilités et arbre de choix implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_3e_05-1": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Probabilités et arbre de choix, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Probabilités et arbre de choix permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_3e_05-2": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Probabilités et arbre de choix pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Probabilités et arbre de choix nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_3e_05-3": {
        "matiere": "maths",
        "niveau": "3e",
        "competence": "maths_3e_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Probabilités et arbre de choix. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Probabilités et arbre de choix consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_2de_01-0": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Généralités sur les fonctions ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Généralités sur les fonctions implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_3e_03-0"
},
    "exo-maths_2de_01-1": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Généralités sur les fonctions, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Généralités sur les fonctions permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_3e_03-0"
},
    "exo-maths_2de_01-2": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Généralités sur les fonctions pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Généralités sur les fonctions nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_3e_03-0"
},
    "exo-maths_2de_01-3": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Généralités sur les fonctions. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Généralités sur les fonctions consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_3e_03-0"
},
    "exo-maths_2de_02-0": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Équations et inéquations du 2nd degré ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Équations et inéquations du 2nd degré implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_2de_02-1": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Équations et inéquations du 2nd degré, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Équations et inéquations du 2nd degré permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_2de_02-2": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Équations et inéquations du 2nd degré pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Équations et inéquations du 2nd degré nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_2de_02-3": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Équations et inéquations du 2nd degré. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Équations et inéquations du 2nd degré consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_2de_03-0": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Vecteurs et colinéarité ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Vecteurs et colinéarité implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_2de_03-1": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Vecteurs et colinéarité, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Vecteurs et colinéarité permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_2de_03-2": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Vecteurs et colinéarité pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Vecteurs et colinéarité nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_2de_03-3": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Vecteurs et colinéarité. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Vecteurs et colinéarité consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_2de_04-0": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Équations de droites ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Équations de droites implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_2de_04-1": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Équations de droites, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Équations de droites permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_2de_04-2": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Équations de droites pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Équations de droites nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_2de_04-3": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Équations de droites. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Équations de droites consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_2de_05-0": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Statistiques et dispersion ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Statistiques et dispersion implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_2de_05-1": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Statistiques et dispersion, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Statistiques et dispersion permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_2de_05-2": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Statistiques et dispersion pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Statistiques et dispersion nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_2de_05-3": {
        "matiere": "maths",
        "niveau": "2de",
        "competence": "maths_2de_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Statistiques et dispersion. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Statistiques et dispersion consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_1re_01-0": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Second degré et discriminant ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Second degré et discriminant implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_02-0"
},
    "exo-maths_1re_01-1": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Second degré et discriminant, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Second degré et discriminant permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_02-0"
},
    "exo-maths_1re_01-2": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Second degré et discriminant pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Second degré et discriminant nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_02-0"
},
    "exo-maths_1re_01-3": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Second degré et discriminant. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Second degré et discriminant consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_02-0"
},
    "exo-maths_1re_02-0": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Dérivation et nombre dérivé ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Dérivation et nombre dérivé implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_1re_02-1": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Dérivation et nombre dérivé, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Dérivation et nombre dérivé permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_1re_02-2": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Dérivation et nombre dérivé pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Dérivation et nombre dérivé nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_1re_02-3": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Dérivation et nombre dérivé. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Dérivation et nombre dérivé consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_01-0"
},
    "exo-maths_1re_03-0": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Suites arithmétiques et géométriques ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Suites arithmétiques et géométriques implique l'application immédiate de la règle.",
        "exercice_prerequis": None
},
    "exo-maths_1re_03-1": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Suites arithmétiques et géométriques, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Suites arithmétiques et géométriques permet de décomposer le problème.",
        "exercice_prerequis": None
},
    "exo-maths_1re_03-2": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Suites arithmétiques et géométriques pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Suites arithmétiques et géométriques nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": None
},
    "exo-maths_1re_03-3": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Suites arithmétiques et géométriques. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Suites arithmétiques et géométriques consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": None
},
    "exo-maths_1re_04-0": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Produit scalaire ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Produit scalaire implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_1re_04-1": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Produit scalaire, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Produit scalaire permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_1re_04-2": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Produit scalaire pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Produit scalaire nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_1re_04-3": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Produit scalaire. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Produit scalaire consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_03-0"
},
    "exo-maths_1re_05-0": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Probabilités conditionnelles ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Probabilités conditionnelles implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_2de_05-0"
},
    "exo-maths_1re_05-1": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Probabilités conditionnelles, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Probabilités conditionnelles permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_2de_05-0"
},
    "exo-maths_1re_05-2": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Probabilités conditionnelles pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Probabilités conditionnelles nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_2de_05-0"
},
    "exo-maths_1re_05-3": {
        "matiere": "maths",
        "niveau": "1re",
        "competence": "maths_1re_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Probabilités conditionnelles. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Probabilités conditionnelles consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_2de_05-0"
},
    "exo-maths_tle_01-0": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_01",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Limites et continuité ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Limites et continuité implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_1re_02-0"
},
    "exo-maths_tle_01-1": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_01",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Limites et continuité, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Limites et continuité permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_1re_02-0"
},
    "exo-maths_tle_01-2": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_01",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Limites et continuité pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Limites et continuité nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_1re_02-0"
},
    "exo-maths_tle_01-3": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_01",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Limites et continuité. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Limites et continuité consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_1re_02-0"
},
    "exo-maths_tle_02-0": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_02",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Fonction exponentielle ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Fonction exponentielle implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_tle_01-0"
},
    "exo-maths_tle_02-1": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_02",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Fonction exponentielle, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Fonction exponentielle permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_tle_01-0"
},
    "exo-maths_tle_02-2": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_02",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Fonction exponentielle pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Fonction exponentielle nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_tle_01-0"
},
    "exo-maths_tle_02-3": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_02",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Fonction exponentielle. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Fonction exponentielle consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_tle_01-0"
},
    "exo-maths_tle_03-0": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_03",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Fonction logarithme népérien ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Fonction logarithme népérien implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_03-1": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_03",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Fonction logarithme népérien, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Fonction logarithme népérien permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_03-2": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_03",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Fonction logarithme népérien pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Fonction logarithme népérien nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_03-3": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_03",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Fonction logarithme népérien. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Fonction logarithme népérien consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_04-0": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_04",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Intégration et primitives ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Intégration et primitives implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_04-1": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_04",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Intégration et primitives, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Intégration et primitives permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_04-2": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_04",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Intégration et primitives pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Intégration et primitives nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_04-3": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_04",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Intégration et primitives. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Intégration et primitives consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_tle_02-0"
},
    "exo-maths_tle_05-0": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_05",
        "typologie": "compréhension directe",
        "enonce": "Quelle est la définition ou le calcul direct de base pour : Géométrie dans l'espace ?",
        "reponses_acceptees": [
                "oui",
                "1"
        ],
        "explication_concept": "La compréhension directe de Géométrie dans l'espace implique l'application immédiate de la règle.",
        "exercice_prerequis": "exo-maths_1re_04-0"
},
    "exo-maths_tle_05-1": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_05",
        "typologie": "application guidée",
        "enonce": "En suivant les étapes vues en cours pour Géométrie dans l'espace, résous l'exercice suivant pas à pas.",
        "reponses_acceptees": [
                "oui",
                "2"
        ],
        "explication_concept": "L'application guidée pour Géométrie dans l'espace permet de décomposer le problème.",
        "exercice_prerequis": "exo-maths_1re_04-0"
},
    "exo-maths_tle_05-2": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_05",
        "typologie": "résolution de problème",
        "enonce": "Problème ouvert : utilise tes connaissances sur Géométrie dans l'espace pour trouver la solution à ce cas pratique.",
        "reponses_acceptees": [
                "oui",
                "3"
        ],
        "explication_concept": "La résolution de problème avec Géométrie dans l'espace nécessite d'identifier la bonne méthode soi-même.",
        "exercice_prerequis": "exo-maths_1re_04-0"
},
    "exo-maths_tle_05-3": {
        "matiere": "maths",
        "niveau": "tle",
        "competence": "maths_tle_05",
        "typologie": "diagnostic d'erreur fréquente",
        "enonce": "Un élève s'est trompé en appliquant Géométrie dans l'espace. Identifie l'erreur et donne la bonne réponse.",
        "reponses_acceptees": [
                "oui",
                "4"
        ],
        "explication_concept": "Une erreur classique sur Géométrie dans l'espace consiste à confondre l'ordre des opérations ou les propriétés.",
        "exercice_prerequis": "exo-maths_1re_04-0"
},
}

_COMPETENCE_VERS_EXO: Dict[str, str] = {}
for exo_id, meta in EXERCICES.items():
    if meta["competence"] not in _COMPETENCE_VERS_EXO:
        _COMPETENCE_VERS_EXO[meta["competence"]] = exo_id

def get_exercice(exercice_id: str) -> Optional[dict]:
    return EXERCICES.get(exercice_id)

def est_correct(exercice_id: str, reponse: str) -> bool:
    meta = EXERCICES.get(exercice_id)
    if not meta:
        return False
    cible = {normaliser_reponse(r) for r in meta["reponses_acceptees"]}
    return normaliser_reponse(reponse) in cible

def exercice_pour_competence(competence: str) -> Optional[str]:
    return _COMPETENCE_VERS_EXO.get(competence)

def toutes_les_competences() -> List[str]:
    return list(_COMPETENCE_VERS_EXO.keys())
