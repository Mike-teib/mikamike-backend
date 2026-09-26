"""
dedup.py — Empreintes et similarité pour la déduplication (exercices, quiz, notions).

- empreinte_exacte : même énoncé et même réponse (normalisés) ;
- empreinte_gabarit : même énoncé une fois les NOMBRES masqués (« 3x + 2 = 8 » ≡
  « 5x + 1 = 11 ») — même structure de question ;
- similarite : Jaccard sur les 3-grammes de mots (quasi-doublons rédactionnels).

Aucune suppression : ces fonctions ne servent qu'à signaler / bloquer une création.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import FrozenSet

_NOMBRE = re.compile(r"\d+(?:[.,]\d+)?")


def normaliser(texte: str) -> str:
    t = unicodedata.normalize("NFC", texte or "").casefold()
    t = re.sub(r"[\s ]+", " ", t)
    return re.sub(r"\s*([=+\-×*/^()<>,;:.!?])\s*", r"\1", t).strip()


def _h(t: str) -> str:
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def empreinte_exacte(enonce: str, reponse: str = "") -> str:
    return _h(normaliser(enonce) + "\x1f" + normaliser(reponse))


def empreinte_gabarit(enonce: str) -> str:
    return _h(_NOMBRE.sub("#", normaliser(enonce)))


def _shingles(texte: str, n: int = 3) -> FrozenSet[str]:
    mots = re.findall(r"\w+|[=+\-×*/^]", normaliser(texte))
    if len(mots) < n:
        return frozenset({" ".join(mots)})
    return frozenset(" ".join(mots[i:i + n]) for i in range(len(mots) - n + 1))


def similarite(a: str, b: str) -> float:
    sa, sb = _shingles(a), _shingles(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)
