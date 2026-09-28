"""issues.py — Type commun des anomalies QA (tous validateurs)."""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class Severity(str, Enum):
    BLOCKER = "BLOCKER"    # interdit l'entrée dans la banque / la publication
    ERROR = "ERROR"        # contenu faux ou incohérent, à corriger
    WARNING = "WARNING"    # suspect, revue humaine recommandée
    INFO = "INFO"


class Issue(NamedTuple):
    code: str          # code stable en MAJUSCULES, ex. NOTION_UNPROVEN
    severity: Severity
    object_id: str     # notion_id / exercise_id / quiz_id / source_id
    detail: str = ""

    def as_dict(self) -> dict:
        return {"code": self.code, "severity": self.severity.value, "object_id": self.object_id, "detail": self.detail}
