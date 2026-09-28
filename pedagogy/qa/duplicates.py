"""
duplicates.py — Détection de doublons / quasi-doublons entre exercices et entre quiz.

Autonome (normalisation et empreintes propres à ce module). Déterministe.

Codes (préfixe EXERCISE_ ou QUIZ_ selon le type d'objet ; object_id = le second élément
de la paire dans l'ordre trié des identifiants, le détail cite le premier) :

  <P>_DUPLICATE_EXACT     ERROR    même texte normalisé (énoncé + choix triés).
  <P>_DUPLICATE_TEMPLATE  WARNING  même texte une fois les nombres masqués, sur la MÊME notion
                                   (variante paramétrique : diversifier la banque).
  <P>_TOO_SIMILAR         WARNING  Jaccard des 3-grammes de caractères >= 0.85, même matière
                                   et même niveau (hors paires déjà signalées ci-dessus).

Les identifiants dupliqués (exercise_id / quiz_id) sont déjà détectés au chargement du
registre (reg.load_errors → LOAD_ERROR) et ne sont pas re-signalés ici.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import Dict, Iterable, List, NamedTuple, Set, Tuple

from pedagogy.issues import Issue, Severity
from pedagogy.models import Exercise, QuizItem

SIMILARITY_THRESHOLD = 0.85


_SYMBOLS = {
    "×": "*", "·": "*", "÷": "/", "−": "-", "–": "-", "≤": "<=", "≥": ">=", "≠": " neq ", "√": " sqrt ",
    "π": " pi ", "²": "^2", "³": "^3", "∞": " inf ", "°": " deg ", "µ": " mu ", "μ": " mu ", "Δ": " delta ",
    "%": " pct ", "€": " eur ",
}


def normalize_text(text: str) -> str:
    """
    Minuscules, sans accents, ponctuation → espace, espaces simples. Chiffres conservés ;
    les symboles mathématiques usuels sont traduits en ASCII (sinon « 2×3 » deviendrait « 23 »).
    """
    t = text or ""
    for a, b in _SYMBOLS.items():
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").casefold()
    t = re.sub(r"(\d)[,.](\d)", r"\1_\2", t)  # garde 3,5 comme un seul nombre
    t = re.sub(r"[^a-z0-9_+\-*/=^<>()]+", " ", t)
    return " ".join(t.split())


def mask_numbers(text: str) -> str:
    return re.sub(r"\d+(?:_\d+)?", "#", text)


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trigrams(text: str) -> Set[str]:
    padded = f"  {text} "
    return {padded[i:i + 3] for i in range(len(padded) - 2)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


class Item(NamedTuple):
    item_id: str
    notion_id: str
    group: Tuple[str, str]  # (matière, niveau)
    text: str               # texte normalisé


def exercise_item(ex: Exercise) -> Item:
    raw = " ".join([ex.statement, *sorted(ex.choices)])
    return Item(ex.exercise_id, ex.notion_id, (ex.subject.value, ex.level.value), normalize_text(raw))


def quiz_item(q: QuizItem) -> Item:
    raw = " ".join([q.question, *sorted(q.choices)])
    return Item(q.quiz_id, q.notion_id, (q.subject.value, q.level.value), normalize_text(raw))


def find_duplicates(items: Iterable[Item], prefix: str) -> List[Issue]:
    items = sorted(items, key=lambda it: it.item_id)
    out: List[Issue] = []
    flagged: Set[Tuple[str, str]] = set()

    exact: Dict[str, List[Item]] = defaultdict(list)
    for it in items:
        exact[fingerprint(it.text)].append(it)
    for fp in sorted(exact):
        grp = exact[fp]
        for it in grp[1:]:
            out.append(Issue(f"{prefix}_DUPLICATE_EXACT", Severity.ERROR, it.item_id, f"identique_a:{grp[0].item_id}"))
            flagged.add((grp[0].item_id, it.item_id))

    template: Dict[Tuple[str, str], List[Item]] = defaultdict(list)
    for it in items:
        template[(it.notion_id, fingerprint(mask_numbers(it.text)))].append(it)
    for key in sorted(template):
        grp = template[key]
        for it in grp[1:]:
            pair = (grp[0].item_id, it.item_id)
            if pair in flagged or fingerprint(it.text) == fingerprint(grp[0].text):
                continue
            out.append(Issue(f"{prefix}_DUPLICATE_TEMPLATE", Severity.WARNING, it.item_id,
                             f"meme_gabarit_que:{grp[0].item_id}:notion={it.notion_id}"))
            flagged.add(pair)

    by_group: Dict[Tuple[str, str], List[Tuple[Item, Set[str]]]] = defaultdict(list)
    for it in items:
        by_group[it.group].append((it, trigrams(it.text)))
    for g in sorted(by_group):
        members = by_group[g]
        for i in range(len(members)):
            a, ta = members[i]
            for j in range(i + 1, len(members)):
                b, tb = members[j]
                small, large = sorted((len(ta), len(tb)))
                if large == 0 or small / large < SIMILARITY_THRESHOLD:
                    continue  # borne supérieure du Jaccard insuffisante
                if (a.item_id, b.item_id) in flagged or a.text == b.text:
                    continue
                score = jaccard(ta, tb)
                if score >= SIMILARITY_THRESHOLD:
                    out.append(Issue(f"{prefix}_TOO_SIMILAR", Severity.WARNING, b.item_id,
                                     f"proche_de:{a.item_id}:jaccard3={score:.2f}"))
    return out


def find_exercise_duplicates(exercises: Iterable[Exercise]) -> List[Issue]:
    return find_duplicates((exercise_item(e) for e in exercises), "EXERCISE")


def find_quiz_duplicates(quizzes: Iterable[QuizItem]) -> List[Issue]:
    return find_duplicates((quiz_item(q) for q in quizzes), "QUIZ")
