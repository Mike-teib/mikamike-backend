"""qa_fixtures.py — Constructeurs de données FICTIVES pour les tests QA (agent E)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List

from pedagogy.models import (
    CYCLE_OF_LEVEL,
    SUBJECT_CODE,
    Exercise,
    Level,
    Notion,
    OfficialSource,
    QuizItem,
    Subject,
    normalize_title,
    slugify,
)
from pedagogy.registry import Registry


def source_dict(source_id="SRC-TEST", subjects=("MATHS",), levels=("6E",), **kw) -> Dict:
    d = {
        "source_id": source_id,
        "source_type": "OFFICIAL_BO",
        "title": "Programme fictif de test",
        "publisher": "Test",
        "reference": "BO fictif",
        "subjects": list(subjects),
        "levels": list(levels),
        "school_year_start": "2020-2021",
        "school_year_end": None,
        "retrieval": "EXPECTED",
        "local_path": "",
        "sha256": "",
    }
    d.update(kw)
    return d


def notion_dict(title: str, subject="MATHS", level="6E", domain_code="NC", **kw) -> Dict:
    subj, lv = Subject(subject), Level(level)
    d = {
        "notion_id": f"{SUBJECT_CODE[subj]}.{lv.value}.{domain_code}.{slugify(title)}",
        "subject": subject,
        "level": level,
        "cycle": CYCLE_OF_LEVEL[lv].value,
        "school_year": "2025-2026",
        "official_program_version": "programme fictif",
        "domain": "Domaine fictif",
        "domain_code": domain_code,
        "chapter": "Chapitre fictif",
        "title": title,
        "normalized_title": normalize_title(title),
        "learning_objectives": ["objectif"],
        "common_mistakes": ["erreur"],
        "difficulty": 2,
        "source_type": "OFFICIAL_BO",
        "source_id": "SRC-TEST",
        "source_title": "Programme fictif de test",
        "source_url_or_ref": "BO fictif",
    }
    d.update(kw)
    return d


def notion(title: str, **kw) -> Notion:
    return Notion.model_validate(notion_dict(title, **kw))


def registry(notions: Iterable[Notion] = (), sources: Iterable[Dict] = (source_dict(),), exercises=(), quizzes=()) -> Registry:
    reg = Registry()
    for s in sources:
        src = OfficialSource.model_validate(s)
        reg.sources[src.source_id] = src
    for n in notions:
        reg.notions[n.notion_id] = n
    for e in exercises:
        reg.exercises[e.exercise_id] = e
    for q in quizzes:
        reg.quizzes[q.quiz_id] = q
    return reg


def exercise_dict(ex_id: str, notion_id: str, statement: str, subject="MATHS", level="6E",
                  difficulty="APPLICATION", **kw) -> Dict:
    d = {
        "exercise_id": ex_id,
        "notion_id": notion_id,
        "subject": subject,
        "level": level,
        "difficulty": difficulty,
        "exercise_type": "SHORT_ANSWER",
        "statement": statement,
        "expected_answer": {"kind": "EXACT_TEXT", "value": "reponse"},
        "solution": "solution",
        "step_by_step_solution": ["etape"],
        "hints": ["indice"],
        "remediation": "revoir le cours",
        "estimated_time_min": 3,
        "skills_tested": ["calculer"],
        "source_notions": [notion_id],
        "generation_origin": "FIXTURE_TEST",
    }
    d.update(kw)
    return d


def exercise(*a, **kw) -> Exercise:
    return Exercise.model_validate(exercise_dict(*a, **kw))


def quiz_dict(q_id: str, notion_id: str, question: str, choices=("un", "deux", "trois"), subject="MATHS",
              level="6E", difficulty="APPLICATION", **kw) -> Dict:
    d = {
        "quiz_id": q_id,
        "notion_id": notion_id,
        "subject": subject,
        "level": level,
        "question": question,
        "choices": list(choices),
        "correct_answer": 0,
        "reference_answer": choices[0],
        "explanation": "explication de test",
        "difficulty": difficulty,
        "generation_origin": "FIXTURE_TEST",
    }
    d.update(kw)
    return d


def quiz(*a, **kw) -> QuizItem:
    return QuizItem.model_validate(quiz_dict(*a, **kw))


def write_data_dir(root: Path, notion_files: Dict[str, Dict], sources: List[Dict],
                   exercises: List[Dict] = (), quizzes: List[Dict] = ()) -> Path:
    data = root / "data"
    (data / "sources").mkdir(parents=True, exist_ok=True)
    (data / "sources" / "official_sources.json").write_text(
        json.dumps({"schema_version": "1.0", "sources": sources}, ensure_ascii=False), encoding="utf-8")
    for rel, content in notion_files.items():
        p = data / "notions" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False), encoding="utf-8")
    if exercises:
        p = data / "bank" / "exercises" / "test.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"exercises": list(exercises)}, ensure_ascii=False), encoding="utf-8")
    if quizzes:
        p = data / "bank" / "quizzes" / "test.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"quizzes": list(quizzes)}, ensure_ascii=False), encoding="utf-8")
    return data


def notion_file(subject: str, level: str, notions: List[Dict]) -> Dict:
    return {
        "subject": subject,
        "level": level,
        "generated_by": "tests",
        "disclaimer": "Données fictives de test.",
        "notions": notions,
    }
