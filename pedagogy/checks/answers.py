"""
answers.py — Vérification d'une réponse d'élève contre une ExpectedAnswer (déterministe).

  check_answer(expected, student) -> Verdict
  check_answer_detailed(expected, student) -> CheckResult (verdict + raisons)
  render_expected(expected) -> str   (écriture canonique de la réponse attendue, pour l'auto-contrôle)
  answer_texts(expected) -> List[str] (formes textuelles de la réponse, pour détecter les fuites)

Répartition par AnswerKind :
  MATH_EXPR  : équivalence symbolique SymPy (gardes de sécurité) + required_form ;
  QUANTITY   : valeur + unité (dimension, tolérance relative, chiffres significatifs,
               required_form ∈ {notation_scientifique, unite_imposee}) ;
  EXACT_TEXT : égalité après normalisation (casse, espaces, apostrophes, ponctuation finale,
               article initial « le/la/les/l'/un/une/des/du ») ;
               value peut être une liste de formes acceptées ;
  CHOICE     : index (0-based) ou lettre (A, B…) ; plusieurs index ⇒ ensemble exact ;
  BOOLEAN    : vrai/faux, true/false, oui/non ;
  ORDERING   : suite ordonnée (liste JSON, ou « a ; b ; c », « a < b < c », « a > b > c », « a → b ») ;
  MATCHING   : paires gauche → droite (objet JSON, ou « a → 1 ; b → 2 », « a : 1 », « a = 1 ») ;
  RUBRIC     : toujours NEEDS_HUMAN_REVIEW (réponse rédigée, jamais auto-validée).
Jamais VALID par défaut : toute attente malformée ⇒ NEEDS_HUMAN_REVIEW.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pedagogy.checks import maths, physics
from pedagogy.checks.verdict import CheckResult, Verdict, invalid, review, valid
from pedagogy.models import AnswerKind, ExpectedAnswer

MAX_STUDENT_LENGTH = 2000
_QUANTITY_FORMS = frozenset({"notation_scientifique", "unite_imposee"})


# --------------------------------------------------------------------------- #
# Normalisation texte
# --------------------------------------------------------------------------- #
def normalize_answer_text(text: str) -> str:
    t = unicodedata.normalize("NFC", str(text or "")).casefold()
    for a, b in (("’", "'"), ("‘", "'"), ("ʼ", "'"), ("«", ""), ("»", ""), (" ", " "), (" ", " "),
                 ("−", "-"), ("–", "-"), ("—", "-"), ("œ", "oe")):
        t = t.replace(a, b)
    t = " ".join(t.split())
    t = re.sub(r"\s*'\s*", "'", t)
    t = re.sub(r"(\d),(\d)", r"\1.\2", t)
    return t.strip(" .;:,!?\"'")


_ARTICLE = re.compile(r"^(?:le|la|les|l'|un|une|des|du|de la|de l'|d')\s*")


def normalize_short_text(text: str) -> str:
    """Texte court (EXACT_TEXT) : normalisation + article initial retiré (« le noyau » ≡ « noyau »)."""
    t = normalize_answer_text(text)
    stripped = _ARTICLE.sub("", t, count=1).strip()
    return stripped or t


# --------------------------------------------------------------------------- #
# Formes structurées
# --------------------------------------------------------------------------- #
_TRUE = {"vrai", "v", "true", "oui", "o", "yes", "1", "juste", "exact", "correct"}
_FALSE = {"faux", "f", "false", "non", "n", "no", "0", "incorrect", "inexact"}


def parse_boolean(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        t = normalize_answer_text(value)
        if t in _TRUE:
            return True
        if t in _FALSE:
            return False
    return None


def parse_choice(value: Any) -> Optional[Tuple[int, ...]]:
    """int, liste d'int, « 2 », « 1, 3 », « B », « A et C » → tuple trié d'index (0-based)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return (value,) if value >= 0 else None
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                return None
            out.append(v)
        return tuple(sorted(set(out))) if out else None
    if isinstance(value, str):
        t = value.strip()
        if not t or len(t) > 100:
            return None
        parts = [p for p in re.split(r"\s*(?:,|;|\bet\b|\band\b|\s)\s*", t) if p]
        out = []
        for p in parts:
            p = p.strip("().")
            if re.fullmatch(r"\d{1,2}", p):
                out.append(int(p))
            elif re.fullmatch(r"[A-Za-z]", p):
                out.append(ord(p.upper()) - ord("A"))
            else:
                return None
        return tuple(sorted(set(out))) if out else None
    return None


def parse_ordering(value: Any) -> Optional[List[str]]:
    if isinstance(value, (list, tuple)):
        items = [normalize_answer_text(v) for v in value]
        return items if items and all(items) else None
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_STUDENT_LENGTH:
        return None
    t = value.strip()
    if t.startswith("["):
        try:
            data = json.loads(t)
        except ValueError:
            return None
        return parse_ordering(data) if isinstance(data, list) else None
    for sep in (r"\s*;\s*", r"\s*(?:→|->|⟶)\s*", r"\s*<\s*", r"\s*>\s*", r"\s*\|\s*", r"\s*\n\s*", r",\s+"):
        if re.search(sep, t):
            items = [normalize_answer_text(x) for x in re.split(sep, t)]
            return items if all(items) else None
    return None


def parse_matching(value: Any) -> Optional[Dict[str, str]]:
    if isinstance(value, dict):
        out = {normalize_answer_text(k): normalize_answer_text(v) for k, v in value.items()}
        return out if out and all(out) and all(out.values()) else None
    if isinstance(value, (list, tuple)):
        out = {}
        for pair in value:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                return None
            out[normalize_answer_text(pair[0])] = normalize_answer_text(pair[1])
        return out if out and all(out) and all(out.values()) else None
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_STUDENT_LENGTH:
        return None
    t = value.strip()
    if t.startswith("{") or t.startswith("["):
        try:
            data = json.loads(t)
        except ValueError:
            return None
        return parse_matching(data)
    out = {}
    for part in [p for p in re.split(r"\s*[;\n]\s*", t) if p.strip()]:
        m = re.fullmatch(r"(.+?)\s*(?:→|->|⟶|:|=)\s*(.+)", part.strip())
        if not m:
            return None
        k, v = normalize_answer_text(m.group(1)), normalize_answer_text(m.group(2))
        if not k or not v or k in out:
            return None
        out[k] = v
    return out or None


def _item_equal(a: str, b: str) -> bool:
    return normalize_answer_text(a) == normalize_answer_text(b)


# --------------------------------------------------------------------------- #
# Grandeurs
# --------------------------------------------------------------------------- #
def quantity_expected_text(expected: ExpectedAnswer) -> str:
    v = expected.value
    if isinstance(v, bool) or v is None:
        raise physics.QuantityError("valeur_attendue_invalide")
    if isinstance(v, (int, float)):
        num = maths.value_to_text(v).replace(".", ",")
    elif isinstance(v, str):
        num = v.strip()
    else:
        raise physics.QuantityError("valeur_attendue_invalide")
    return f"{num} {expected.unit}".strip() if expected.unit else num


def _check_quantity(expected: ExpectedAnswer, student: str) -> CheckResult:
    if expected.required_form and expected.required_form not in _QUANTITY_FORMS:
        return review("forme_inconnue")
    try:
        exp_txt = quantity_expected_text(expected)
    except (physics.QuantityError, maths.MathInputRejected) as exc:
        return review(f"attendue_{exc}")
    tol = 0.01 if expected.tolerance_relative is None else expected.tolerance_relative
    return physics.check_quantity(
        exp_txt, student,
        unit_required=True,
        tolerance_relative=tol,
        required_sig_figs=expected.significant_figures,
        scientific_notation=expected.required_form == "notation_scientifique",
        unit_imposed=expected.required_form == "unite_imposee",
    )


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #
def check_answer_detailed(expected: ExpectedAnswer, student: Any) -> CheckResult:
    kind = expected.kind
    if kind == AnswerKind.RUBRIC:
        return review("reponse_redigee_revue_humaine")
    if student is None:
        return invalid("reponse_vide")
    if not isinstance(student, str):
        student = json.dumps(student, ensure_ascii=False) if isinstance(student, (list, dict)) else str(student)
    if len(student) > MAX_STUDENT_LENGTH:
        return review("reponse_trop_longue")
    if not student.strip():
        return invalid("reponse_vide")
    try:
        if kind == AnswerKind.MATH_EXPR:
            return maths.check_math_answer(expected.value, student, expected.required_form)
        if kind == AnswerKind.QUANTITY:
            return _check_quantity(expected, student)
        if kind == AnswerKind.EXACT_TEXT:
            accepted = expected.value if isinstance(expected.value, (list, tuple)) else [expected.value]
            accepted = [a for a in accepted if isinstance(a, (str, int, float)) and not isinstance(a, bool)]
            norm = [normalize_short_text(str(a)) for a in accepted]
            if not norm or not all(norm):
                return review("attendue_vide")
            return valid("texte_identique") if normalize_short_text(student) in norm else invalid("texte_different")
        if kind == AnswerKind.CHOICE:
            exp = parse_choice(expected.value)
            if exp is None:
                return review("attendue_choix_invalide")
            got = parse_choice(student)
            if got is None:
                return invalid("choix_illisible")
            return valid("choix_correct") if got == exp else invalid("choix_incorrect")
        if kind == AnswerKind.BOOLEAN:
            exp_b = parse_boolean(expected.value)
            if exp_b is None:
                return review("attendue_booleen_invalide")
            got_b = parse_boolean(student)
            if got_b is None:
                return invalid("booleen_illisible")
            return valid("booleen_correct") if got_b == exp_b else invalid("booleen_incorrect")
        if kind == AnswerKind.ORDERING:
            exp_o = parse_ordering(expected.value)
            if exp_o is None or len(exp_o) < 2:
                return review("attendue_ordre_invalide")
            got_o = parse_ordering(student)
            if got_o is None:
                return invalid("ordre_illisible")
            return valid("ordre_correct") if got_o == exp_o else invalid("ordre_incorrect")
        if kind == AnswerKind.MATCHING:
            exp_m = parse_matching(expected.value)
            if exp_m is None:
                return review("attendue_association_invalide")
            got_m = parse_matching(student)
            if got_m is None:
                return invalid("association_illisible")
            return valid("association_correcte") if got_m == exp_m else invalid("association_incorrecte")
    except (RecursionError, MemoryError, OverflowError):  # garde ultime
        return review("calcul_trop_lourd")
    return review("type_de_reponse_non_supporte")


def check_answer(expected: ExpectedAnswer, student: Any) -> Verdict:
    return check_answer_detailed(expected, student).verdict


# --------------------------------------------------------------------------- #
# Rendu canonique de l'attendu
# --------------------------------------------------------------------------- #
def render_expected(expected: ExpectedAnswer) -> str:
    """Écriture de la réponse attendue telle qu'un élève parfait la donnerait."""
    v, kind = expected.value, expected.kind
    if kind == AnswerKind.MATH_EXPR:
        try:
            return maths.value_to_text(v)
        except maths.MathInputRejected:
            return str(v)
    if kind == AnswerKind.QUANTITY:
        numeric = isinstance(v, (int, float)) and not isinstance(v, bool)
        sci = expected.required_form == "notation_scientifique"
        if numeric and (expected.significant_figures or sci):
            n = expected.significant_figures
            if not n:
                digits = re.sub(r"\D", "", maths.value_to_text(v)).strip("0")
                n = max(len(digits), 1)
            num = physics.format_significant(float(v), n)
            if sci and "×" not in num:
                mant, _, exp = f"{float(v):.{n - 1}e}".partition("e")
                num = f"{mant.replace('.', ',')} × 10^{int(exp)}"
            return f"{num} {expected.unit}".strip() if expected.unit else num
        try:
            return quantity_expected_text(expected)
        except (physics.QuantityError, maths.MathInputRejected):
            return str(v)
    if kind == AnswerKind.EXACT_TEXT:
        return str(v[0]) if isinstance(v, (list, tuple)) and v else str(v)
    if kind == AnswerKind.CHOICE:
        c = parse_choice(v)
        return ", ".join(str(i) for i in c) if c else str(v)
    if kind == AnswerKind.BOOLEAN:
        b = parse_boolean(v)
        return ("vrai" if b else "faux") if b is not None else str(v)
    if kind == AnswerKind.ORDERING:
        return json.dumps(list(v), ensure_ascii=False) if isinstance(v, (list, tuple)) else str(v)
    if kind == AnswerKind.MATCHING:
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, (list, tuple)):
            return json.dumps([list(p) for p in v], ensure_ascii=False)
        return str(v)
    return str(v)


def answer_texts(expected: ExpectedAnswer) -> List[str]:
    """Formes textuelles de la réponse (fuites dans énoncé/indices). Vide si non pertinent."""
    kind, v = expected.kind, expected.value
    if kind == AnswerKind.MATH_EXPR:
        try:
            t = maths.value_to_text(v)
        except maths.MathInputRejected:
            return []
        outs = []
        for sol in re.split(r"\s+ou\s+|;", t):
            sol = sol.split("=")[-1].strip()
            if sol:
                outs.append(sol)
        return outs
    if kind == AnswerKind.QUANTITY:
        if isinstance(v, bool) or v is None:
            return []
        if isinstance(v, (int, float)):
            return [maths.value_to_text(v)]
        try:
            return [physics.parse_quantity(str(v)).mantissa] if not physics.parse_quantity(str(v)).scientific \
                else [str(v).strip()]
        except physics.QuantityError:
            return [str(v).strip()]
    if kind == AnswerKind.EXACT_TEXT:
        vals = v if isinstance(v, (list, tuple)) else [v]
        return [str(x).strip() for x in vals if str(x).strip()]
    return []


def _number_variants(s: str) -> List[str]:
    out = {s}
    if re.fullmatch(r"[-+]?\d+[.,]\d+", s):
        out |= {s.replace(",", "."), s.replace(".", ",")}
    return sorted(out)


def text_contains_answer(text: str, answer: str, *, min_length: int = 3) -> bool:
    """Recherche « frontière de jeton » : « 0,7 » n'est PAS trouvé dans « 0,75 » ni « 10,7 »."""
    a = (answer or "").strip()
    if len(re.sub(r"[\s+\-−]", "", a)) < min_length or not text:
        return False
    hay = unicodedata.normalize("NFC", text).casefold().replace("−", "-")
    for variant in _number_variants(unicodedata.normalize("NFC", a).casefold().replace("−", "-")):
        pat = r"(?<![\w.,])(?<![\d][.,])" + re.escape(variant) + r"(?![\w])(?![.,]\d)"
        if re.search(pat, hay):
            return True
    return False
