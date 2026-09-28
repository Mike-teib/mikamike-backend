"""Mini-catalogue réel de production MikaMike.

Contenu volontairement minimal : un exercice historique déjà validé par Mike,
rattaché à une notion officielle prouvée du programme de mathématiques de 5e
applicable à la rentrée 2026-2027.

Ce module ne charge AUCUN brouillon de la mégabanque pédagogique.
"""
from __future__ import annotations

from functools import lru_cache

from app.api.v1.tutorat.contenu import CatalogueTutorat
from app.curriculum.exercices import Exercice
from app.curriculum.model import (
    Chapitre,
    Domaine,
    Matiere,
    Niveau,
    Notion,
    Preuve,
    Programme,
    Referentiel,
    SourceOfficielle,
    StatutPreuve,
    StatutTexte,
    Theme,
)
from app.curriculum.pedagogie.tuteur import PlanGuidage

SOURCE_ID = "source:bo:maths-c4-2026"
PROGRAMME_ID = "programme:maths:c4-2026"
DOMAINE_ID = "domaine:maths:nombres-calculs"
THEME_ID = "theme:maths:operations"
CHAPITRE_ID = "chapitre:maths:5e:operations"
NOTION_ID = "notion:maths:5e:priorites-operatoires"
EXERCICE_ID = "exo:maths:5e:priorites-01"

_SOURCE_URL = "https://www.education.gouv.fr/bo/2026/Hebdo10/MENE2602912A"
_TEXTE_NOTION = "Connaitre et utiliser les priorités opératoires."
_SHA_EXTRAIT = "95410a1e7b83bb45bb707e2c313368f7d1e277485ca4eadb8a79ce9977fdc418"
_SHA_DOCUMENT = "e20a05da6c68a08c4487fc63a3345c902f5249b4bf6e950765bfb9c2da0aadb9"


@lru_cache(maxsize=1)
def catalogue_pilote_reel() -> CatalogueTutorat:
    source = SourceOfficielle(
        id=SOURCE_ID,
        titre="Programme de mathématiques pour le cycle 4",
        editeur="Ministère de l'Éducation nationale",
        url=_SOURCE_URL,
        reference="BO n°10 du 5 mars 2026 — annexe 2 — NOR MENE2602912A",
        date_publication="2026-03-05",
        sha256_document=_SHA_DOCUMENT,
        fictive=False,
    )
    programme = Programme(
        id=PROGRAMME_ID,
        source_id=SOURCE_ID,
        matiere=Matiere.MATHEMATIQUES,
        niveaux=(Niveau.CINQUIEME,),
        titre="Programme de mathématiques du cycle 4 — 5e — rentrée 2026-2027",
        rentree_debut=2026,
    )
    domaine = Domaine(
        id=DOMAINE_ID,
        programme_id=PROGRAMME_ID,
        titre="Nombres et calculs",
        ordre=1,
    )
    theme = Theme(
        id=THEME_ID,
        programme_id=PROGRAMME_ID,
        domaine_id=DOMAINE_ID,
        titre="Opérations",
        ordre=1,
    )
    chapitre = Chapitre(
        id=CHAPITRE_ID,
        programme_id=PROGRAMME_ID,
        theme_id=THEME_ID,
        niveau=Niveau.CINQUIEME,
        titre="Opérations",
        ordre=1,
        ambigu=False,
    )
    preuve = Preuve(
        source_id=SOURCE_ID,
        document="Programme de mathématiques pour le cycle 4 — annexe 2",
        url=_SOURCE_URL,
        page=7,
        section="Nombres et calculs — Cinquième — Opérations",
        extrait=_TEXTE_NOTION,
        sha256_extrait=_SHA_EXTRAIT,
        statut=StatutPreuve.PROVEN,
        date_verification="2026-09-28",
    )
    notion = Notion(
        id=NOTION_ID,
        programme_id=PROGRAMME_ID,
        chapitre_id=CHAPITRE_ID,
        niveau=Niveau.CINQUIEME,
        matiere=Matiere.MATHEMATIQUES,
        texte=_TEXTE_NOTION,
        statut_texte=StatutTexte.TEXT_EXACT,
        preuve=preuve,
        prerequis=(),
        id_historique="MATHS.5E.NC.priorites-operatoires",
    )
    referentiel = Referentiel(
        sources=(source,),
        programmes=(programme,),
        domaines=(domaine,),
        themes=(theme,),
        chapitres=(chapitre,),
        notions=(notion,),
    )
    exercice = Exercice(
        id=EXERCICE_ID,
        notion_id=NOTION_ID,
        matiere=Matiere.MATHEMATIQUES,
        niveau=Niveau.CINQUIEME,
        programme_id=PROGRAMME_ID,
        chapitre_id=CHAPITRE_ID,
        difficulte=1,
        objectif_pedagogique="Appliquer correctement les priorités opératoires.",
        prerequis=(),
        enonce="Calcule : 8 + 3 × 2",
        reponse_attendue="14",
        type_verification="maths_symbolique",
        indices=(
            "Repère d’abord la multiplication dans l’expression.",
            "Calcule 3 × 2 avant d’effectuer l’addition.",
        ),
        erreurs_frequentes={
            "22": "Tu as calculé de gauche à droite sans respecter la priorité de la multiplication."
        },
        source_sha256_extrait=_SHA_EXTRAIT,
    )
    plan = PlanGuidage(
        questions_intermediaires=("Quelle opération dois-tu effectuer en premier ?",),
        methodes_alternatives=(
            "Souligne d’abord les produits et quotients, calcule-les, puis réécris l’expression.",
        ),
        question_comprehension="Dans 5 + 2 × 3, quel résultat obtiens-tu après la première opération ?",
        reponse_comprehension="6",
        type_verification_comprehension="maths_symbolique",
        correction_commentee=(
            "La multiplication est prioritaire : 3 × 2 = 6. "
            "On calcule ensuite 8 + 6 = 14."
        ),
        exercice_consolidation_id=None,
    )
    return CatalogueTutorat(referentiel, [exercice], {EXERCICE_ID: plan})


def metadonnees_exercices() -> list[dict[str, str]]:
    cat = catalogue_pilote_reel()
    return [
        {
            "exercice_id": ex.id,
            "notion_id": ex.notion_id,
            "niveau": ex.niveau.value,
            "matiere": ex.matiere.value,
            "consigne": ex.enonce,
        }
        for ex in cat.exercices.values()
    ]
