"""
checks — Contrôles déterministes réutilisables (aucun LLM, aucun réseau).

  verdict        : Verdict (VALID / INVALID / AMBIGUOUS / NEEDS_HUMAN_REVIEW), CheckResult
  maths          : équivalence symbolique SymPy sécurisée, formes requises
  physics        : grandeurs, unités, dimensions, chiffres significatifs, homogénéité, bornes physiques
  math_notation  : intégrité LaTeX/Unicode d'un texte, préservation source → sortie
  answers        : check_answer(ExpectedAnswer, réponse) par AnswerKind
  similarity     : normalisation, empreintes exacte / gabarit, similarité Jaccard 3-grammes
"""

from pedagogy.checks.verdict import CheckResult, Verdict  # noqa: F401
