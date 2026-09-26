"""
provenance.py — Évaluation de la preuve d'une notion et verrou de génération.

Le statut déclaré dans une Preuve n'est JAMAIS cru sur parole : `evaluer_preuve`
le recalcule à partir d'éléments vérifiables (source enregistrée, URL cohérente,
page, extrait, empreinte SHA-256, présence du texte de la notion dans l'extrait).

`autorisation_generation` est le verrou unique : aucune génération d'exercice
ou de quiz ne doit être lancée pour une notion qui ne le franchit pas.
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional

from app.curriculum.ids import normaliser_pour_empreinte
from app.curriculum.model import (
    STATUTS_TEXTE_UTILISABLES,
    Chapitre,
    IndexReferentiel,
    Notion,
    Preuve,
    SourceOfficielle,
    StatutPreuve,
)


class EvaluationPreuve(NamedTuple):
    statut: StatutPreuve
    raisons: List[str]


def _contenu_dans(texte: str, extrait: str) -> bool:
    a = normaliser_pour_empreinte(texte).casefold()
    b = normaliser_pour_empreinte(extrait).casefold()
    return bool(a) and a in b


def evaluer_preuve(
    notion: Notion,
    source: Optional[SourceOfficielle],
    *,
    autoriser_fictif: bool = False,
) -> EvaluationPreuve:
    """
    Recalcule le statut de preuve d'une notion.

    - QUARANTINED : preuve incohérente (empreinte fausse, source d'une autre notion,
      déclarée PROVEN sans justification, source fictive hors mode test) ;
    - AMBIGUOUS   : déclarée ambiguë, ou texte de la notion absent de l'extrait ;
    - NOT_EVIDENCED : aucune preuve, ou source non enregistrée ;
    - PROVEN      : tout est vérifié.
    """
    preuve: Optional[Preuve] = notion.preuve
    if preuve is None:
        return EvaluationPreuve(StatutPreuve.NOT_EVIDENCED, ["aucune_preuve"])

    raisons: List[str] = []
    if preuve.statut == StatutPreuve.QUARANTINED:
        return EvaluationPreuve(StatutPreuve.QUARANTINED, ["quarantaine_declaree"])

    if not preuve.empreinte_coherente():
        return EvaluationPreuve(StatutPreuve.QUARANTINED, ["sha256_extrait_incoherent"])

    if source is None or source.id != preuve.source_id:
        return EvaluationPreuve(StatutPreuve.NOT_EVIDENCED, ["source_non_enregistree"])

    if source.fictive and not autoriser_fictif:
        return EvaluationPreuve(StatutPreuve.QUARANTINED, ["source_fictive_hors_mode_test"])

    if preuve.url != source.url and not preuve.url.startswith(source.url + "#"):
        raisons.append("url_preuve_differente_de_la_source")

    if preuve.statut == StatutPreuve.AMBIGUOUS:
        return EvaluationPreuve(StatutPreuve.AMBIGUOUS, ["ambiguite_declaree", *raisons])

    if not _contenu_dans(notion.texte, preuve.extrait):
        return EvaluationPreuve(StatutPreuve.AMBIGUOUS, ["texte_notion_absent_de_l_extrait", *raisons])

    if raisons:
        # Incohérence de rattachement : on ne prouve pas, on isole.
        return EvaluationPreuve(StatutPreuve.QUARANTINED, raisons)

    return EvaluationPreuve(StatutPreuve.PROVEN, [])


class Autorisation(NamedTuple):
    autorise: bool
    raisons: List[str]


def autorisation_generation(
    notion: Notion,
    idx: IndexReferentiel,
    *,
    autoriser_fictif: bool = False,
) -> Autorisation:
    """
    Verrou de génération de contenu (exercice / quiz) pour une notion.

    Refuse si : preuve non PROVEN, texte non utilisable (tronqué, fragmenté,
    formule corrompue…), notion sans chapitre, chapitre ambigu ou d'un autre
    programme, programme ou source inconnus.
    """
    raisons: List[str] = []

    source = None
    prog = idx.programmes.get(notion.programme_id)
    if prog is None:
        raisons.append("programme_inconnu")
    else:
        source = idx.sources.get(prog.source_id)

    ev = evaluer_preuve(
        notion,
        idx.sources.get(notion.preuve.source_id) if notion.preuve else source,
        autoriser_fictif=autoriser_fictif,
    )
    if ev.statut != StatutPreuve.PROVEN:
        raisons.append(f"preuve_{ev.statut.value.lower()}")
        raisons.extend(ev.raisons)

    if notion.statut_texte not in STATUTS_TEXTE_UTILISABLES:
        raisons.append(f"texte_{notion.statut_texte.value.lower()}")

    chap: Optional[Chapitre] = idx.chapitres.get(notion.chapitre_id) if notion.chapitre_id else None
    if notion.chapitre_id is None:
        raisons.append("notion_sans_chapitre")
    elif chap is None:
        raisons.append("chapitre_inconnu")
    else:
        if chap.ambigu:
            raisons.append("chapitre_ambigu")
        if chap.programme_id != notion.programme_id:
            raisons.append("chapitre_d_un_autre_programme")

    return Autorisation(not raisons, raisons)
