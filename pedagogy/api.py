"""
api.py — API pédagogique en LECTURE SEULE (préparée, NON montée dans main.py).

  GET /pedagogy/subjects
  GET /pedagogy/levels
  GET /pedagogy/notions            ?subject=&level=&notion_id=&difficulty=&include_unproven=&limit=&offset=
  GET /pedagogy/notions/{id}
  GET /pedagogy/exercises          ?subject=&level=&notion_id=&difficulty=&limit=&offset=
  GET /pedagogy/quiz               ?subject=&level=&notion_id=&difficulty=&limit=&offset=

Règles :
  - aucune route d'écriture ;
  - exercices et quiz servis UNIQUEMENT s'ils sont rattachés à une notion
    PROVEN_OFFICIAL, sans blocage QA, et jamais s'ils sont des fixtures de test ;
  - les notions non prouvées ne sont listées que sur demande explicite
    (include_unproven=true, usage interne) et portent toujours leur proof_status ;
  - pagination bornée.

Montage (décision ultérieure, hors de ce chantier) :
    from pedagogy.api import build_router
    app.include_router(build_router(), prefix="/api/v1")
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from pedagogy.models import (
    LEVEL_ORDER,
    SUBJECT_LEVELS,
    DifficultyBand,
    GenerationOrigin,
    Level,
    ProofStatus,
    QAStatus,
    Subject,
)
from pedagogy.registry import Registry, load_registry

MAX_LIMIT = 200
_SERVABLE_QA = {QAStatus.AUTO_PASSED, QAStatus.HUMAN_APPROVED}


def _page(items: List[Dict[str, Any]], limit: int, offset: int) -> Dict[str, Any]:
    return {"total": len(items), "limit": limit, "offset": offset, "items": items[offset:offset + limit]}


def _proven(reg: Registry, notion_id: str) -> bool:
    n = reg.notions.get(notion_id)
    return bool(n and n.proof_status == ProofStatus.PROVEN_OFFICIAL)


def build_router(registry: Optional[Registry] = None) -> APIRouter:
    reg = registry if registry is not None else load_registry()
    router = APIRouter(prefix="/pedagogy", tags=["pedagogy (lecture seule)"])

    @router.get("/subjects")
    def subjects() -> Dict[str, Any]:
        return {"items": [
            {"subject": s.value, "levels": [lv.value for lv in LEVEL_ORDER if lv in SUBJECT_LEVELS[s]]}
            for s in Subject
        ]}

    @router.get("/levels")
    def levels() -> Dict[str, Any]:
        return {"items": [lv.value for lv in LEVEL_ORDER]}

    @router.get("/notions")
    def notions(
        subject: Optional[Subject] = None,
        level: Optional[Level] = None,
        notion_id: Optional[str] = Query(default=None, max_length=120),
        difficulty: Optional[int] = Query(default=None, ge=1, le=5),
        include_unproven: bool = False,
        limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
        offset: int = Query(default=0, ge=0),
    ) -> Dict[str, Any]:
        out = []
        for n in reg.by_subject_level(subject, level):
            if notion_id and n.notion_id != notion_id:
                continue
            if difficulty is not None and n.difficulty != difficulty:
                continue
            if not include_unproven and n.proof_status != ProofStatus.PROVEN_OFFICIAL:
                continue
            out.append(n.model_dump(mode="json"))
        return _page(out, limit, offset)

    @router.get("/notions/{notion_id}")
    def notion(notion_id: str) -> Dict[str, Any]:
        n = reg.notions.get(notion_id)
        if n is None:
            raise HTTPException(status_code=404, detail="notion_inconnue")
        return n.model_dump(mode="json")

    def _servable(items, subject, level, notion_id, difficulty):
        out = []
        for it in sorted(items, key=lambda x: getattr(x, "exercise_id", getattr(x, "quiz_id", ""))):
            if it.generation_origin == GenerationOrigin.FIXTURE_TEST or it.qa_status not in _SERVABLE_QA:
                continue
            if not _proven(reg, it.notion_id):
                continue
            if subject and it.subject != subject or level and it.level != level:
                continue
            if notion_id and it.notion_id != notion_id or difficulty and it.difficulty != difficulty:
                continue
            out.append(it.model_dump(mode="json"))
        return out

    @router.get("/exercises")
    def exercises(
        subject: Optional[Subject] = None,
        level: Optional[Level] = None,
        notion_id: Optional[str] = Query(default=None, max_length=120),
        difficulty: Optional[DifficultyBand] = None,
        limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
        offset: int = Query(default=0, ge=0),
    ) -> Dict[str, Any]:
        return _page(_servable(reg.exercises.values(), subject, level, notion_id, difficulty), limit, offset)

    @router.get("/quiz")
    def quiz(
        subject: Optional[Subject] = None,
        level: Optional[Level] = None,
        notion_id: Optional[str] = Query(default=None, max_length=120),
        difficulty: Optional[DifficultyBand] = None,
        limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
        offset: int = Query(default=0, ge=0),
    ) -> Dict[str, Any]:
        return _page(_servable(reg.quizzes.values(), subject, level, notion_id, difficulty), limit, offset)

    return router
