"""
integrite.py — Contrôles d'intégrité CROISÉS d'un lot de contenu (référentiel + exercices + quiz).

Complète `structure.valider_referentiel` (cohérence interne du référentiel) par les recoupements
entre objets et avec les documents sources :

  notion.programme / notion.chapitre / chapitre.programme / matière / niveau  (structure + contenus)
  rentrée             PROGRAMME_HORS_RENTREE        programme de la notion non en vigueur à la rentrée visée
  source              PREUVE_SOURCE_AUTRE_PROGRAMME preuve tirée d'une autre source que celle du programme
                      SOURCE_DOCUMENT_ABSENT        document source (PDF…) non fourni / empreinte inconnue
  preuve / hash       HASH_EXTRAIT_INCOHERENT       sha256 de l'extrait ≠ extrait
  texte               TEXTE_DECLARE_INCOHERENT      statut de texte déclaré utilisable, recalcul non utilisable
  contenu exercice    EXERCICE_INVALIDE             toute raison de `valider_exercice` (notion inconnue ou non
                                                    prouvée, matière/niveau/programme/chapitre, source, fuite…)
  quiz                QUIZ_INVALIDE                 toute raison de `valider_question`
  identifiants        CONTENU_ID_DUPLIQUE
  plans de guidage    PLAN_INVALIDE / PLAN_SANS_EXERCICE

Règle : **aucune génération si l'intégrité n'est pas démontrée**. `RapportIntegrite.generables`
ne contient que les notions dont l'autorisation de génération passe ET qui ne sont touchées par
AUCUNE anomalie (ni elles, ni leur chapitre, ni leur programme). Si le rapport contient une
anomalie globale (source, doublon d'identifiant…), `generables` est vide.
"""

from __future__ import annotations

from collections import Counter
from typing import Dict, FrozenSet, Iterable, List, Mapping, NamedTuple, Optional, Sequence

from app.curriculum.exercices import BanqueExercices, Exercice, valider_exercice
from app.curriculum.model import STATUTS_TEXTE_UTILISABLES, Referentiel
from app.curriculum.provenance import autorisation_generation
from app.curriculum.quiz import QuestionQuiz, valider_question
from app.curriculum.structure import Anomalie, valider_referentiel
from app.curriculum.text_quality import analyser_texte

# Anomalies qui invalident TOUT le lot (pas seulement un objet).
CODES_GLOBAUX = frozenset({"ID_DUPLIQUE", "CONTENU_ID_DUPLIQUE", "SOURCE_DOCUMENT_ABSENT",
                           "PROGRAMME_SANS_SOURCE", "PROGRAMMES_CHEVAUCHANTS", "PROGRAMME_INCOHERENT"})


class RapportIntegrite(NamedTuple):
    anomalies: List[Anomalie]
    generables: FrozenSet[str]

    @property
    def demontree(self) -> bool:
        return not self.anomalies


def verifier_integrite(
    ref: Referentiel,
    exercices: Sequence[Exercice] = (),
    quiz: Sequence[QuestionQuiz] = (),
    *,
    plans: Optional[Mapping[str, object]] = None,
    documents_sha256: Optional[Iterable[str]] = None,
    rentree: Optional[int] = None,
    autoriser_fictif: bool = False,
) -> RapportIntegrite:
    """
    `documents_sha256` : empreintes des documents sources FOURNIS avec le lot (import v2).
    None = contrôle non demandé (v1) ; un ensemble (même vide) = chaque source non fictive
    doit y figurer.
    """
    idx = ref.index()
    out: List[Anomalie] = list(valider_referentiel(ref))

    # --- sources / documents -------------------------------------------------------
    if documents_sha256 is not None:
        docs = set(documents_sha256)
        for s in ref.sources:
            if not s.fictive and s.sha256_document not in docs:
                out.append(Anomalie("SOURCE_DOCUMENT_ABSENT", s.id, s.sha256_document[:12]))

    # --- notions : preuve, hash, texte, rentrée -------------------------------------
    for n in ref.notions:
        prog = idx.programmes.get(n.programme_id)
        if n.preuve is not None:
            if not n.preuve.empreinte_coherente():
                out.append(Anomalie("HASH_EXTRAIT_INCOHERENT", n.id))
            if prog is not None and n.preuve.source_id != prog.source_id:
                out.append(Anomalie("PREUVE_SOURCE_AUTRE_PROGRAMME", n.id, n.preuve.source_id))
        if n.statut_texte in STATUTS_TEXTE_UTILISABLES:
            recalc = analyser_texte(n.texte).statut
            if recalc not in STATUTS_TEXTE_UTILISABLES:
                out.append(Anomalie("TEXTE_DECLARE_INCOHERENT", n.id,
                                    f"{n.statut_texte.value} déclaré, {recalc.value} recalculé"))
        if rentree is not None and prog is not None and not prog.en_vigueur(rentree):
            out.append(Anomalie("PROGRAMME_HORS_RENTREE", n.id, f"{prog.id} / {rentree}"))

    # --- contenus ----------------------------------------------------------------------
    ids = Counter([e.id for e in exercices] + [q.id for q in quiz])
    for oid, k in ids.items():
        if k > 1:
            out.append(Anomalie("CONTENU_ID_DUPLIQUE", oid, f"{k} occurrences"))
    banque = BanqueExercices()
    for e in exercices:
        # Banque = contenus PRÉCÉDENTS : un doublon n'est signalé qu'une fois, sur le second.
        for r in valider_exercice(e, idx, banque, autoriser_fictif=autoriser_fictif):
            if not r.startswith("id_deja_utilise"):
                out.append(Anomalie("EXERCICE_INVALIDE", e.id, r))
        banque.ajouter(e)
    for q in quiz:
        for r in valider_question(q, idx, autoriser_fictif=autoriser_fictif):
            out.append(Anomalie("QUIZ_INVALIDE", q.id, r))

    # --- plans de guidage ------------------------------------------------------------
    if plans:
        from app.curriculum.pedagogie.tuteur import valider_plan

        exos = {e.id: e for e in exercices}
        for exo_id, plan in sorted(plans.items()):
            ex = exos.get(exo_id)
            if ex is None:
                out.append(Anomalie("PLAN_SANS_EXERCICE", exo_id))
                continue
            for r in valider_plan(plan, ex, exiger_cle_comprehension=True):
                out.append(Anomalie("PLAN_INVALIDE", exo_id, r))

    anomalies = sorted(set(out))
    return RapportIntegrite(anomalies, _generables(ref, anomalies, exercices, quiz, autoriser_fictif))


def _generables(ref: Referentiel, anomalies: List[Anomalie], exercices, quiz,
                autoriser_fictif: bool) -> FrozenSet[str]:
    if any(a.code in CODES_GLOBAUX for a in anomalies):
        return frozenset()
    idx = ref.index()
    touches = {a.objet_id for a in anomalies}
    # Un contenu invalide rend sa notion non générable (son contenu doit d'abord être corrigé).
    notion_du_contenu: Dict[str, str] = {c.id: c.notion_id for c in [*exercices, *quiz]}
    touches |= {notion_du_contenu[o] for o in list(touches) if o in notion_du_contenu}
    ok = set()
    for n in ref.notions:
        if n.optionnelle or {n.id, n.chapitre_id, n.programme_id} & touches:
            continue
        if autorisation_generation(n, idx, autoriser_fictif=autoriser_fictif).autorise:
            ok.add(n.id)
    return frozenset(ok)


def exiger_integrite(rapport: RapportIntegrite) -> None:
    """Verrou : lève si l'intégrité n'est pas démontrée (aucune génération possible)."""
    if not rapport.demontree:
        codes = ",".join(sorted({a.code for a in rapport.anomalies}))
        raise IntegriteNonDemontree(f"{len(rapport.anomalies)} anomalie(s) : {codes}")


class IntegriteNonDemontree(RuntimeError):
    pass
