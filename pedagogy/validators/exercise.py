"""
exercise.py — Contrôles déterministes d'UN exercice (agent D).

Hors périmètre (QA registre, agent E) : doublons entre items, adéquation au niveau.

Codes d'anomalie STABLES (code — sévérité — signification) :
  NOTION_UNKNOWN                BLOCKER  notion_id absent du registre
  NOTION_NOT_PROVEN             BLOCKER  notion.proof_status != PROVEN_OFFICIAL
  NOTION_NOT_APPROVED           BLOCKER  notion.review_status != APPROVED
  NOTION_WITHOUT_SOURCE         BLOCKER  notion sans source_id, ou source_id absent du registre des sources
  SUBJECT_MISMATCH              ERROR    matière de l'exercice ≠ matière de la notion
  LEVEL_MISMATCH                ERROR    niveau de l'exercice ≠ niveau de la notion
  PREREQUISITE_UNKNOWN          ERROR    un prérequis n'est pas une notion du registre
  SOURCE_NOTION_UNKNOWN         ERROR    une source_notion (≠ notion_id) n'est pas une notion du registre
  ANSWER_MISSING                BLOCKER  réponse attendue vide (ou RUBRIC sans critère)
  SOLUTION_MISSING              ERROR    solution ou étapes vides
  SOLUTION_INCONSISTENT         ERROR    la réponse attendue n'apparaît pas (ou pas d'équivalent prouvé)
                                         dans la dernière étape ni dans la solution
  SELF_CHECK_FAILED             BLOCKER  la réponse attendue ne se valide pas elle-même (check_answer)
  AMBIGUOUS_ANSWER              ERROR    check_answer indécidable (AMBIGUOUS / NEEDS_HUMAN_REVIEW) sur
                                         la réponse attendue alors que le type n'est pas RUBRIC
  QCM_NO_CORRECT                BLOCKER  QCM : réponse non CHOICE, index absent/hors bornes
  QCM_MULTIPLE_CORRECT          BLOCKER  QCM : plusieurs index sans consigne « plusieurs réponses », ou
                                         un autre choix identique/équivalent au choix correct
  ANSWER_IN_STATEMENT           ERROR    la réponse figure dans l'énoncé (recherche par frontière de jeton)
  HINT_REVEALS_ANSWER           WARNING  un indice donne la réponse
  MATH_NOTATION_BROKEN          ERROR    notation LaTeX/Unicode corrompue (énoncé, solution, étapes,
                                         indices, choix, remédiation)
  UNIT_INCOHERENT               ERROR    QUANTITY : unité inconnue, dimension différente de l'unité
                                         demandée par l'énoncé, ou unité manquante alors qu'attendue
  PHYSICALLY_IMPOSSIBLE         ERROR    valeur hors bornes physiques (checks.physics.PHYSICAL_BOUNDS)
  COMMON_ERROR_ACTUALLY_CORRECT ERROR    une « erreur fréquente » listée est validée comme correcte
  FIXTURE_IN_BANK               WARNING  un exercice FIXTURE_TEST figure dans la banque du registre
  PUBLISHED_FORBIDDEN           BLOCKER  statut PUBLISHED (exercice ou notion) interdit dans ce chantier
"""

from __future__ import annotations

import re
from typing import List, Optional

from pedagogy.checks import maths, physics
from pedagogy.checks.answers import (
    answer_texts,
    check_answer_detailed,
    normalize_answer_text,
    parse_choice,
    quantity_expected_text,
    render_expected,
    text_contains_answer,
)
from pedagogy.checks.math_notation import integrity_anomalies
from pedagogy.checks.verdict import Verdict
from pedagogy.issues import Issue, Severity
from pedagogy.models import (
    AnswerKind,
    Exercise,
    ExerciseType,
    ExpectedAnswer,
    GenerationOrigin,
    ProofStatus,
    PublicationStatus,
    ReviewStatus,
    Subject,
)
from pedagogy.registry import Registry

B, E, W = Severity.BLOCKER, Severity.ERROR, Severity.WARNING

MULTI_ANSWER_RE = re.compile(
    r"(?i)plusieurs\s+(bonnes\s+)?r[ée]ponses|une\s+ou\s+plusieurs|toutes\s+les\s+(bonnes\s+)?r[ée]ponses\s+"
    r"(exactes|correctes|justes)|cochez\s+(toutes|les)\b|coche\s+(toutes|les)\b|s[ée]lectionne[rz]?\s+toutes"
)


def _empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


def _choice_equivalent(kind_hint: Optional[AnswerKind], a: str, b: str) -> bool:
    """Deux textes de choix désignent-ils la même réponse ? (égalité normalisée ou équivalence prouvée)."""
    if normalize_answer_text(a) == normalize_answer_text(b):
        return True
    if re.search(r"[A-Za-zÀ-ÿ]{4,}", a + b):  # textes rédigés : égalité normalisée seulement
        return False
    try:
        if physics.parse_quantity(a).unit_text or physics.parse_quantity(b).unit_text:
            return physics.check_quantity(a, b, tolerance_relative=1e-9).ok
    except physics.QuantityError:
        pass
    return maths.equivalent(a, b).verdict == Verdict.VALID


def validate_exercise(ex: Exercise, reg: Registry) -> List[Issue]:
    """Renvoie toutes les anomalies d'un exercice (liste vide = conforme)."""
    issues: List[Issue] = []
    oid = ex.exercise_id

    def add(code: str, sev: Severity, detail: str = "") -> None:
        issues.append(Issue(code, sev, oid, detail))

    # ------------------------------------------------------------------ notion
    notion = reg.notions.get(ex.notion_id)
    if notion is None:
        add("NOTION_UNKNOWN", B, ex.notion_id)
    else:
        if notion.proof_status != ProofStatus.PROVEN_OFFICIAL:
            add("NOTION_NOT_PROVEN", B, f"{ex.notion_id}:{notion.proof_status.value}")
        elif notion.review_status != ReviewStatus.APPROVED:
            add("NOTION_NOT_APPROVED", B, f"{ex.notion_id}:{notion.review_status.value}")
        if not notion.source_id or notion.source_id not in reg.sources:
            add("NOTION_WITHOUT_SOURCE", B, f"{ex.notion_id}:{notion.source_id or '-'}")
        if notion.subject != ex.subject:
            add("SUBJECT_MISMATCH", E, f"exercice={ex.subject.value} notion={notion.subject.value}")
        if notion.level != ex.level:
            add("LEVEL_MISMATCH", E, f"exercice={ex.level.value} notion={notion.level.value}")
        if notion.publication_status == PublicationStatus.PUBLISHED:
            add("PUBLISHED_FORBIDDEN", B, f"notion {ex.notion_id} PUBLISHED")
    for p in ex.prerequisites:
        if p not in reg.notions:
            add("PREREQUISITE_UNKNOWN", E, p)
    for s in ex.source_notions:
        if s != ex.notion_id and s not in reg.notions:
            add("SOURCE_NOTION_UNKNOWN", E, s)

    # ------------------------------------------------------------------ statuts
    if ex.publication_status == PublicationStatus.PUBLISHED:
        add("PUBLISHED_FORBIDDEN", B, "exercice PUBLISHED")
    if ex.generation_origin == GenerationOrigin.FIXTURE_TEST and ex.exercise_id in reg.exercises:
        add("FIXTURE_IN_BANK", W, "exercice de test présent dans la banque")

    # ------------------------------------------------------------------ notation
    fields = [("statement", ex.statement), ("solution", ex.solution), ("remediation", ex.remediation)]
    fields += [(f"step[{i}]", s) for i, s in enumerate(ex.step_by_step_solution)]
    fields += [(f"hint[{i}]", h) for i, h in enumerate(ex.hints)]
    fields += [(f"choice[{i}]", c) for i, c in enumerate(ex.choices)]
    for name, text in fields:
        anomalies = integrity_anomalies(text)
        if anomalies:
            add("MATH_NOTATION_BROKEN", E, f"{name}:{','.join(anomalies)}")

    # ------------------------------------------------------------------ solution
    steps = [s for s in ex.step_by_step_solution if s.strip()]
    if not ex.solution.strip() or not steps:
        add("SOLUTION_MISSING", E, "solution ou étapes vides")

    # ------------------------------------------------------------------ réponse
    exp: ExpectedAnswer = ex.expected_answer
    kind = exp.kind
    if _empty(exp.value) or (kind == AnswerKind.RUBRIC and not any(r.strip() for r in exp.rubric)):
        add("ANSWER_MISSING", B, kind.value)
        return issues  # les contrôles suivants n'ont pas de sens sans réponse

    # QCM
    if ex.exercise_type == ExerciseType.QCM or (kind == AnswerKind.CHOICE and ex.choices):
        idx = parse_choice(exp.value) if kind == AnswerKind.CHOICE else None
        if kind != AnswerKind.CHOICE:
            add("QCM_NO_CORRECT", B, f"kind={kind.value} (CHOICE attendu)")
        elif idx is None or not ex.choices or any(i >= len(ex.choices) for i in idx):
            add("QCM_NO_CORRECT", B, f"index={exp.value!r} choix={len(ex.choices)}")
        else:
            if len(idx) > 1 and not MULTI_ANSWER_RE.search(ex.statement):
                add("QCM_MULTIPLE_CORRECT", B, f"index={list(idx)} sans consigne « plusieurs réponses »")
            if len(idx) == 1:
                good = ex.choices[idx[0]]
                twins = [j for j, c in enumerate(ex.choices) if j != idx[0] and _choice_equivalent(None, good, c)]
                if twins:
                    add("QCM_MULTIPLE_CORRECT", B, f"choix {twins} équivalent(s) au choix correct {idx[0]}")

    # Auto-contrôle
    if kind != AnswerKind.RUBRIC:
        rendered = render_expected(exp)
        self_res = check_answer_detailed(exp, rendered)
        if self_res.verdict == Verdict.INVALID:
            add("SELF_CHECK_FAILED", B, f"{rendered!r}:{','.join(self_res.reasons)}")
        elif self_res.undecided:
            add("AMBIGUOUS_ANSWER", E, f"{self_res.verdict.value}:{','.join(self_res.reasons)}")

    # Cohérence solution ↔ réponse
    if steps and ex.solution.strip():
        _check_solution_consistency(ex, add)

    # Fuites
    for a in answer_texts(exp):
        if text_contains_answer(ex.statement, a):
            add("ANSWER_IN_STATEMENT", E, a)
            break
    leak_texts = list(answer_texts(exp))
    if kind == AnswerKind.CHOICE:
        idx = parse_choice(exp.value)
        if idx and len(idx) == 1 and idx[0] < len(ex.choices):
            leak_texts.append(ex.choices[idx[0]])
    for i, h in enumerate(ex.hints):
        if any(text_contains_answer(h, a, min_length=3 if kind != AnswerKind.CHOICE else 4) for a in leak_texts):
            add("HINT_REVEALS_ANSWER", W, f"hint[{i}]")

    # Unités / bornes physiques
    if kind == AnswerKind.QUANTITY:
        _check_units(ex, add)

    # Erreurs fréquentes réellement correctes
    if kind != AnswerKind.RUBRIC:
        for wrong in ex.common_errors:
            if check_answer_detailed(exp, wrong).verdict == Verdict.VALID:
                add("COMMON_ERROR_ACTUALLY_CORRECT", E, wrong)
    return issues


def _check_solution_consistency(ex: Exercise, add) -> None:
    exp = ex.expected_answer
    kind = exp.kind
    last = [s for s in ex.step_by_step_solution if s.strip()][-1]
    texts = (last, ex.solution)
    ok: Optional[bool] = None
    if kind == AnswerKind.MATH_EXPR:
        ok = any(maths.find_equivalent_in_text(exp.value, t) for t in texts)
    elif kind == AnswerKind.QUANTITY:
        try:
            exp_txt = quantity_expected_text(exp)
        except (physics.QuantityError, maths.MathInputRejected):
            return
        tol = 0.01 if exp.tolerance_relative is None else max(exp.tolerance_relative, 1e-9)
        ok = any(physics.find_quantity_in_text(exp_txt, t, tol) for t in texts)
    elif kind == AnswerKind.EXACT_TEXT:
        vals = exp.value if isinstance(exp.value, (list, tuple)) else [exp.value]
        hay = " ".join(normalize_answer_text(t) for t in texts)
        ok = any(normalize_answer_text(str(v)) and normalize_answer_text(str(v)) in hay for v in vals)
    elif kind == AnswerKind.CHOICE and ex.choices:
        idx = parse_choice(exp.value)
        if not idx or any(i >= len(ex.choices) for i in idx):
            return
        hay = " ".join(normalize_answer_text(t) for t in texts)
        ok = all(
            normalize_answer_text(ex.choices[i]) in hay
            or (not re.search(r"[A-Za-zÀ-ÿ]{4,}", ex.choices[i]) and any(
                maths.find_equivalent_in_text(ex.choices[i], t) for t in texts))
            for i in idx
        )
    if ok is False:
        add("SOLUTION_INCONSISTENT", E, f"réponse {render_expected(exp)!r} absente de la solution / dernière étape")


def _check_units(ex: Exercise, add) -> None:
    exp = ex.expected_answer
    try:
        q = physics.parse_quantity(quantity_expected_text(exp))
    except (physics.QuantityError, maths.MathInputRejected) as exc:
        add("UNIT_INCOHERENT", E, f"attendue illisible:{exc}")
        return
    implied = physics.units_implied_by_text(ex.statement, ignore_single_capitals=ex.subject == Subject.MATHS)
    if implied:
        dims = {u.dim for _, u in implied}
        if not q.unit_text and dims != {physics.DIMENSIONLESS}:
            add("UNIT_INCOHERENT", E, "unité manquante (énoncé : " + ", ".join(t for t, _ in implied) + ")")
        elif q.unit_text and q.unit.dim not in dims:
            add("UNIT_INCOHERENT", E, f"{q.unit_text} ≠ " + ", ".join(t for t, _ in implied))
    violations = physics.physical_bound_violations(physics.to_si(q), q.unit.dim, ex.statement)
    if violations:
        add("PHYSICALLY_IMPOSSIBLE", E, ",".join(violations))
