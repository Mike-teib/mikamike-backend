"""
Enseignement scientifique (lot 17) : la provenance des disciplines est vérifiée à la structure.
Une notion d'ES sans relevé des disciplines de la source n'est pas générable ; une source
pluridisciplinaire n'est jamais forcée dans une matière unique. Données FICTIVES.
"""

from app.curriculum.model import Matiere, Niveau, Notion, Preuve, Programme
import pytest

from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.structure import valider_referentiel


@pytest.fixture()
def ref():
    return referentiel_fictif()


def _remplacer(ref, champ, ancien_id, nouveau):
    return ref.model_copy(update={champ: tuple(nouveau if o.id == ancien_id else o for o in getattr(ref, champ))})


def _codes(ref):
    return {(a.code, a.objet_id) for a in valider_referentiel(ref)}


def _notion_es(ref, disciplines, indiquees):
    src = ref.sources[0]
    prog = Programme(id="prog:fictif:es:lycee:2030", source_id=src.id, matiere=Matiere.ENSEIGNEMENT_SCIENTIFIQUE,
                     niveaux=(Niveau.PREMIERE,), titre="[FICTIF] ES", rentree_debut=2030)
    base = ref.notions[0]
    preuve = base.preuve.model_copy(update={"disciplines_indiquees": indiquees}) if base.preuve else Preuve(
        source_id=src.id, document="fictif.pdf", url="https://exemple.invalid/fictif", page=1,
        extrait="[FICTIF]", sha256_extrait="0" * 64, disciplines_indiquees=indiquees)
    n = Notion(id="notion:fictif:es-energie", programme_id=prog.id, niveau=Niveau.PREMIERE,
               matiere=Matiere.ENSEIGNEMENT_SCIENTIFIQUE, texte="[FICTIF] Notion ES énergie",
               preuve=preuve, disciplines_mobilisees=disciplines)
    return ref.model_copy(update={"programmes": (*ref.programmes, prog), "notions": (*ref.notions, n)}), n.id


def test_es_conforme_a_la_source(ref):
    r, nid = _notion_es(ref, (Matiere.PHYSIQUE_CHIMIE, Matiere.SVT), (Matiere.PHYSIQUE_CHIMIE, Matiere.SVT))
    assert ("DISCIPLINES_NON_PROUVEES", nid) not in _codes(r)


def test_es_sans_releve_des_disciplines(ref):
    r, nid = _notion_es(ref, (Matiere.PHYSIQUE_CHIMIE,), None)
    assert ("DISCIPLINES_NON_PROUVEES", nid) in _codes(r)


def test_es_discipline_inventee_ou_oubliee(ref):
    r, nid = _notion_es(ref, (Matiere.PHYSIQUE_CHIMIE, Matiere.SVT), (Matiere.PHYSIQUE_CHIMIE,))
    assert ("DISCIPLINES_NON_PROUVEES", nid) in _codes(r)
    r, nid = _notion_es(ref, (Matiere.PHYSIQUE_CHIMIE,), (Matiere.PHYSIQUE_CHIMIE, Matiere.MATHEMATIQUES))
    assert ("DISCIPLINES_NON_PROUVEES", nid) in _codes(r)


def test_source_pluridisciplinaire_forcee_dans_une_matiere(ref):
    n = ref.notions[0]
    assert n.preuve is not None
    n2 = n.model_copy(update={"preuve": n.preuve.model_copy(
        update={"disciplines_indiquees": (Matiere.MATHEMATIQUES, Matiere.PHYSIQUE_CHIMIE)})})
    assert ("DISCIPLINES_NON_PROUVEES", n.id) in _codes(_remplacer(ref, "notions", n.id, n2))
    n3 = n.model_copy(update={"preuve": n.preuve.model_copy(update={"disciplines_indiquees": (n.matiere,)})})
    assert ("DISCIPLINES_NON_PROUVEES", n.id) not in _codes(_remplacer(ref, "notions", n.id, n3))


def test_notion_mono_sans_releve_inchangee(ref):
    assert not any(c == "DISCIPLINES_NON_PROUVEES" for c, _ in _codes(ref))
