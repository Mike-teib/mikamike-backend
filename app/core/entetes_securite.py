"""
entetes_securite.py — En-têtes HTTP de sécurité et erreurs de validation sans écho (lot 21, S4).

- `EntetesSecurite` (ASGI) : nosniff, anti-framing, pas de référent, pas de cache pour l'API ;
  CSP stricte sur les réponses JSON (la documentation Swagger, HTML, n'est pas concernée).
- `erreur_validation` : les 422 ne renvoient plus la valeur saisie (`input`) ni le contexte :
  un mot de passe trop court était renvoyé tel quel dans le corps de la réponse (S4-03).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_COMMUNS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
]
_JSON = [
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
    (b"cache-control", b"no-store"),
]


class EntetesSecurite:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def envoyer(message):
            if message["type"] == "http.response.start":
                entetes = list(message.get("headers", []))
                presents = {k.lower() for k, _ in entetes}
                ajout = list(_COMMUNS)
                ctype = dict((k.lower(), v) for k, v in entetes).get(b"content-type", b"")
                if ctype.startswith(b"application/json"):
                    ajout += _JSON
                entetes += [(k, v) for k, v in ajout if k not in presents]
                message = dict(message, headers=entetes)
            await send(message)

        await self.app(scope, receive, envoyer)


async def erreur_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    detail = [{"type": e.get("type"), "loc": list(e.get("loc", ())), "msg": e.get("msg")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": detail})
