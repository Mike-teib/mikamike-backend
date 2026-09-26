"""
audit.py — Audit global de déduplication et de contenu orphelin (Phase 18).

Ne SUPPRIME rien : produit un rapport déterministe (listes triées) de :
  exact_duplicates      même énoncé + même réponse (exercices et questions de quiz)
  near_duplicates       similarité rédactionnelle ≥ seuil (Jaccard 3-grammes)
  same_notion_question  même notion + même gabarit d'énoncé (nombres masqués)
  same_answer_structure même notion + même forme de réponse (ex. « x=# »)
  orphan_content        contenu rattaché à une notion inconnue, notion sans chapitre,
                        chapitre sans notion
"""

from __future__ import annotations

import re
from collections import defaultdict
from itertools import combinations
from typing import Dict, FrozenSet, Iterable, List, Sequence, Tuple

from app.curriculum import dedup
from app.curriculum.exercices import Exercice
from app.curriculum.model import Referentiel
from app.curriculum.quiz import QuestionQuiz

SEUIL_QUASI_DOUBLON = 0.8


def _items(exercices: Sequence[Exercice], quiz: Sequence[QuestionQuiz]) -> List[Tuple[str, str, str, str]]:
    """(id, notion_id, enonce, reponse) pour exercices et questions de quiz."""
    out = [(e.id, e.notion_id, e.enonce, e.reponse_attendue) for e in exercices]
    out += [(q.id, q.notion_id, q.enonce, q.choix[q.index_correct] if 0 <= q.index_correct < len(q.choix) else "")
            for q in quiz]
    return sorted(out)


def _forme_reponse(rep: str) -> str:
    return re.sub(r"\d+(?:[.,]\d+)?", "#", dedup.normaliser(rep))


def _groupes(cles: Iterable[Tuple[str, str]]) -> List[List[str]]:
    g: Dict[str, List[str]] = defaultdict(list)
    for cle, oid in cles:
        g[cle].append(oid)
    return sorted(sorted(v) for v in g.values() if len(v) > 1)


def auditer(
    ref: Referentiel,
    exercices: Sequence[Exercice] = (),
    quiz: Sequence[QuestionQuiz] = (),
    *,
    seuil: float = SEUIL_QUASI_DOUBLON,
) -> Dict[str, object]:
    items = _items(exercices, quiz)
    notions = {n.id: n for n in ref.notions}

    exact = _groupes((dedup.empreinte_exacte(e, r), i) for i, _, e, r in items)
    meme_q = _groupes((n + "|" + dedup.empreinte_gabarit(e), i) for i, n, e, _ in items)
    meme_rep = _groupes((n + "|" + _forme_reponse(r), i) for i, n, _, r in items)

    proches: List[Tuple[str, str, float]] = []
    # Comparaison par paires restreinte à une même notion (évite O(N²) global).
    par_notion: Dict[str, List[Tuple[str, FrozenSet[str], str]]] = defaultdict(list)
    # 3-grammes et empreintes calculés UNE fois par item (R2-22 : auparavant recalculés à
    # chaque paire, soit O(k²) normalisations par notion).
    for i, n, e, _ in items:
        par_notion[n].append((i, dedup.shingles(e), dedup.empreinte_exacte(e)))
    for groupe in par_notion.values():
        for (ia, sa, ha), (ib, sb, hb) in combinations(groupe, 2):
            s = dedup.jaccard(sa, sb)
            if s >= seuil and ha != hb:
                proches.append((ia, ib, round(s, 3)))

    orphelins: List[Dict[str, str]] = []
    for i, n, _, _ in items:
        if n not in notions:
            orphelins.append({"type": "contenu_notion_inconnue", "id": i, "notion_id": n})
    for n in sorted(notions.values(), key=lambda x: x.id):
        if n.chapitre_id is None:
            orphelins.append({"type": "notion_sans_chapitre", "id": n.id})
    chapitres_utilises = {n.chapitre_id for n in ref.notions}
    for c in sorted(ref.chapitres, key=lambda x: x.id):
        if c.id not in chapitres_utilises:
            orphelins.append({"type": "chapitre_sans_notion", "id": c.id})

    return {
        "exact_duplicates": exact,
        "near_duplicates": sorted(proches),
        "same_notion_question": meme_q,
        "same_answer_structure": meme_rep,
        "orphan_content": orphelins,
        "totaux": {
            "items": len(items),
            "exact_duplicates": sum(len(g) for g in exact),
            "near_duplicates": len(proches),
            "orphan_content": len(orphelins),
        },
    }
