"""
quiz.py — Contrôles déterministes d'UNE question de quiz (agent D).

La clé `reference_answer` est indépendante des choix : le choix désigné par
`correct_answer` doit lui être équivalent (check_answer avec `answer_kind`), et AUCUN
autre choix ne doit l'être.

Codes d'anomalie STABLES (code — sévérité — signification) :
  NOTION_UNKNOWN               BLOCKER  notion_id absent du registre
  NOTION_NOT_PROVEN            BLOCKER  notion.proof_status != PROVEN_OFFICIAL
  NOTION_WITHOUT_SOURCE        BLOCKER  notion sans source_id, ou source_id absent du registre des sources
  SUBJECT_MISMATCH             ERROR    matière du quiz ≠ matière de la notion
  LEVEL_MISMATCH               ERROR    niveau du quiz ≠ niveau de la notion
  CORRECT_ANSWER_WRONG         BLOCKER  choices[correct_answer] non équivalent à reference_answer
  CORRECT_ANSWER_UNDECIDABLE   ERROR    équivalence du choix correct indécidable (AMBIGUOUS / REVIEW)
  MULTIPLE_CORRECT             BLOCKER  un autre choix est équivalent à reference_answer
  DISTRACTOR_UNDECIDABLE       WARNING  un distracteur ne peut pas être départagé automatiquement
  DUPLICATE_CHOICES            ERROR    deux choix identiques après normalisation
  EMPTY_CHOICE                 ERROR    choix vide
  AMBIGUOUS_CHOICE             ERROR    « toutes les réponses », « aucune », « je ne sais pas »…
  ANSWER_IN_QUESTION           ERROR    la réponse figure dans la question (frontière de jeton)
  EXPLANATION_MISSING          ERROR    explication vide
  EXPLANATION_TOO_SHORT        WARNING  explication de moins de 25 caractères utiles
  DISTRACTOR_RATIONALE_MISSING WARNING  un distracteur sans justification
  LENGTH_LEAK                  WARNING  choix correct > 2× le plus long distracteur et > 20 caractères
  IMPLAUSIBLE_DISTRACTOR       WARNING  type incohérent (numérique vs texte) avec la bonne réponse
  MATH_NOTATION_BROKEN         ERROR    notation corrompue (question, choix, explication, justifications)
  FIXTURE_IN_BANK              WARNING  un quiz FIXTURE_TEST figure dans la banque du registre
  PUBLISHED_FORBIDDEN          BLOCKER  statut PUBLISHED (quiz ou notion) interdit dans ce chantier
"""

from __future__ import annotations

import re
from typing import List

from pedagogy.checks.answers import check_answer_detailed, normalize_answer_text, text_contains_answer
from pedagogy.checks.math_notation import integrity_anomalies
from pedagogy.checks.verdict import Verdict
from pedagogy.issues import Issue, Severity
from pedagogy.models import AnswerKind, ExpectedAnswer, GenerationOrigin, ProofStatus, PublicationStatus, QuizItem
from pedagogy.registry import Registry

B, E, W = Severity.BLOCKER, Severity.ERROR, Severity.WARNING

MIN_EXPLANATION_CHARS = 25
AMBIGUOUS_CHOICE_RE = re.compile(
    r"(?i)^\s*(toutes?\s+les\s+r[ée]ponses|aucune(\s+des?\s+(r[ée]ponses|propositions)(\s+pr[ée]c[ée]dentes)?)?"
    r"|je\s+ne\s+sais\s+pas|on\s+ne\s+peut\s+pas\s+savoir|les\s+deux|autre|toutes?\s+les\s+propositions)\b"
)
_NUMERIC_RE = re.compile(
    r"^\s*[-+−]?\s*\(?\s*\d[\d\s]*(?:[.,]\d+)?(?:\s*/\s*\d+)?\)?"
    r"(?:\s*(?:[×x*·]\s*10\s*\^?\s*\{?[-−+]?\d+\}?|[eE][-−+]?\d+))?"
    r"\s*(?:[A-Za-zµμΩ°%/.·⁻¹²³^\-0-9]{0,12})\s*$"
)
_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ]{4,}")


def _is_numeric(s: str) -> bool:
    return bool(_NUMERIC_RE.match(s or "")) or bool(re.fullmatch(r"[\d\s+\-−*/×÷^().,=²³√π]+", s or "") and
                                                  re.search(r"\d", s or ""))


def _is_text(s: str) -> bool:
    return bool(_WORD_RE.search(s or "")) and not re.search(r"\d", s or "")


def validate_quiz(q: QuizItem, reg: Registry) -> List[Issue]:
    """Renvoie toutes les anomalies d'une question de quiz (liste vide = conforme)."""
    issues: List[Issue] = []
    oid = q.quiz_id

    def add(code: str, sev: Severity, detail: str = "") -> None:
        issues.append(Issue(code, sev, oid, detail))

    # ------------------------------------------------------------------ notion
    notion = reg.notions.get(q.notion_id)
    if notion is None:
        add("NOTION_UNKNOWN", B, q.notion_id)
    else:
        if notion.proof_status != ProofStatus.PROVEN_OFFICIAL:
            add("NOTION_NOT_PROVEN", B, f"{q.notion_id}:{notion.proof_status.value}")
        if not notion.source_id or notion.source_id not in reg.sources:
            add("NOTION_WITHOUT_SOURCE", B, f"{q.notion_id}:{notion.source_id or '-'}")
        if notion.subject != q.subject:
            add("SUBJECT_MISMATCH", E, f"quiz={q.subject.value} notion={notion.subject.value}")
        if notion.level != q.level:
            add("LEVEL_MISMATCH", E, f"quiz={q.level.value} notion={notion.level.value}")
        if notion.publication_status == PublicationStatus.PUBLISHED:
            add("PUBLISHED_FORBIDDEN", B, f"notion {q.notion_id} PUBLISHED")

    if q.publication_status == PublicationStatus.PUBLISHED:
        add("PUBLISHED_FORBIDDEN", B, "quiz PUBLISHED")
    if q.generation_origin == GenerationOrigin.FIXTURE_TEST and q.quiz_id in reg.quizzes:
        add("FIXTURE_IN_BANK", W, "quiz de test présent dans la banque")

    # ------------------------------------------------------------------ notation
    fields = [("question", q.question), ("explanation", q.explanation)]
    fields += [(f"choice[{i}]", c) for i, c in enumerate(q.choices)]
    fields += [(f"rationale[{i}]", r) for i, r in sorted(q.distractor_rationale.items())]
    for name, text in fields:
        anomalies = integrity_anomalies(text)
        if anomalies:
            add("MATH_NOTATION_BROKEN", E, f"{name}:{','.join(anomalies)}")

    # ------------------------------------------------------------------ choix
    norm = [normalize_answer_text(c) for c in q.choices]
    for i, c in enumerate(q.choices):
        if not c.strip():
            add("EMPTY_CHOICE", E, f"choice[{i}]")
        elif AMBIGUOUS_CHOICE_RE.search(c):
            add("AMBIGUOUS_CHOICE", E, f"choice[{i}]={c!r}")
    seen = {}
    for i, n in enumerate(norm):
        if not n:
            continue
        if n in seen:
            add("DUPLICATE_CHOICES", E, f"choice[{seen[n]}] = choice[{i}]")
        else:
            seen[n] = i

    # ------------------------------------------------------------------ clé
    if q.answer_kind == AnswerKind.RUBRIC:
        add("CORRECT_ANSWER_UNDECIDABLE", E, "answer_kind RUBRIC incompatible avec un quiz à choix")
        ref = None
    else:
        value = q.reference_answer
        if q.answer_kind == AnswerKind.CHOICE:
            value = q.reference_answer.strip()
        ref = ExpectedAnswer(kind=q.answer_kind, value=value)
    correct = q.choices[q.correct_answer]
    if ref is not None:
        student_for = (lambda i: str(i)) if q.answer_kind == AnswerKind.CHOICE else (lambda i: q.choices[i])
        res = check_answer_detailed(ref, student_for(q.correct_answer))
        if res.verdict == Verdict.INVALID:
            add("CORRECT_ANSWER_WRONG", B, f"{correct!r} ≠ {q.reference_answer!r}:{','.join(res.reasons)}")
        elif res.undecided:
            add("CORRECT_ANSWER_UNDECIDABLE", E, f"{res.verdict.value}:{','.join(res.reasons)}")
        if q.answer_kind != AnswerKind.CHOICE:
            for i, c in enumerate(q.choices):
                if i == q.correct_answer or not c.strip():
                    continue
                r = check_answer_detailed(ref, c)
                if r.verdict == Verdict.VALID:
                    add("MULTIPLE_CORRECT", B, f"choice[{i}]={c!r} équivalent à la référence")
                elif r.undecided and not AMBIGUOUS_CHOICE_RE.search(c):
                    add("DISTRACTOR_UNDECIDABLE", W, f"choice[{i}]:{r.verdict.value}:{','.join(r.reasons)}")

    # ------------------------------------------------------------------ fuites
    leak = [q.reference_answer] + ([correct] if correct.strip() else [])
    if any(text_contains_answer(q.question, a, min_length=3) for a in leak if len(a) <= 200):
        add("ANSWER_IN_QUESTION", E, q.reference_answer)

    # ------------------------------------------------------------------ explication
    expl = q.explanation.strip()
    if not expl:
        add("EXPLANATION_MISSING", E)
    elif len(expl) < MIN_EXPLANATION_CHARS:
        add("EXPLANATION_TOO_SHORT", W, f"{len(expl)} caractères")

    # ------------------------------------------------------------------ distracteurs
    distractors = [i for i in range(len(q.choices)) if i != q.correct_answer]
    for i in distractors:
        if not q.distractor_rationale.get(i, "").strip():
            add("DISTRACTOR_RATIONALE_MISSING", W, f"choice[{i}]")
    longest = max((len(q.choices[i].strip()) for i in distractors), default=0)
    if len(correct.strip()) > 20 and len(correct.strip()) > 2 * longest:
        add("LENGTH_LEAK", W, f"{len(correct.strip())} vs {longest}")
    if _is_numeric(correct) or _is_text(correct):
        for i in distractors:
            c = q.choices[i]
            if not c.strip() or AMBIGUOUS_CHOICE_RE.search(c):
                continue
            if (_is_numeric(correct) and _is_text(c)) or (_is_text(correct) and _is_numeric(c)):
                add("IMPLAUSIBLE_DISTRACTOR", W, f"choice[{i}]={c!r}")
    return issues
