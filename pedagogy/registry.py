"""
registry.py — Chargement du registre canonique (notions, sources, banque) depuis
pedagogy/data/. Lecture seule, déterministe (ordre trié), validation stricte.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from pedagogy.models import (
    Exercise,
    Level,
    Notion,
    NotionFile,
    OfficialSource,
    QuizItem,
    Subject,
)

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"
REPO_ROOT = PACKAGE_DIR.parent


class RegistryError(ValueError):
    pass


@dataclass
class Registry:
    sources: Dict[str, OfficialSource] = field(default_factory=dict)
    notions: Dict[str, Notion] = field(default_factory=dict)
    notion_files: Dict[str, NotionFile] = field(default_factory=dict)  # chemin relatif → fichier
    exercises: Dict[str, Exercise] = field(default_factory=dict)
    quizzes: Dict[str, QuizItem] = field(default_factory=dict)
    load_errors: List[Tuple[str, str]] = field(default_factory=list)  # (chemin, raison)

    def by_subject_level(self, subject: Optional[Subject] = None, level: Optional[Level] = None) -> List[Notion]:
        return [
            n for _, n in sorted(self.notions.items())
            if (subject is None or n.subject == subject) and (level is None or n.level == level)
        ]


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _json_files(folder: Path) -> Iterable[Path]:
    return sorted(p for p in folder.rglob("*.json") if p.is_file()) if folder.is_dir() else []


def load_registry(data_dir: Path = DATA_DIR, *, strict: bool = False) -> Registry:
    """
    Charge tout le registre. En mode non strict, un fichier invalide est consigné dans
    load_errors (la QA le signale) au lieu d'interrompre le chargement.
    """
    reg = Registry()

    def fail(path: Path, reason: str) -> None:
        rel = str(path.relative_to(data_dir)) if data_dir in path.parents else str(path)
        if strict:
            raise RegistryError(f"{rel}: {reason}")
        reg.load_errors.append((rel, reason))

    src_file = data_dir / "sources" / "official_sources.json"
    if src_file.is_file():
        try:
            for raw in _read_json(src_file)["sources"]:
                s = OfficialSource.model_validate(raw)
                if s.source_id in reg.sources:
                    fail(src_file, f"source_dupliquee:{s.source_id}")
                reg.sources[s.source_id] = s
        except Exception as exc:  # noqa: BLE001 — consigné, pas avalé
            fail(src_file, f"sources_invalides:{type(exc).__name__}:{str(exc).splitlines()[0][:200]}")

    for path in _json_files(data_dir / "notions"):
        try:
            nf = NotionFile.model_validate(_read_json(path))
        except Exception as exc:  # noqa: BLE001
            fail(path, f"fichier_notions_invalide:{type(exc).__name__}:{str(exc).splitlines()[0][:300]}")
            continue
        reg.notion_files[str(path.relative_to(data_dir))] = nf
        for n in nf.notions:
            if n.notion_id in reg.notions:
                fail(path, f"notion_id_duplique:{n.notion_id}")
                continue
            reg.notions[n.notion_id] = n

    for path in _json_files(data_dir / "bank" / "exercises"):
        try:
            for raw in _read_json(path)["exercises"]:
                ex = Exercise.model_validate(raw)
                if ex.exercise_id in reg.exercises:
                    fail(path, f"exercise_id_duplique:{ex.exercise_id}")
                    continue
                reg.exercises[ex.exercise_id] = ex
        except Exception as exc:  # noqa: BLE001
            fail(path, f"exercices_invalides:{type(exc).__name__}:{str(exc).splitlines()[0][:300]}")

    for path in _json_files(data_dir / "bank" / "quizzes"):
        try:
            for raw in _read_json(path)["quizzes"]:
                q = QuizItem.model_validate(raw)
                if q.quiz_id in reg.quizzes:
                    fail(path, f"quiz_id_duplique:{q.quiz_id}")
                    continue
                reg.quizzes[q.quiz_id] = q
        except Exception as exc:  # noqa: BLE001
            fail(path, f"quiz_invalides:{type(exc).__name__}:{str(exc).splitlines()[0][:300]}")

    return reg
