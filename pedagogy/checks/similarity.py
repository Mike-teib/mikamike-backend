"""
similarity.py — Empreintes et similarité pour la déduplication (exercices, quiz, notions).

Adapté de app/curriculum/dedup.py (branche session6-production-hardening), autonome.

- normalize_text      : NFC, casse repliée, espaces simples, espaces autour des opérateurs retirés ;
- exact_fingerprint   : même énoncé et même réponse (normalisés) ;
- template_fingerprint: même énoncé une fois les NOMBRES masqués (« 3x + 2 = 8 » ≡ « 5x + 1 = 11 ») ;
- similarity          : Jaccard sur les 3-grammes de mots (quasi-doublons rédactionnels).

Aucune suppression : ces fonctions servent à signaler / bloquer, jamais à effacer.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import FrozenSet

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "").casefold()
    t = t.replace("’", "'").replace("−", "-")
    t = re.sub(r"[\s  ]+", " ", t)
    return re.sub(r"\s*([=+\-×*/^()<>,;:.!?])\s*", r"\1", t).strip()


def _h(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def exact_fingerprint(statement: str, answer: str = "") -> str:
    return _h(normalize_text(statement) + "\x1f" + normalize_text(answer))


def template_fingerprint(statement: str) -> str:
    return _h(_NUMBER.sub("#", normalize_text(statement)))


def shingles(text: str, n: int = 3) -> FrozenSet[str]:
    words = re.findall(r"\w+|[=+\-×*/^]", normalize_text(text))
    if len(words) < n:
        return frozenset({" ".join(words)}) if words else frozenset()
    return frozenset(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def jaccard(sa: FrozenSet[str], sb: FrozenSet[str]) -> float:
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def similarity(a: str, b: str, n: int = 3) -> float:
    return jaccard(shingles(a, n), shingles(b, n))
