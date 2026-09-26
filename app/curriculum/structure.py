"""
structure.py — Validateur structurel d'un Referentiel (chapitres / notions).

Contrôles (codes stables, triés, déterministes) :
  ID_DUPLIQUE                 même identifiant pour deux objets
  PROGRAMME_SANS_SOURCE       programme dont la source n'est pas enregistrée
  PROGRAMME_INCOHERENT        matière inexistante à ce niveau (ex. SVT en CM1)
  PROGRAMMES_CHEVAUCHANTS     deux versions en vigueur la même rentrée (matière, niveau)
  DOMAINE_SANS_PROGRAMME / THEME_SANS_PROGRAMME / CHAPITRE_SANS_PROGRAMME
  MAUVAIS_DOMAINE             thème rattaché à un domaine d'un autre programme / inconnu
  MAUVAIS_THEME               chapitre rattaché à un thème inconnu ou d'un autre programme
  MAUVAIS_NIVEAU              chapitre/notion d'un niveau non couvert par son programme,
                              ou notion d'un niveau ≠ celui de son chapitre
  MAUVAISE_MATIERE            notion de matière ≠ matière du programme
  NOTION_SANS_CHAPITRE        notion non rattachée
  NOTION_CHAPITRE_INCONNU     chapitre référencé inexistant
  NOTION_PROGRAMME_DIFFERENT  notion et chapitre de programmes différents
  PREREQUIS_INCONNU           prérequis inexistant
  PREREQUIS_CYCLE             cycle dans le graphe de prérequis
  VERSION_MELANGEE            prérequis pris dans une version de programme non en
                              vigueur en même temps que celle de la notion (même matière)
  DOUBLON_NOTION              deux notions au texte identique dans un même chapitre
  TEXTE_SUSPECT               texte non utilisable (tronqué, colonnes, formule…)
  PLURIDISCIPLINAIRE_INVALIDE disciplines mobilisées déclarées hors Enseignement scientifique

Rien n'est corrigé automatiquement : le validateur ne fait que signaler.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, NamedTuple, Optional, Set

from app.curriculum.ids import normaliser_pour_empreinte
from app.curriculum.model import (
    NIVEAUX_PAR_MATIERE,
    STATUTS_TEXTE_UTILISABLES,
    IndexReferentiel,
    Matiere,
    Programme,
    Referentiel,
)
from app.curriculum.text_quality import analyser_texte


class Anomalie(NamedTuple):
    code: str
    objet_id: str
    detail: str = ""


def _periodes_se_chevauchent(a: Programme, b: Programme) -> bool:
    fin_a = a.rentree_fin if a.rentree_fin is not None else 10**6
    fin_b = b.rentree_fin if b.rentree_fin is not None else 10**6
    return a.rentree_debut <= fin_b and b.rentree_debut <= fin_a


def valider_referentiel(ref: Referentiel, *, analyser_textes: bool = True) -> List[Anomalie]:
    idx = IndexReferentiel(ref)
    out: List[Anomalie] = []

    # --- identifiants uniques (tous types confondus) --------------------------
    tous = [o.id for groupe in (ref.sources, ref.programmes, ref.domaines, ref.themes,
                                ref.chapitres, ref.notions) for o in groupe]
    for oid, n in Counter(tous).items():
        if n > 1:
            out.append(Anomalie("ID_DUPLIQUE", oid, f"{n} occurrences"))

    # --- programmes -------------------------------------------------------------
    for p in ref.programmes:
        if p.source_id not in idx.sources:
            out.append(Anomalie("PROGRAMME_SANS_SOURCE", p.id, p.source_id))
        hors = [n.value for n in p.niveaux if n not in NIVEAUX_PAR_MATIERE[p.matiere]]
        if hors:
            out.append(Anomalie("PROGRAMME_INCOHERENT", p.id, f"{p.matiere.value} absente en {','.join(hors)}"))
    progs = list(ref.programmes)
    for i, a in enumerate(progs):
        for b in progs[i + 1:]:
            if a.matiere == b.matiere and set(a.niveaux) & set(b.niveaux) and _periodes_se_chevauchent(a, b):
                out.append(Anomalie("PROGRAMMES_CHEVAUCHANTS", a.id, b.id))

    # --- domaines / thèmes / chapitres ------------------------------------------
    for d in ref.domaines:
        if d.programme_id not in idx.programmes:
            out.append(Anomalie("DOMAINE_SANS_PROGRAMME", d.id, d.programme_id))
    for t in ref.themes:
        if t.programme_id not in idx.programmes:
            out.append(Anomalie("THEME_SANS_PROGRAMME", t.id, t.programme_id))
        dom = idx.domaines.get(t.domaine_id)
        if dom is None or dom.programme_id != t.programme_id:
            out.append(Anomalie("MAUVAIS_DOMAINE", t.id, t.domaine_id))
    for c in ref.chapitres:
        prog = idx.programmes.get(c.programme_id)
        if prog is None:
            out.append(Anomalie("CHAPITRE_SANS_PROGRAMME", c.id, c.programme_id))
        elif c.niveau not in prog.niveaux:
            out.append(Anomalie("MAUVAIS_NIVEAU", c.id, f"{c.niveau.value} hors {prog.id}"))
        th = idx.themes.get(c.theme_id)
        if th is None or th.programme_id != c.programme_id:
            out.append(Anomalie("MAUVAIS_THEME", c.id, c.theme_id))

    # --- notions -----------------------------------------------------------------
    textes_par_chapitre: Dict[str, Counter] = defaultdict(Counter)
    for n in ref.notions:
        prog = idx.programmes.get(n.programme_id)
        if prog is not None:
            if n.matiere != prog.matiere:
                out.append(Anomalie("MAUVAISE_MATIERE", n.id, f"{n.matiere.value} ≠ {prog.matiere.value}"))
            if n.niveau not in prog.niveaux:
                out.append(Anomalie("MAUVAIS_NIVEAU", n.id, f"{n.niveau.value} hors {prog.id}"))
        if n.chapitre_id is None:
            out.append(Anomalie("NOTION_SANS_CHAPITRE", n.id))
        else:
            chap = idx.chapitres.get(n.chapitre_id)
            if chap is None:
                out.append(Anomalie("NOTION_CHAPITRE_INCONNU", n.id, n.chapitre_id))
            else:
                if chap.programme_id != n.programme_id:
                    out.append(Anomalie("NOTION_PROGRAMME_DIFFERENT", n.id, chap.programme_id))
                if chap.niveau != n.niveau:
                    out.append(Anomalie("MAUVAIS_NIVEAU", n.id, f"notion {n.niveau.value} / chapitre {chap.niveau.value}"))
            textes_par_chapitre[n.chapitre_id][normaliser_pour_empreinte(n.texte).casefold()] += 1

        if n.disciplines_mobilisees and n.matiere != Matiere.ENSEIGNEMENT_SCIENTIFIQUE:
            out.append(Anomalie("PLURIDISCIPLINAIRE_INVALIDE", n.id, n.matiere.value))
        # Lot 17 (S4) : provenance des disciplines. ES : disciplines déclarées = disciplines
        # indiquées par la source (relevé obligatoire). Hors ES : une source pluridisciplinaire
        # ne peut pas être forcée dans une seule matière.
        indiquees = n.preuve.disciplines_indiquees if n.preuve else None
        if n.matiere == Matiere.ENSEIGNEMENT_SCIENTIFIQUE or indiquees is not None:
            from app.curriculum.verifiers.enseignement_scientifique import verifier_notion_es

            v = verifier_notion_es(n, indiquees)
            if v.verdict.value != "VALID":
                out.append(Anomalie("DISCIPLINES_NON_PROUVEES", n.id, ",".join(v.raisons)))

        if analyser_textes:
            rap = analyser_texte(n.texte, extrait_source=n.preuve.extrait if n.preuve else None)
            if rap.statut not in STATUTS_TEXTE_UTILISABLES and rap.statut.value != "SOURCE_NOT_EVIDENCED":
                out.append(Anomalie("TEXTE_SUSPECT", n.id, rap.statut.value))

        for pre in n.prerequis:
            cible = idx.notions.get(pre)
            if cible is None:
                out.append(Anomalie("PREREQUIS_INCONNU", n.id, pre))
                continue
            p_n, p_c = idx.programmes.get(n.programme_id), idx.programmes.get(cible.programme_id)
            if p_n and p_c and p_n.id != p_c.id and p_n.matiere == p_c.matiere \
                    and set(p_n.niveaux) & set(p_c.niveaux) and not _periodes_se_chevauchent(p_n, p_c):
                # Même matière & niveau, versions jamais en vigueur ensemble = ancienne version mélangée.
                out.append(Anomalie("VERSION_MELANGEE", n.id, f"{pre} ({p_c.id})"))

    for chap_id, compteur in textes_par_chapitre.items():
        for texte, k in compteur.items():
            if k > 1:
                out.append(Anomalie("DOUBLON_NOTION", chap_id, f"{k}× « {texte[:60]} »"))

    out.extend(_cycles_prerequis(idx))
    return sorted(set(out))


def _cycles_prerequis(idx: IndexReferentiel) -> List[Anomalie]:
    """DFS itératif (pas de limite de récursion sur les longues chaînes de prérequis)."""
    BLANC, GRIS, NOIR = 0, 1, 2
    couleur: Dict[str, int] = {nid: BLANC for nid in idx.notions}
    trouves: Set[str] = set()

    for racine in sorted(idx.notions):
        if couleur[racine] != BLANC:
            continue
        pile = [(racine, iter(idx.notions[racine].prerequis))]
        couleur[racine] = GRIS
        while pile:
            nid, enfants = pile[-1]
            suivant = next(enfants, None)
            if suivant is None:
                couleur[nid] = NOIR
                pile.pop()
            elif suivant in couleur:
                if couleur[suivant] == GRIS:
                    trouves.add(suivant)
                elif couleur[suivant] == BLANC:
                    couleur[suivant] = GRIS
                    pile.append((suivant, iter(idx.notions[suivant].prerequis)))
    return [Anomalie("PREREQUIS_CYCLE", nid) for nid in sorted(trouves)]


def compter_notions(ref: Referentiel, *, inclure_optionnelles: bool = False,
                    programme_id: Optional[str] = None) -> int:
    """Décompte officiel : les notions OPTIONNELLES ne sont pas comptées par défaut."""
    return sum(
        1 for n in ref.notions
        if (inclure_optionnelles or not n.optionnelle)
        and (programme_id is None or n.programme_id == programme_id)
    )
