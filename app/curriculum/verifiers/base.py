"""base.py — Verdicts communs à tous les vérificateurs."""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Tuple


class Verdict(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    AMBIGUOUS = "AMBIGUOUS"
    NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"


class Resultat(NamedTuple):
    verdict: Verdict
    raisons: Tuple[str, ...] = ()

    @property
    def valide(self) -> bool:
        return self.verdict == Verdict.VALID


def invalide(*raisons: str) -> Resultat:
    return Resultat(Verdict.INVALID, tuple(raisons))


def revue(*raisons: str) -> Resultat:
    return Resultat(Verdict.NEEDS_HUMAN_REVIEW, tuple(raisons))


def ambigu(*raisons: str) -> Resultat:
    return Resultat(Verdict.AMBIGUOUS, tuple(raisons))


def valide(*raisons: str) -> Resultat:
    return Resultat(Verdict.VALID, tuple(raisons))
