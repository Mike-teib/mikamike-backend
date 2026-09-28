"""verdict.py — Verdicts communs à tous les contrôles déterministes.

Règle : un contrôle ne renvoie JAMAIS VALID par défaut. Toute entrée non analysable,
hors périmètre ou non prouvée donne AMBIGUOUS ou NEEDS_HUMAN_REVIEW.
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Tuple


class Verdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


UNDECIDED = frozenset({Verdict.AMBIGUOUS, Verdict.NEEDS_HUMAN_REVIEW})


class CheckResult(NamedTuple):
    verdict: Verdict = Verdict.NEEDS_HUMAN_REVIEW
    reasons: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.verdict == Verdict.VALID

    @property
    def undecided(self) -> bool:
        return self.verdict in UNDECIDED


def valid(*reasons: str) -> CheckResult:
    return CheckResult(Verdict.VALID, tuple(reasons))


def invalid(*reasons: str) -> CheckResult:
    return CheckResult(Verdict.INVALID, tuple(reasons))


def ambiguous(*reasons: str) -> CheckResult:
    return CheckResult(Verdict.AMBIGUOUS, tuple(reasons))


def review(*reasons: str) -> CheckResult:
    return CheckResult(Verdict.NEEDS_HUMAN_REVIEW, tuple(reasons))
