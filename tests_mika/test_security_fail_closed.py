"""
Tests unitaires et d'intégration de la sécurité Fail-Closed & Validation OCR.
Conforme au Cahier des Charges §8.
"""

import base64
import datetime as _dt
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from jose import jwt

from app.api.v1.security.fail_closed import (
    exiger_session_active,
    valider_payload_ocr,
    OcrPayload,
    MAX_OCR_PAYLOAD_BYTES,
    _JWT_SECRET,
    _JWT_ALGORITHM
)

# Application d'essai pour tester les dépendances de sécurité
app_secu_test = FastAPI()


@app_secu_test.get("/api/v1/test-protege")
def endpoint_protege(session: dict = Depends(exiger_session_active)):
    return {"statut": "succes", "user": session["pseudo_id"]}


@app_secu_test.post("/api/v1/test-ocr")
def endpoint_ocr(payload: OcrPayload = Depends(valider_payload_ocr)):
    return {"statut": "ocr_valide", "taille": len(payload.image_b64)}


client = TestClient(app_secu_test)


# --- Helper pour créer des jetons de test ---
def generer_token_test(pseudo_id: str = "eleve_test_secu", exp_delta_seconds: int = 3600) -> str:
    now = _dt.datetime.now(_dt.timezone.utc)
    exp = int((now + _dt.timedelta(seconds=exp_delta_seconds)).timestamp())
    payload = {"sub": pseudo_id, "role": "eleve", "exp": exp}
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


# --- Tests de la Garde de Session Fail-Closed ---

def test_session_active_valide_succes():
    """Vérifie l'accès réussi avec un jeton de session valide."""
    token = generer_token_test(pseudo_id="eleve_valide_123", exp_delta_seconds=3600)
    response = client.get("/api/v1/test-protege", headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    assert response.json()["statut"] == "succes"
    assert response.json()["user"] == "eleve_valide_123"


def test_session_absente_refus_fail_closed():
    """Vérifie le refus Fail-Closed (401) lorsque l'en-tête Authorization est absent."""
    response = client.get("/api/v1/test-protege")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "session_requise"


def test_session_expiree_refus_fail_closed():
    """Vérifie le refus Fail-Closed (401) lorsque le jeton de session est expiré."""
    token_expire = generer_token_test(pseudo_id="eleve_expire", exp_delta_seconds=-100)
    response = client.get("/api/v1/test-protege", headers={"Authorization": f"Bearer {token_expire}"})
    
    assert response.status_code == 401
    assert "expirer" in response.json()["detail"].lower()


def test_token_corrompu_refus_fail_closed():
    """Vérifie le refus (401) en cas de jeton altéré / signature invalide."""
    token_corrompu = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.badpayload.signature"
    response = client.get("/api/v1/test-protege", headers={"Authorization": token_corrompu})
    
    assert response.status_code == 401
    assert "invalide" in response.json()["detail"].lower() or "expirer" in response.json()["detail"].lower()


# --- Tests du Filtrage Amont OCR / Ardoise ---

def test_ocr_payload_valide_succes():
    """Vérifie l'acceptation d'un payload OCR base64 valide de taille normale."""
    b64_valide = base64.b64encode(b"image_ardoise_manuscrite_2x+4=10").decode("utf-8")
    payload = {"image_b64": f"data:image/png;base64,{b64_valide}", "exercice_id": "exo-01"}
    
    response = client.post("/api/v1/test-ocr", json=payload)
    assert response.status_code == 200
    assert response.json()["statut"] == "ocr_valide"


def test_ocr_payload_trop_gros_refuse_413():
    """Vérifie le rejet Fail-Closed (413) si le payload OCR dépasse 2 Mo."""
    # Création d'une chaîne de plus de 2 Mo (2 * 1024 * 1024 + 100 octets)
    gros_str = "A" * (MAX_OCR_PAYLOAD_BYTES + 100)
    payload = {"image_b64": gros_str, "exercice_id": "exo-01"}
    
    response = client.post("/api/v1/test-ocr", json=payload)
    assert response.status_code == 413
    assert "payload_ocr_trop_volumineux" in response.json()["detail"]


def test_ocr_payload_corrompu_refuse_400():
    """Vérifie le rejet (400) avant tout traitement IA si le base64 est corrompu."""
    payload_corrompu = {"image_b64": "data:image/png;base64,!!!!!NOT_VALID_BASE64_BYTES!!!!!=="}
    
    response = client.post("/api/v1/test-ocr", json=payload_corrompu)
    assert response.status_code == 400
    assert "corrompu" in response.json()["detail"] or "invalide" in response.json()["detail"]


def test_ocr_payload_vide_refuse_400():
    """Vérifie le rejet (400) si le payload est vide."""
    payload_vide = {"image_b64": "   "}
    
    response = client.post("/api/v1/test-ocr", json=payload_vide)
    assert response.status_code == 400
    assert "vides" in response.json()["detail"]
