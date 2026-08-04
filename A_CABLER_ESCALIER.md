# Directives d'Intégration du Moteur Pédagogique (Escalier, Parcours & Mémoire Espacée)

**Date** : 03/08/2026  
**Agent** : ANTI2  
**Référence** : Cahier des charges §4 & Ordre de Mission #27-#28

---

## 📌 Lignes à ajouter dans `main.py` (Intégration Moteur Pédagogique)

Pour intégrer l'ensemble des modules du Learning Engine (Orchestrateur 8 Étapes, Graphe de Compétences et Mémorisation Espacée), ajouter les lignes suivantes dans `main.py` :

```python
# --- Learning Engine & Memory Routers ----------------------------------------- #
from app.api.v1.escalier.router import escalier_router
from app.api.v1.parcours.router import parcours_graph_router
from app.api.v1.memory.router import memory_router

# Dans la fonction create_app() :
app.include_router(escalier_router, prefix=API_V1_PREFIX)
app.include_router(parcours_graph_router, prefix=API_V1_PREFIX)
app.include_router(memory_router, prefix=API_V1_PREFIX)
```

---

## 📑 Endpoints exposés sous `/api/v1`

### 1. Orchestrateur Escalier Mika (`POST /api/v1/escalier/etape`) — Cahier §4
- **Entrée** : `student_pseudo_id`, `competence_objectif`, `exercice_id`, `reponse_eleve`, `avec_aide`.
- **Comportement** : Déroule la boucle déterministe en 8 étapes (*Objectif -> Analyse Erreur -> Prérequis -> Explication -> Micro-remédiation -> Vérification Moteur -> Retour Objectif -> Mémoire*).

### 2. Graphe de Compétences & Parcours Personnalisé (`POST /api/v1/parcours`) — Tâche #27
- **Entrée** : `user_id`, `level` (primaire, 6e, 5e, 4e, 3e, 2de, 1re, tle), `subject` (Maths, Physique, Chimie, SVT).
- **Retour** :
  - `competency_graph` : Graphe complet du niveau/sujet avec validation DAG (0 cycle).
  - `personalized_learning_path` : Les 3 premières notions à étudier ordonnées par satisfaction des prérequis.

### 3. Mémorisation Espacée Ebbinghaus (`POST /api/v1/memory/schedule`) — Tâche #28
- **Entrée** : `user_id`, `notion_id`, `mastery_event` (`SUCCESS` / `FAILURE`).
- **Comportement** :
  - Détecte la **fragilité** en cas d'échec (`statut_fragilite = True`, rappel immédiat J+1).
  - Planifie les rappels échelonnés à **J+1, J+3, J+7, J+14** en cas de réussites consécutives.
  - Modélise la courbe d'oubli d'Ebbinghaus $R = e^{-t / S}$.
