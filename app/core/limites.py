"""
limites.py — Borne la taille du corps des requêtes HTTP (revue session 2, R2-20).

Middleware ASGI pur : refus 413 AVANT lecture si `Content-Length` dépasse la limite (ou est
invalide), et comptage en flux pour les corps sans longueur annoncée (chunked). Aucun corps
de plusieurs centaines de Mo n'est donc lu en mémoire ni parsé.

MIKA_MAX_BODY_BYTES (défaut 4 Mio : l'état de séance est borné à 2 Mo + enveloppe JSON).
"""

from __future__ import annotations

import json
import os

DEFAUT_MAX_OCTETS = 4 * 1024 * 1024


class _TropVolumineux(Exception):
    pass


def max_octets_configure() -> int:
    brut = os.getenv("MIKA_MAX_BODY_BYTES", str(DEFAUT_MAX_OCTETS))
    try:
        v = int(brut)
    except ValueError as exc:
        raise ValueError("MIKA_MAX_BODY_BYTES non entier") from exc
    if not 1024 <= v <= 64 * 1024 * 1024:
        raise ValueError("MIKA_MAX_BODY_BYTES hors [1 Kio, 64 Mio]")
    return v


class LimiteTailleCorps:
    def __init__(self, app, max_octets: int | None = None):
        self.app = app
        self.max_octets = max_octets if max_octets is not None else max_octets_configure()

    async def _refuser(self, send) -> None:
        corps = json.dumps({"detail": "corps_de_requete_trop_volumineux"}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"),
                                (b"content-length", str(len(corps)).encode())]})
        await send({"type": "http.response.body", "body": corps})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        for nom, valeur in scope.get("headers", ()):
            if nom == b"content-length":
                if not valeur.isdigit() or int(valeur) > self.max_octets:
                    return await self._refuser(send)
        total = 0
        etat = {"demarre": False, "trop": False, "refus_envoye": False}

        async def recevoir():
            nonlocal total
            msg = await receive()
            if msg["type"] == "http.request":
                total += len(msg.get("body", b""))
                if total > self.max_octets:
                    etat["trop"] = True
                    raise _TropVolumineux()
            return msg

        async def envoyer(msg):
            # Le framework peut intercepter l'exception (400 « parsing ») : on substitue alors
            # sa réponse par le 413 attendu.
            if etat["trop"]:
                if not etat["refus_envoye"] and msg["type"] == "http.response.start":
                    etat["refus_envoye"] = True
                    await self._refuser(send)
                return
            if msg["type"] == "http.response.start":
                etat["demarre"] = True
            await send(msg)

        try:
            await self.app(scope, recevoir, envoyer)
        except _TropVolumineux:
            if not etat["demarre"] and not etat["refus_envoye"]:
                etat["refus_envoye"] = True
                await self._refuser(send)
