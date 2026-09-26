"""
fixtures.py — Référentiel FICTIF pour tests et démonstration hors ligne.

⚠ Rien ici n'est un programme officiel. La source est marquée `fictive=True`,
son URL pointe vers le domaine réservé `example.invalid`, et chaque texte est
préfixé « [FICTIF] ». En mode normal, `evaluer_preuve` met une notion adossée à
une source fictive en QUARANTINED : ces données ne peuvent donc jamais passer
pour prouvées en production.
"""

from __future__ import annotations

from app.curriculum.ids import sha256_texte
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

SOURCE_FICTIVE_ID = "src:fictif:demo"
URL_FICTIVE = "https://example.invalid/programme-fictif.pdf"

EXTRAIT_P3 = (
    "[FICTIF] Comparer, ranger et encadrer des fractions de même dénominateur. "
    "[FICTIF] Utiliser l'écriture fractionnaire 1/10 et 1/100 pour les nombres décimaux."
)
EXTRAIT_P4 = "[FICTIF] Pour aller plus loin. [FICTIF] Encadrer une fraction entre deux entiers consécutifs."


def _preuve(extrait: str, page: int, statut: StatutPreuve = StatutPreuve.PROVEN) -> Preuve:
    return Preuve(
        source_id=SOURCE_FICTIVE_ID,
        document="programme-fictif.pdf",
        url=URL_FICTIVE,
        page=page,
        section="[FICTIF] Nombres et calculs",
        extrait=extrait,
        sha256_extrait=sha256_texte(extrait),
        statut=statut,
        date_verification="2026-09-26",
    )


def referentiel_fictif() -> Referentiel:
    src = SourceOfficielle(
        id=SOURCE_FICTIVE_ID,
        titre="[FICTIF] Programme de démonstration",
        editeur="MikaMike — fixtures de test",
        url=URL_FICTIVE,
        reference="FIXTURE_FICTIVE",
        date_publication="2026-09-01",
        sha256_document="0" * 64,
        fictive=True,
    )
    prog = Programme(
        id="prog:fictif:mathematiques:cycle3:2025",
        source_id=src.id,
        matiere=Matiere.MATHEMATIQUES,
        niveaux=(Niveau.CM1, Niveau.CM2, Niveau.SIXIEME),
        titre="[FICTIF] Mathématiques cycle 3",
        rentree_debut=2025,
    )
    dom = Domaine(id="dom:fictif:nombres", programme_id=prog.id, titre="[FICTIF] Nombres et calculs", ordre=1)
    th = Theme(id="theme:fictif:fractions", programme_id=prog.id, domaine_id=dom.id,
               titre="[FICTIF] Fractions et décimaux", ordre=1)
    chap = Chapitre(id="chap:fictif:fractions-6e", programme_id=prog.id, theme_id=th.id,
                    niveau=Niveau.SIXIEME, titre="[FICTIF] Fractions", ordre=1)

    n1 = Notion(
        id="notion:fictif:comparer-fractions",
        programme_id=prog.id, chapitre_id=chap.id, niveau=Niveau.SIXIEME,
        matiere=Matiere.MATHEMATIQUES,
        texte="[FICTIF] Comparer, ranger et encadrer des fractions de même dénominateur.",
        statut_texte=StatutTexte.TEXT_EXACT,
        preuve=_preuve(EXTRAIT_P3, page=3),
    )
    n2 = Notion(
        id="notion:fictif:fractions-decimales",
        programme_id=prog.id, chapitre_id=chap.id, niveau=Niveau.SIXIEME,
        matiere=Matiere.MATHEMATIQUES,
        texte="[FICTIF] Utiliser l'écriture fractionnaire 1/10 et 1/100 pour les nombres décimaux.",
        statut_texte=StatutTexte.TEXT_EXACT,
        preuve=_preuve(EXTRAIT_P3, page=3),
        prerequis=(n1.id,),
    )
    # Notion sans preuve : doit rester NOT_EVIDENCED et bloquer la génération.
    n3 = Notion(
        id="notion:fictif:sans-preuve",
        programme_id=prog.id, chapitre_id=chap.id, niveau=Niveau.SIXIEME,
        matiere=Matiere.MATHEMATIQUES,
        texte="[FICTIF] Notion déclarée sans preuve.",
        statut_texte=StatutTexte.SOURCE_NOT_EVIDENCED,
    )
    # Notion optionnelle prouvée : ne compte pas dans le total officiel.
    n4 = Notion(
        id="notion:fictif:optionnelle",
        programme_id=prog.id, chapitre_id=chap.id, niveau=Niveau.SIXIEME,
        matiere=Matiere.MATHEMATIQUES,
        texte="[FICTIF] Encadrer une fraction entre deux entiers consécutifs.",
        statut_texte=StatutTexte.TEXT_EXACT,
        preuve=_preuve(EXTRAIT_P4, page=4),
        optionnelle=True,
    )

    notions = (n1, n2, n3, n4)
    return Referentiel(sources=(src,), programmes=(prog,), domaines=(dom,), themes=(th,),
                       chapitres=(chap,), notions=notions)
