# Directives d'Intégration du Module RGPD (Export & Effacement)

**Date** : 03/08/2026  
**Agent** : ANTI2  
**Statut** : Prêt pour câblage ultérieur (**NE PAS intégrer sur le Staging en cours**).

---

## 📌 Lignes à ajouter dans `main.py` (Intégration Ultérieure)

Pour activer les endpoints du Droit RGPD (Export `/export/{id}` et Effacement `/effacer/{id}`), ajouter les lignes suivantes dans `main.py` :

```python
# --- Module RGPD (Export & Droit à l'oubli) ----------------------------------- #
from app.api.v1.rgpd.router import rgpd_router

# Dans la fonction create_app() :
app.include_router(rgpd_router, prefix=API_V1_PREFIX)
```

---

## 📑 Endpoints exposés sous `/api/v1/rgpd`

1. **`GET /api/v1/rgpd/export/{student_pseudo_id}`**
   - **Rôle** : Exporte toutes les tentatives et états de maîtrise enregistrés pour un élève (pseudonymisé HMAC).
   - **Sécurité RGPD** : Strictement aucune PII (pas de nom, prénom, email ni adresse IP).

2. **`DELETE /api/v1/rgpd/effacer/{student_pseudo_id}`**
   - **Rôle** : Purge définitivement l'historique et les compétences de l'élève (Droit à l'oubli).
   - **Retour** : Compte rendu du nombre d'enregistrements supprimés.
