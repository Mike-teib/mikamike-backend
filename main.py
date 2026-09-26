"""
Point d'entrée FastAPI — MikaMike Backend (autonome).

Lancement :  uvicorn main:app --reload

App minimale montant les routeurs MikaMike (tuteur) et comptes/paiement sous le
préfixe public /api/v1, aux chemins exacts attendus par le frontend :
  POST /api/v1/exercices/soumettre
  GET  /api/v1/parcours/prochaine-etape
  GET  /api/v1/parents/dashboard/{student_pseudo_id}
  POST /api/v1/comptes/inscription | /connexion   ·  GET /api/v1/comptes/moi
  POST /api/v1/paiement/checkout | /webhook       ·  GET /api/v1/paiement/statut
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.mikamike.router import mika_router
from paiement_comptes.router_comptes import router as comptes_router
from paiement_comptes.router_paiement import router as paiement_router
from app.api.v1.escalier.router import escalier_router
from app.api.v1.parcours.router import parcours_graph_router
from app.api.v1.memory.router import memory_router
from app.api.v1.rgpd.router import rgpd_router
from app.api.v1.session.router import session_router
from app.api.v1.auth.router import auth_router

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def _cycle_de_vie(_app: FastAPI):
    # Schéma : jamais de create_all implicite (revue session 2, R2-07). Par défaut
    # (MIKA_DB_INIT=check) l'application REFUSE de démarrer si une base n'est pas à la
    # révision head ; `migrate` applique les migrations ; `none` pour les bases de test.
    from app.core.auth import mode_auth
    from app.db.migrations import initialiser_au_demarrage

    mode_auth()  # configuration d'authentification invalide ⇒ refus de démarrer
    initialiser_au_demarrage()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=_cycle_de_vie,
        title="MikaMike Backend",
        version="1.0.0",
        openapi_url=f"{API_V1_PREFIX}/openapi.json",
        docs_url=f"{API_V1_PREFIX}/docs",
        redoc_url=f"{API_V1_PREFIX}/redoc",
    )

    origins = [o for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["health"])
    @app.get("/healthz", tags=["health"], include_in_schema=False)
    def health():
        return {"status": "ok", "app": "mikamike-backend", "version": "1.0.0"}

    app.include_router(mika_router, prefix=API_V1_PREFIX)
    app.include_router(comptes_router, prefix=API_V1_PREFIX)
    app.include_router(paiement_router, prefix=API_V1_PREFIX)
    app.include_router(escalier_router, prefix=API_V1_PREFIX)
    app.include_router(parcours_graph_router, prefix=API_V1_PREFIX)
    app.include_router(memory_router, prefix=API_V1_PREFIX)
    app.include_router(rgpd_router, prefix=API_V1_PREFIX)
    app.include_router(session_router, prefix=API_V1_PREFIX)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    return app


app = create_app()
