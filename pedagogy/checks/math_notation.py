"""
math_notation.py — Intégrité de la notation mathématique (LaTeX / Unicode) dans les textes.

Adapté de app/curriculum/math_guard.py (branche session6-production-hardening), autonome.

1. `integrity_anomalies(texte)` : défauts d'un texte seul
     DOLLAR_UNBALANCED        nombre impair de délimiteurs $ (hors \\$)
     LATEX_DELIM_UNBALANCED   \\( \\) ou \\[ \\] non appariés
     BRACES_UNBALANCED        accolades {} non équilibrées (hors \\{ \\})
     MATH_BRACKETS_UNBALANCED () non équilibrées DANS un segment mathématique ($…$, \\(…\\))
     FRAC_INCOMPLETE          \\frac sans ses deux arguments {..}{..}
     SQRT_INCOMPLETE          \\sqrt sans argument
     SCRIPT_DANGLING          ^ ou _ sans argument (fin de segment, espace, accolade fermante)
     LATEX_BACKSLASH_LOST     « frac{ », « sqrt{ », « times », « cdot »… sans barre oblique
     REPLACEMENT_CHAR         caractère U+FFFD (encodage corrompu)
     PRIVATE_USE_CHAR         glyphe de zone à usage privé (police symbole mal extraite)
     CONTROL_CHAR             caractère de contrôle (hors \\t \\n \\r)
2. `preservation_anomalies(source, sortie)` : altérations introduites par une transformation
     FRACTION_CONVERTED:a/b   (ex. « 1/10 » → « 0,1 »)
     FRACTION_LOST:a/b
     LATEX_FRAC_LOST          \\frac disparu
     EXPONENT_LOST            (« x^2 » → « x2 », « 10^{-3} » → « 10-3 », « x² » → « x2 »)
     SUBSCRIPT_LOST
     PARENTHESES_CHANGED      nombre de (), [] ou {} modifié
     ROOT_LOST                √ / \\sqrt disparu
     SYMBOL_CHANGED           ≤ ≥ ≠ ≈ ∈ π ∞ … modifiés
     OPERATOR_CHANGED         = < > ≤ ≥ ≠ modifiés
     NEW_INTEGRITY:<code>     défaut d'intégrité absent de la source et présent en sortie
3. `apply_preserving_math(texte, transformation)` : applique une transformation de texte en
   masquant les expressions mathématiques par des jetons opaques, puis les restaure À
   L'IDENTIQUE (ValueError si un jeton a été altéré).
4. `latex_to_plain(texte)` : conversion LaTeX simple → écriture linéaire (pour les
   vérificateurs), sans rien évaluer.

Aucune dépendance externe ; déterministe.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from fractions import Fraction
from typing import Callable, List, Tuple

# --------------------------------------------------------------------------- #
# LaTeX → linéaire
# --------------------------------------------------------------------------- #
_LATEX_SYMBOLS = {
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\pi": "π", r"\leq": "≤", r"\le": "≤",
    r"\geq": "≥", r"\ge": "≥", r"\neq": "≠", r"\approx": "≈", r"\infty": "∞", r"\in": "∈",
    r"\pm": "±", r"\to": "→", r"\rightarrow": "→", r"\Rightarrow": "⇒",
}


def latex_to_plain(text: str) -> str:
    t = text or ""
    if "\\" not in t and "$" not in t and "{" not in t:
        return t
    t = t.replace("\\$", "\x00DOLLAR\x00")
    t = re.sub(r"\\[()\[\]]", " ", t).replace("$", "")
    t = t.replace("\x00DOLLAR\x00", "$")
    t = re.sub(r"\\(?:left|right|displaystyle)\b", "", t)
    t = re.sub(r"\\[,;:!]|~", " ", t)
    t = re.sub(r"\\(?:text|mathrm|mathit|mathbf|operatorname)\s*\{([^{}]*)\}", r"\1", t)
    for _ in range(10):
        new = re.sub(r"\\[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"((\1)/(\2))", t)
        new = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"sqrt(\1)", new)
        new = re.sub(r"\^\s*\{([^{}]*)\}", r"^(\1)", new)
        new = re.sub(r"_\s*\{([^{}]*)\}", r"_\1", new)
        if new == t:
            break
        t = new
    for k in sorted(_LATEX_SYMBOLS, key=len, reverse=True):
        t = re.sub(re.escape(k) + r"(?![A-Za-z])", _LATEX_SYMBOLS[k], t)
    t = re.sub(r"\\(ln|log|exp|sin|cos|tan)(?![A-Za-z])", r"\1", t)
    return t.replace("{", "(").replace("}", ")")


# --------------------------------------------------------------------------- #
# Intégrité d'un texte seul
# --------------------------------------------------------------------------- #
_MATH_SEGMENT = re.compile(r"\$\$(.+?)\$\$|\$(.+?)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]", re.S)
_LOST_BACKSLASH = re.compile(
    r"(?<![\\A-Za-z])(?:d?frac|sqrt)\s*\{|(?<![\\A-Za-z])(?:times|cdot|leq|geq|neq|infty)(?![A-Za-zÀ-ÿ])"
)


def _math_segments(text: str) -> List[str]:
    return [next(g for g in m.groups() if g is not None) for m in _MATH_SEGMENT.finditer(text)]


def _balanced(s: str, open_c: str, close_c: str) -> bool:
    depth = 0
    for c in s:
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _read_arg(t: str, i: int) -> int:
    """Lit un argument LaTeX à partir de i : {groupe équilibré}, \\commande ou caractère.
    Renvoie l'index qui suit l'argument, ou -1 si absent/incomplet."""
    while i < len(t) and t[i] == " ":
        i += 1
    if i >= len(t):
        return -1
    c = t[i]
    if c == "{":
        depth = 0
        for j in range(i, len(t)):
            if t[j] == "{" and (j == 0 or t[j - 1] != "\\"):
                depth += 1
            elif t[j] == "}" and (j == 0 or t[j - 1] != "\\"):
                depth -= 1
                if depth == 0:
                    return j + 1
        return -1
    if c == "\\":
        m = re.match(r"\\[A-Za-z]+", t[i:])
        return i + m.end() if m else -1
    if c.isalnum():
        return i + 1
    return -1


def integrity_anomalies(text: str) -> List[str]:
    t = text or ""
    out: List[str] = []
    unescaped = re.sub(r"\\\$", "", t)
    if unescaped.count("$") % 2:
        out.append("DOLLAR_UNBALANCED")
    if t.count("\\(") != t.count("\\)") or t.count("\\[") != t.count("\\]"):
        out.append("LATEX_DELIM_UNBALANCED")
    if not _balanced(re.sub(r"\\[{}]", "", t), "{", "}"):
        out.append("BRACES_UNBALANCED")
    for seg in _math_segments(t):
        s = re.sub(r"\\[{}()\[\]]|\\left.|\\right.", "", seg)
        # Seules les parenthèses : ]a ; b[ est une notation d'intervalle française valide.
        if not _balanced(s, "(", ")"):
            out.append("MATH_BRACKETS_UNBALANCED")
            break
    for m in re.finditer(r"\\[dt]?frac(?![A-Za-z])", t):
        i = _read_arg(t, m.end())
        if i < 0 or _read_arg(t, i) < 0:
            out.append("FRAC_INCOMPLETE")
            break
    for m in re.finditer(r"\\sqrt(?![A-Za-z])", t):
        j = m.end()
        while j < len(t) and t[j] == " ":
            j += 1
        if j < len(t) and t[j] == "[":  # \sqrt[n]{x}
            k = t.find("]", j)
            j = k + 1 if k > 0 else len(t)
        if _read_arg(t, j) < 0:
            out.append("SQRT_INCOMPLETE")
            break
    segs = _math_segments(t)
    plain = _MATH_SEGMENT.sub(" ", t)
    if any(re.search(r"[\^_]\s*(?:$|[})\]=,;])", s) for s in segs) or \
            re.search(r"\^(?=\s*(?:$|[.,;:!?)\]}]|\s[A-Za-zÀ-ÿ]{2,}))", plain):
        out.append("SCRIPT_DANGLING")
    if _LOST_BACKSLASH.search(t):
        out.append("LATEX_BACKSLASH_LOST")
    if "\ufffd" in t:
        out.append("REPLACEMENT_CHAR")
    if any(unicodedata.category(c) == "Co" for c in t):
        out.append("PRIVATE_USE_CHAR")
    if any(unicodedata.category(c) == "Cc" and c not in "\t\n\r" for c in t):
        out.append("CONTROL_CHAR")
    return out


def is_notation_ok(text: str) -> bool:
    return not integrity_anomalies(text)


# --------------------------------------------------------------------------- #
# Préservation source → sortie
# --------------------------------------------------------------------------- #
_FRACTION = re.compile(r"(?<![\w.,])(\d+)\s*/\s*(\d+)(?![\w.,])")
_EXPONENT_CARET = re.compile(r"\^\s*(?:\{[^{}]*\}|\(?\s*[-−]?\s*[\w.]+\s*\)?)")
_EXPONENT_UNICODE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿ]+")
_SUBSCRIPT = re.compile(r"_\s*(?:\{[^{}]*\}|\w)|[₀₁₂₃₄₅₆₇₈₉]")
_ROOT = re.compile(r"√\s*(\([^)]*\)|[\w.]+)|\\sqrt")
_SYMBOLS = "≤≥≠≈∈∉⊂⊄∪∩∞π∑∏∫→↦±×÷∀∃ℕℤℚℝℂ∅°"
_OPERATORS = "=<>≤≥≠"


def _fractions(t: str) -> Counter:
    return Counter(f"{a}/{b}" for a, b in _FRACTION.findall(t))


def _count(t: str, chars: str) -> Counter:
    return Counter(c for c in t if c in chars)


def _decimal_forms(fr: Fraction) -> List[str]:
    val = fr.numerator / fr.denominator
    s = f"{val:.10f}".rstrip("0").rstrip(".")
    return [s, s.replace(".", ",")]


def _exponent_count(t: str) -> int:
    return len(_EXPONENT_CARET.findall(t)) + sum(len(x) for x in _EXPONENT_UNICODE.findall(t))


def preservation_anomalies(source: str, output: str) -> List[str]:
    source, output = source or "", output or ""
    out: List[str] = []
    f_src, f_out = _fractions(source), _fractions(output)
    for frac, n in sorted(f_src.items()):
        if f_out[frac] < n:
            a, b = (int(x) for x in frac.split("/"))
            converted = b != 0 and any(
                re.search(r"(?<![\d.,])" + re.escape(d) + r"(?![\d])", output) for d in _decimal_forms(Fraction(a, b))
            )
            out.append(f"FRACTION_CONVERTED:{frac}" if converted else f"FRACTION_LOST:{frac}")
    if len(re.findall(r"\\[dt]?frac", output)) < len(re.findall(r"\\[dt]?frac", source)):
        out.append("LATEX_FRAC_LOST")
    if _exponent_count(output) < _exponent_count(source):
        out.append("EXPONENT_LOST")
    if len(_SUBSCRIPT.findall(output)) < len(_SUBSCRIPT.findall(source)):
        out.append("SUBSCRIPT_LOST")
    for o, c in ("()", "[]", "{}"):
        if (source.count(o), source.count(c)) != (output.count(o), output.count(c)):
            out.append("PARENTHESES_CHANGED")
            break
    if Counter(_ROOT.findall(source)) - Counter(_ROOT.findall(output)) or \
            len(_ROOT.findall(output)) < len(_ROOT.findall(source)):
        out.append("ROOT_LOST")
    if _count(source, _SYMBOLS) != _count(output, _SYMBOLS):
        out.append("SYMBOL_CHANGED")
    if _count(source, _OPERATORS) != _count(output, _OPERATORS):
        out.append("OPERATOR_CHANGED")
    before = set(integrity_anomalies(source))
    for code in integrity_anomalies(output):
        if code not in before:
            out.append(f"NEW_INTEGRITY:{code}")
    return out


# --------------------------------------------------------------------------- #
# Transformation protégée
# --------------------------------------------------------------------------- #
_EXPRESSION = re.compile(
    r"\$[^$]+\$"
    r"|(?:[\w.,]*[\d)][\w.,]*|[a-zA-Z])?"
    r"(?:\s*(?:[=<>≤≥≠+\-−×÷*/^√()]|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺ⁿ])+\s*[\w.,()]*)+"
)
_TOKEN = "\u2063MATH{}\u2063"  # séparateur invisible


def _is_math(fragment: str) -> bool:
    return fragment.startswith("$") or bool(re.search(
        r"[\d)]\s*[/^]|[\^√⁰¹²³⁴⁵⁶⁷⁸⁹⁻]|[=<>≤≥≠]|\d\s*[+\-−×÷*]\s*\w|\w\s*[+\-−×÷*]\s*\d", fragment))


def protect(text: str) -> Tuple[str, List[str]]:
    expressions: List[str] = []

    def _sub(m: re.Match) -> str:
        frag = m.group(0)
        if not _is_math(frag):
            return frag
        expressions.append(frag)
        return _TOKEN.format(len(expressions) - 1)

    return _EXPRESSION.sub(_sub, text), expressions


def restore(text: str, expressions: List[str]) -> str:
    for i, expr in enumerate(expressions):
        token = _TOKEN.format(i)
        if text.count(token) != 1:
            raise ValueError(f"jeton_mathematique_{i}_altere")
        text = text.replace(token, expr)
    return text


def apply_preserving_math(text: str, transformation: Callable[[str], str]) -> str:
    masked, expressions = protect(text)
    return restore(transformation(masked), expressions)
