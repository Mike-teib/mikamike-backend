"""
curriculum_dataset.py — Référentiel de Compétences et Moteur de Graphe (Tâche #27).
==================================================================================
Couvre les 8 niveaux (primaire, 6e, 5e, 4e, 3e, 2de, 1re, tle) et 4 matières (Maths, Physique, Chimie, SVT).
Valide l'absence de cycle (DAG) et génère le chemin d'apprentissage personnalisé.
"""

from __future__ import annotations

from typing import Dict, List, Set, Any, Tuple


class NotionNode:
    """Représentation d'une compétence dans le graphe de compétences."""
    def __init__(
        self,
        notion_id: str,
        titre: str,
        level: str,
        subject: str,
        prerequisite_ids: List[str],
        description: str = ""
    ):
        self.notion_id = notion_id
        self.titre = titre
        self.level = level
        self.subject = subject
        self.prerequisite_ids = prerequisite_ids
        self.description = description

    def to_dict(self, mastery_status: int = 0) -> Dict[str, Any]:
        return {
            "notion_id": self.notion_id,
            "titre": self.titre,
            "level": self.level,
            "subject": self.subject,
            "prerequisite_ids": self.prerequisite_ids,
            "mastery_status": mastery_status,
            "description": self.description
        }


# --- BASE DE DONNÉES CURRICULUM MULTI-NIVEAUX ET MULTI-MATIÈRES ---

CURRICULA_DATA: Dict[Tuple[str, str], List[NotionNode]] = {
    # ------------------ MATHÉMATIQUES ------------------
    ("primaire", "maths"): [
        NotionNode("maths_prim_01", "Addition et soustraction", "primaire", "Maths", [], "Bases du calcul numérique"),
        NotionNode("maths_prim_02", "Tables de multiplication", "primaire", "Maths", ["maths_prim_01"], "Mémorisation des tables"),
        NotionNode("maths_prim_03", "Division euclidienne", "primaire", "Maths", ["maths_prim_02"], "Partage et reste"),
        NotionNode("maths_prim_04", "Fractions simples", "primaire", "Maths", ["maths_prim_03"], "Demis, tiers, quarts"),
        NotionNode("maths_prim_05", "Périmètre et aires de base", "primaire", "Maths", ["maths_prim_01"], "Carré et rectangle"),
    ],
    ("6e", "maths"): [
        NotionNode("maths_6e_01", "Nombres décimaux", "6e", "Maths", [], "Virgules et puissances de 10"),
        NotionNode("maths_6e_02", "Priorités opératoires", "6e", "Maths", ["maths_6e_01"], "Parenthèses et multiplications d'abord"),
        NotionNode("maths_6e_03", "Fractions et égalités", "6e", "Maths", ["maths_6e_01"], "Simplification de fractions"),
        NotionNode("maths_6e_04", "Angles et mesure", "6e", "Maths", [], "Rapporteur et degrés"),
        NotionNode("maths_6e_05", "Périmètres et Aires", "6e", "Maths", ["maths_6e_01"], "Formules usuelles de géométrie"),
    ],
    ("5e", "maths"): [
        NotionNode("maths_5e_01", "Nombres relatifs et opérations", "5e", "Maths", [], "Addition et soustraction de nombres relatifs"),
        NotionNode("maths_5e_02", "Priorités opératoires complètes", "5e", "Maths", ["maths_5e_01"], "Calculs complexes avec parenthèses"),
        NotionNode("maths_5e_03", "Calcul littéral et réductions", "5e", "Maths", ["maths_5e_02"], "Regroupement des termes en x"),
        NotionNode("maths_5e_04", "Équations du 1er degré", "5e", "Maths", ["maths_5e_03"], "Isolation de l'inconnue x"),
        NotionNode("maths_5e_05", "Proportionnalité et pourcentages", "5e", "Maths", ["maths_5e_01"], "Produit en croix et échelles"),
        NotionNode("maths_5e_06", "Triangles et hauteurs", "5e", "Maths", [], "Inégalité triangulaire et médiatrices"),
    ],
    ("4e", "maths"): [
        NotionNode("maths_4e_01", "Calcul littéral et développements", "4e", "Maths", [], "Simple et double distributivité"),
        NotionNode("maths_4e_02", "Équations du 1er degré avancées", "4e", "Maths", ["maths_4e_01"], "Équations avec fractions"),
        NotionNode("maths_4e_03", "Théorème de Pythagore direct", "4e", "Maths", [], "Calcul de l'hypoténuse dans un triangle rectangle"),
        NotionNode("maths_4e_04", "Théorème de Thalès direct", "4e", "Maths", [], "Calcul de longueurs dans des triangles emboîtés"),
        NotionNode("maths_4e_05", "Puissances de 10 et notation scientifique", "4e", "Maths", [], "Grandes et petites grandeurs"),
    ],
    ("3e", "maths"): [
        NotionNode("maths_3e_01", "Réciproque du théorème de Pythagore", "3e", "Maths", ["maths_4e_03"], "Démontrer qu'un triangle est rectangle"),
        NotionNode("maths_3e_02", "Réciproque du théorème de Thalès", "3e", "Maths", ["maths_4e_04"], "Démontrer que deux droites sont parallèles"),
        NotionNode("maths_3e_03", "Fonctions affines et linéaires", "3e", "Maths", ["maths_4e_01"], "Représentation graphique y = ax + b"),
        NotionNode("maths_3e_04", "Trigonométrie dans le triangle rectangle", "3e", "Maths", ["maths_4e_03"], "Cosinus, sinus et tangente"),
        NotionNode("maths_3e_05", "Probabilités et arbre de choix", "3e", "Maths", [], "Événements et probabilités simples"),
    ],
    ("2de", "maths"): [
        NotionNode("maths_2de_01", "Généralités sur les fonctions", "2de", "Maths", ["maths_3e_03"], "Domaine de définition et variations"),
        NotionNode("maths_2de_02", "Équations et inéquations du 2nd degré", "2de", "Maths", ["maths_2de_01"], "Tableau de signes et résolution"),
        NotionNode("maths_2de_03", "Vecteurs et colinéarité", "2de", "Maths", [], "Coordonnées vectorielles et parallélisme"),
        NotionNode("maths_2de_04", "Équations de droites", "2de", "Maths", ["maths_2de_03"], "Vecteur directeur et équation cartésienne"),
        NotionNode("maths_2de_05", "Statistiques et dispersion", "2de", "Maths", [], "Moyenne, médiane et écart interquartile"),
    ],
    ("1re", "maths"): [
        NotionNode("maths_1re_01", "Second degré et discriminant", "1re", "Maths", ["maths_2de_02"], "Calcul du discriminant Delta et racines"),
        NotionNode("maths_1re_02", "Dérivation et nombre dérivé", "1re", "Maths", ["maths_2de_01"], "Tangente et fonction dérivée f'(x)"),
        NotionNode("maths_1re_03", "Suites arithmétiques et géométriques", "1re", "Maths", [], "Raison, terme général et sommes"),
        NotionNode("maths_1re_04", "Produit scalaire", "1re", "Maths", ["maths_2de_03"], "Projeté orthogonal et calcul d'angles"),
        NotionNode("maths_1re_05", "Probabilités conditionnelles", "1re", "Maths", ["maths_2de_05"], "Arbres pondérés et formule de Bayes"),
    ],
    ("tle", "maths"): [
        NotionNode("maths_tle_01", "Limites et continuité", "tle", "Maths", ["maths_1re_02"], "Théorème des valeurs intermédiaires"),
        NotionNode("maths_tle_02", "Fonction exponentielle", "tle", "Maths", ["maths_tle_01"], "Propriétés et équations de exp(x)"),
        NotionNode("maths_tle_03", "Fonction logarithme népérien", "tle", "Maths", ["maths_tle_02"], "Réciproque de l'exponentielle ln(x)"),
        NotionNode("maths_tle_04", "Intégration et primitives", "tle", "Maths", ["maths_tle_02"], "Calcul d'aires et primitives F(x)"),
        NotionNode("maths_tle_05", "Géométrie dans l'espace", "tle", "Maths", ["maths_1re_04"], "Vecteurs, plans et équations de droite"),
    ],

    # ------------------ PHYSIQUE / CHIMIE / SVT ------------------
    ("5e", "physique"): [
        NotionNode("phys_5e_01", "Circuit électrique simple", "5e", "Physique", [], "Générateur, récepteur et boucle fermée"),
        NotionNode("phys_5e_02", "Tension et intensité", "5e", "Physique", ["phys_5e_01"], "Lois des nœuds et des mailles"),
    ],
    ("4e", "chimie"): [
        NotionNode("chim_4e_01", "Atomes et molécules", "4e", "Chimie", [], "Formules chimiques de base (H2O, CO2)"),
        NotionNode("chim_4e_02", "Réaction chimique et équilibrage", "4e", "Chimie", ["chim_4e_01"], "Conservation de la masse et des atomes"),
    ],
    ("3e", "svt"): [
        NotionNode("svt_3e_01", "Cellules et ADN", "3e", "SVT", [], "Support de l'information génétique"),
        NotionNode("svt_3e_02", "Système immunitaire et anticorps", "3e", "SVT", ["svt_3e_01"], "Défense de l'organisme contre les pathogènes"),
    ]
}


class ReferentielInconnu(ValueError):
    """Niveau ou matière non reconnu : on refuse au lieu de deviner."""


def normaliser_niveau(level: str) -> str:
    """
    Normalise la chaîne de niveau. Un niveau inconnu lève ReferentielInconnu
    (auparavant : repli silencieux vers « 5e » = mauvais niveau accepté).
    """
    lvl = (level or "5e").strip().lower()
    mapping = {
        "prim": "primaire", "primaire": "primaire",
        "6e": "6e", "6eme": "6e",
        "5e": "5e", "5eme": "5e",
        "4e": "4e", "4eme": "4e",
        "3e": "3e", "3eme": "3e",
        "2de": "2de", "seconde": "2de",
        "1re": "1re", "premiere": "1re",
        "tle": "tle", "terminale": "tle"
    }
    if lvl not in mapping:
        raise ReferentielInconnu("niveau_inconnu")
    return mapping[lvl]


def normaliser_matiere(subject: str) -> str:
    """Normalise la chaîne de matière (en minuscules pour correspondre aux clés)."""
    sub = (subject or "maths").strip().lower()
    if sub in ("maths", "mathematiques", "math"):
        return "maths"
    if sub in ("physique", "phys"):
        return "physique"
    if sub in ("chimie", "chem"):
        return "chimie"
    # NB : « sciences » n'est PAS un alias de SVT (Sciences et technologie, Enseignement
    # scientifique sont des matières distinctes) : on refuse plutôt que de contaminer.
    if sub in ("svt",):
        return "svt"
    raise ReferentielInconnu("matiere_inconnue")


def valider_graphe_sans_cycles(notions: List[NotionNode]) -> bool:
    """
    Algorithme de détection de cycles (Tarjan / DFS avec états blanc/gris/noir).
    Garantit que le graphe de compétences est un DAG (Directed Acyclic Graph).
    """
    nodes_map = {n.notion_id: n for n in notions}
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def dfs(node_id: str) -> bool:
        if node_id in visiting:
            return False  # Cycle détecté !
        if node_id in visited:
            return True

        visiting.add(node_id)
        node = nodes_map.get(node_id)
        if node:
            for pre_id in node.prerequisite_ids:
                if pre_id in nodes_map and not dfs(pre_id):
                    return False

        visiting.remove(node_id)
        visited.add(node_id)
        return True

    for node in notions:
        if node.notion_id not in visited:
            if not dfs(node.notion_id):
                return False

    return True


def prerequis_non_resolus(notions: List[NotionNode]) -> List[Tuple[str, str]]:
    """Liste (notion_id, prerequis_id) dont le prérequis n'existe dans AUCUN référentiel."""
    connus = {n.notion_id for groupe in CURRICULA_DATA.values() for n in groupe}
    connus.update(n.notion_id for n in notions)
    return [
        (n.notion_id, pre)
        for n in notions
        for pre in n.prerequisite_ids
        if pre not in connus
    ]


def valider_prerequis_resolus(notions: List[NotionNode]) -> bool:
    """Vérifie que chaque prérequis référencé existe (dans ce graphe ou un autre niveau)."""
    return not prerequis_non_resolus(notions)


def obtenir_graphe_competences(level: str, subject: str) -> List[NotionNode]:
    """Retourne la liste des compétences pour un niveau et une matière."""
    lvl = normaliser_niveau(level)
    sub = normaliser_matiere(subject)

    # Récupération EXACTE uniquement : plus de repli vers Maths (qui renvoyait un
    # graphe de mathématiques étiqueté « SVT » ou « Physique »). Absent => liste vide.
    return list(CURRICULA_DATA.get((lvl, sub), []))


def generer_parcours_personnalise(
    notions: List[NotionNode],
    etats_eleve: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Génère les 3 premières notions recommandées à étudier.
    Critère d'ordre : Notion non maîtrisée dont le nombre de prérequis non satisfaits est MINIMAL.
    """
    notions_eligibles = []

    for node in notions:
        etat = etats_eleve.get(node.notion_id, "INCONNU")
        # Si la notion n'est pas consolidée (ACQUIS_AUTONOME / MAITRISE)
        if etat not in ("ACQUIS_AUTONOME", "MAITRISE"):
            # Calcul des prérequis manquants
            prereq_manquants = 0
            for pre_id in node.prerequisite_ids:
                pre_etat = etats_eleve.get(pre_id, "INCONNU")
                if pre_etat not in ("ACQUIS_AUTONOME", "MAITRISE"):
                    prereq_manquants += 1

            notions_eligibles.append({
                "node": node,
                "prereq_manquants": prereq_manquants,
                "etat_courant": etat
            })

    # Tri par nombre de prérequis manquants croissant (0 d'abord)
    notions_eligibles.sort(key=lambda x: x["prereq_manquants"])

    path = []
    for idx, item in enumerate(notions_eligibles[:3], start=1):
        node: NotionNode = item["node"]
        raisons = (
            "Aucun prérequis manquant" if item["prereq_manquants"] == 0
            else f"{item['prereq_manquants']} prérequis en cours de consolidation"
        )
        path.append({
            "notion_id": node.notion_id,
            "titre": node.titre,
            "ordre": idx,
            "raisons": raisons,
            "prerequisite_ids": node.prerequisite_ids
        })

    return path
