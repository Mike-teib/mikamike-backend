"""
observabilite.py — Journalisation structurée SANS données sensibles (lot 25, session 4).

Une ligne JSON par requête (logger « mikamike.http ») :
  {"event": "http_request", "request_id", "method", "route", "status", "duration_ms", "error_code"}
- `route` = GABARIT de la route (« /api/v1/rgpd/export/{student_pseudo_id} »), jamais le chemin
  réel : un pseudo-id, un identifiant de tutorat ou de séance n'apparaissent pas dans les journaux ;
- jamais : en-têtes (Authorization), chaîne de requête, corps (mots de passe, codes d'invitation,
  jetons de vérification), adresse IP, e-mail ;
- `error_code` = code d'erreur court de l'API (`jeton_revoque`, `invitation_invalide`…) ;
- `X-Request-ID` : repris s'il est sûr ([A-Za-z0-9-]{8,64}), sinon remplacé (anti injection de
  journaux), et renvoyé dans la réponse ;
- exception non rattrapée ⇒ 500 JSON `{"detail": "erreur_interne", "request_id"}`, journalisée par
  son TYPE seulement (ni message, ni trace dans la réponse).
`journaliser(event, **champs)` n'accepte que des clés de la liste blanche (les autres sont retirées).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

journal = logging.getLogger("mikamike.http")

_RID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
_CODE = re.compile(r"^[a-z][a-z0-9_]{2,59}$")
CHAMPS_AUTORISES = frozenset({"event", "request_id", "method", "route", "status", "duration_ms", "error_code",
                              "exception", "session_ref", "count", "lot", "etape"})


def journaliser(event: str, **champs: Any) -> None:
    ligne = {"event": event, **{k: v for k, v in champs.items() if k in CHAMPS_AUTORISES}}
    journal.info(json.dumps(ligne, ensure_ascii=False, sort_keys=True, default=str))


def _code_erreur(corps: bytes) -> str | None:
    try:
        data = json.loads(corps.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    d = data.get("detail") if isinstance(data, dict) else None
    if isinstance(d, dict):
        d = d.get("code")
    if isinstance(d, str) and _CODE.fullmatch(d):
        return d
    if isinstance(d, list):
        return "validation"
    return None


class Observabilite:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        entrant = dict(scope.get("headers", ())).get(b"x-request-id", b"").decode("latin-1")
        rid = entrant if _RID.fullmatch(entrant) else uuid.uuid4().hex
        debut = time.perf_counter()
        etat = {"status": 500, "corps": b"", "demarre": False}

        async def envoyer(msg):
            if msg["type"] == "http.response.start":
                etat["status"] = msg["status"]
                etat["demarre"] = True
                msg = {**msg, "headers": [*msg.get("headers", []), (b"x-request-id", rid.encode())]}
            elif msg["type"] == "http.response.body" and etat["status"] >= 400 and len(etat["corps"]) < 2048:
                etat["corps"] += msg.get("body", b"")[:2048]
            await send(msg)

        exception = None
        try:
            await self.app(scope, receive, envoyer)
        except Exception as exc:  # jamais de trace ni de message vers le client
            exception = type(exc).__name__
            if not etat["demarre"]:
                corps = json.dumps({"detail": "erreur_interne", "request_id": rid}).encode()
                await send({"type": "http.response.start", "status": 500,
                            "headers": [(b"content-type", b"application/json"),
                                        (b"content-length", str(len(corps)).encode()),
                                        (b"x-request-id", rid.encode())]})
                await send({"type": "http.response.body", "body": corps})
                etat["status"] = 500
        finally:
            route = getattr(scope.get("route"), "path", None) or "(non_routee)"
            # Le gabarit mémorisé est celui du routeur (sans le préfixe d'inclusion /api/v1).
            if route.startswith("/") and scope.get("path", "").startswith("/api/v1") and not route.startswith("/api/v1"):
                route = "/api/v1" + route
            journaliser("http_request", request_id=rid, method=scope.get("method"), route=route,
                        status=etat["status"], duration_ms=round((time.perf_counter() - debut) * 1000, 2),
                        error_code=_code_erreur(etat["corps"]) if etat["status"] >= 400 else None,
                        **({"exception": exception} if exception else {}))
