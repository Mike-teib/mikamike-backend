"""
Module Sécurité Fail-Closed & Validation OCR — MikaMike.
Conforme au Cahier des Charges §8.
"""

from app.api.v1.security.fail_closed import (
    exiger_session_active,
    valider_payload_ocr,
    OcrPayload,
    MAX_OCR_PAYLOAD_BYTES
)

__all__ = [
    "exiger_session_active",
    "valider_payload_ocr",
    "OcrPayload",
    "MAX_OCR_PAYLOAD_BYTES"
]
