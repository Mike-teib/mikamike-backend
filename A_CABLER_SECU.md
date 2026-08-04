# Directives d'Intégration de la Sécurité Fail-Closed & Validation OCR

**Date** : 03/08/2026  
**Agent** : ANTI2  
**Référence** : Cahier des charges §8 (Sécurité Fail-Closed & Filtrage Amont)

---

## 🔒 1. Garde de Session Fail-Closed (`exiger_session_active`)

Pour protéger un endpoint contre les accès anonymes ou avec jeton expiré, injecter la dépendance `Depends(exiger_session_active)` :

```python
from app.api.v1.security import exiger_session_active

@router.get("/protégé")
def route_securisee(session: dict = Depends(exiger_session_active)):
    pseudo_id = session["pseudo_id"]
    return {"statut": "acces_autorise", "pseudo_id": pseudo_id}
```

* **Comportement Fail-Closed** : Tout en-tête `Authorization: Bearer <token>` absent, invalide ou expiré renvoie immédiatement un code **`401 Unauthorized`**.

---

## 📷 2. Filtrage Amont OCR / Ardoise (`valider_payload_ocr`)

Pour protéger les traitements d'image/ardoise et les appels IA contre les attaques par déni de service (payloads trop lourds ou corrompus), injecter `Depends(valider_payload_ocr)` :

```python
from app.api.v1.security import valider_payload_ocr, OcrPayload

@router.post("/ocr/analyser")
def analyser_ardoise(
    payload: OcrPayload = Depends(valider_payload_ocr),
    session: dict = Depends(exiger_session_active)
):
    # Garantie : Le payload fait < 2 Mo et le base64 est valide AVANT d'arriver ici
    return {"statut": "analyse_ok", "exercice_id": payload.exercice_id}
```

* **Comportement Fail-Closed** :
  * Si la taille dépasse **2 Mo** : rejet immédiat avec **`413 Request Entity Too Large`**.
  * Si le base64 est corrompu ou vide : rejet immédiat avec **`400 Bad Request`**.
