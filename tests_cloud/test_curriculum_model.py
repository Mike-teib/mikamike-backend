"""
Tests du modèle canonique, de la provenance, du verrou de génération et du
validateur structurel. Chaque test « négatif » introduit UN défaut précis dans
le référentiel fictif valide et vérifie qu'il est détecté.
"""

import pytest
from pydantic import ValidationError

from app.curriculum.fixtures import referentiel_fictif
from app.curriculum.ids import sha256_texte, slug, stable_id
from app.curriculum.legacy import migrer_existant
from app.curriculum.model import (
    Chapitre,
    Matiere,
    Niveau,
    Programme,
    StatutPreuve,
    StatutTexte,
    Theme,
)
from app.curriculum.provenance import autorisation_generation, evaluer_preuve
from app.curriculum.structure import compter_notions, valider_referentiel


@pytest.fixture()
def ref():
    return referentiel_fictif()


def _remplacer(ref, champ, ancien_id, nouveau):
    objets = tuple(nouveau if o.id == ancien_id else o for o in getattr(ref, champ))
    return ref.model_copy(update={champ: objets})


def _notion(ref, nid):
    return next(n for n in ref.notions if n.id == nid)


def _codes(ref):
    return {a.code for a in valider_referentiel(ref)}


# --------------------------------------------------------------------------- #
# Identifiants stables
# --------------------------------------------------------------------------- #
def test_ids_stables_et_deterministes():
    assert slug("Équations du 1er degré") == "equations-du-1er-degre"
    a = stable_id("chap", "prog:x:y", "Fractions et décimaux")
    assert a == stable_id("chap", "prog:x:y", "Fractions et décimaux") == "chap:prog:x:y:fractions-et-decimaux"
    with pytest.raises(ValueError):
        slug("!!!")


def test_sha256_insensible_aux_espaces_mais_pas_au_contenu():
    assert sha256_texte("a  b\n c") == sha256_texte("a b c")
    assert sha256_texte("1/10") != sha256_texte("0,1")


# --------------------------------------------------------------------------- #
# Modèle : validations d'entrée
# --------------------------------------------------------------------------- #
def test_modele_refuse_champ_inconnu_et_id_invalide():
    with pytest.raises(ValidationError):
        Programme(id="Pas Un Id", source_id="src:x", matiere=Matiere.SVT,
                  niveaux=(Niveau.CINQUIEME,), titre="Titre", rentree_debut=2025)
    with pytest.raises(ValidationError):
        Programme(id="prog:x", source_id="src:x", matiere=Matiere.SVT, niveaux=(Niveau.CINQUIEME,),
                  titre="Titre", rentree_debut=2025, champ_invente=1)


def test_modele_refuse_versions_incoherentes():
    with pytest.raises(ValidationError):
        Programme(id="prog:x", source_id="src:x", matiere=Matiere.SVT, niveaux=(Niveau.CINQUIEME,),
                  titre="Titre", rentree_debut=2025, rentree_fin=2020)


def test_versionnement_par_rentree():
    p = Programme(id="prog:x", source_id="src:x", matiere=Matiere.SVT, niveaux=(Niveau.CINQUIEME,),
                  titre="Titre", rentree_debut=2016, rentree_fin=2024)
    assert p.en_vigueur(2016) and p.en_vigueur(2024)
    assert not p.en_vigueur(2025) and not p.en_vigueur(2015)


def test_referentiel_fictif_valide(ref):
    assert valider_referentiel(ref) == []


# --------------------------------------------------------------------------- #
# Provenance
# --------------------------------------------------------------------------- #
def test_preuve_prouvee_en_mode_test(ref):
    idx = ref.index()
    n = _notion(ref, "notion:fictif:comparer-fractions")
    assert evaluer_preuve(n, idx.sources[n.preuve.source_id], autoriser_fictif=True).statut == StatutPreuve.PROVEN


def test_source_fictive_jamais_prouvee_hors_mode_test(ref):
    idx = ref.index()
    n = _notion(ref, "notion:fictif:comparer-fractions")
    ev = evaluer_preuve(n, idx.sources[n.preuve.source_id])
    assert ev.statut == StatutPreuve.QUARANTINED
    assert "source_fictive_hors_mode_test" in ev.raisons


def test_sans_preuve_not_evidenced(ref):
    n = _notion(ref, "notion:fictif:sans-preuve")
    assert evaluer_preuve(n, None, autoriser_fictif=True).statut == StatutPreuve.NOT_EVIDENCED


def test_empreinte_falsifiee_quarantaine(ref):
    n = _notion(ref, "notion:fictif:comparer-fractions")
    falsifiee = n.model_copy(update={"preuve": n.preuve.model_copy(update={"extrait": n.preuve.extrait + " ajout"})})
    ev = evaluer_preuve(falsifiee, ref.index().sources[n.preuve.source_id], autoriser_fictif=True)
    assert ev.statut == StatutPreuve.QUARANTINED


def test_statut_proven_declare_n_est_pas_cru(ref):
    """Un texte de notion absent de l'extrait n'est pas prouvé, même si déclaré PROVEN."""
    n = _notion(ref, "notion:fictif:comparer-fractions")
    menteuse = n.model_copy(update={"texte": "[FICTIF] Texte qui n'apparaît pas dans la source."})
    ev = evaluer_preuve(menteuse, ref.index().sources[n.preuve.source_id], autoriser_fictif=True)
    assert ev.statut == StatutPreuve.AMBIGUOUS


def test_source_non_enregistree(ref):
    n = _notion(ref, "notion:fictif:comparer-fractions")
    assert evaluer_preuve(n, None, autoriser_fictif=True).statut == StatutPreuve.NOT_EVIDENCED


def test_url_preuve_incoherente_quarantaine(ref):
    n = _notion(ref, "notion:fictif:comparer-fractions")
    autre = n.model_copy(update={"preuve": n.preuve.model_copy(update={"url": "https://autre.invalid/doc.pdf"})})
    ev = evaluer_preuve(autre, ref.index().sources[n.preuve.source_id], autoriser_fictif=True)
    assert ev.statut == StatutPreuve.QUARANTINED


# --------------------------------------------------------------------------- #
# Verrou de génération
# --------------------------------------------------------------------------- #
def test_generation_autorisee_notion_prouvee(ref):
    a = autorisation_generation(_notion(ref, "notion:fictif:comparer-fractions"), ref.index(), autoriser_fictif=True)
    assert a.autorise, a.raisons


def test_generation_refusee_notion_non_prouvee(ref):
    a = autorisation_generation(_notion(ref, "notion:fictif:sans-preuve"), ref.index(), autoriser_fictif=True)
    assert not a.autorise
    assert "preuve_not_evidenced" in a.raisons


def test_generation_refusee_en_production_sur_source_fictive(ref):
    a = autorisation_generation(_notion(ref, "notion:fictif:comparer-fractions"), ref.index())
    assert not a.autorise


@pytest.mark.parametrize("statut", [s for s in StatutTexte if s not in (StatutTexte.TEXT_EXACT, StatutTexte.TEXT_RECOVERED)])
def test_generation_refusee_texte_suspect(ref, statut):
    n = _notion(ref, "notion:fictif:comparer-fractions").model_copy(update={"statut_texte": statut})
    a = autorisation_generation(n, ref.index(), autoriser_fictif=True)
    assert not a.autorise
    assert f"texte_{statut.value.lower()}" in a.raisons


def test_generation_refusee_chapitre_ambigu(ref):
    chap = ref.chapitres[0].model_copy(update={"ambigu": True})
    ref2 = _remplacer(ref, "chapitres", chap.id, chap)
    a = autorisation_generation(_notion(ref2, "notion:fictif:comparer-fractions"), ref2.index(), autoriser_fictif=True)
    assert "chapitre_ambigu" in a.raisons


def test_generation_refusee_notion_sans_chapitre(ref):
    n = _notion(ref, "notion:fictif:comparer-fractions").model_copy(update={"chapitre_id": None})
    a = autorisation_generation(n, ref.index(), autoriser_fictif=True)
    assert "notion_sans_chapitre" in a.raisons


# --------------------------------------------------------------------------- #
# Validateur structurel : une mutation = une anomalie
# --------------------------------------------------------------------------- #
def test_notion_sans_chapitre_detectee(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"chapitre_id": None})
    assert "NOTION_SANS_CHAPITRE" in _codes(_remplacer(ref, "notions", n.id, n))


def test_chapitre_sans_programme_detecte(ref):
    chap = ref.chapitres[0].model_copy(update={"programme_id": "prog:inexistant"})
    assert "CHAPITRE_SANS_PROGRAMME" in _codes(_remplacer(ref, "chapitres", chap.id, chap))


def test_programme_incoherent_matiere_niveau(ref):
    p = ref.programmes[0].model_copy(update={"matiere": Matiere.ENSEIGNEMENT_SCIENTIFIQUE})
    assert "PROGRAMME_INCOHERENT" in _codes(_remplacer(ref, "programmes", p.id, p))


def test_mauvais_niveau_detecte(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"niveau": Niveau.TERMINALE})
    assert "MAUVAIS_NIVEAU" in _codes(_remplacer(ref, "notions", n.id, n))


def test_mauvaise_matiere_detectee(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"matiere": Matiere.SVT})
    assert "MAUVAISE_MATIERE" in _codes(_remplacer(ref, "notions", n.id, n))


def test_mauvais_domaine_detecte(ref):
    th = ref.themes[0].model_copy(update={"domaine_id": "dom:inexistant"})
    assert "MAUVAIS_DOMAINE" in _codes(_remplacer(ref, "themes", th.id, th))


def test_mauvais_theme_detecte(ref):
    chap = ref.chapitres[0].model_copy(update={"theme_id": "theme:inexistant"})
    assert "MAUVAIS_THEME" in _codes(_remplacer(ref, "chapitres", chap.id, chap))


def test_doublon_detecte(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(
        update={"texte": _notion(ref, "notion:fictif:comparer-fractions").texte}
    )
    assert "DOUBLON_NOTION" in _codes(_remplacer(ref, "notions", n.id, n))


def test_prerequis_inconnu_et_cycle(ref):
    n1 = _notion(ref, "notion:fictif:comparer-fractions").model_copy(
        update={"prerequis": ("notion:fictif:fractions-decimales",)}
    )
    ref2 = _remplacer(ref, "notions", n1.id, n1)
    assert "PREREQUIS_CYCLE" in _codes(ref2)
    n3 = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"prerequis": ("notion:inexistante",)})
    assert "PREREQUIS_INCONNU" in _codes(_remplacer(ref, "notions", n3.id, n3))


def test_texte_contamine_detecte(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(
        update={"texte": "[FICTIF] Comparer des fractions Bulletin officiel n° 31 page 12"}
    )
    assert "TEXTE_SUSPECT" in _codes(_remplacer(ref, "notions", n.id, n))


def test_pluridisciplinaire_hors_es_refuse(ref):
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"disciplines_mobilisees": (Matiere.SVT,)})
    assert "PLURIDISCIPLINAIRE_INVALIDE" in _codes(_remplacer(ref, "notions", n.id, n))


def _ajouter_ancienne_version(ref):
    ancien = Programme(
        id="prog:fictif:mathematiques:cycle3:2016", source_id=ref.sources[0].id,
        matiere=Matiere.MATHEMATIQUES, niveaux=(Niveau.SIXIEME,), titre="[FICTIF] ancienne version",
        rentree_debut=2016, rentree_fin=2024,
    )
    th = Theme(id="theme:fictif:ancien", programme_id=ancien.id, domaine_id="dom:fictif:ancien",
               titre="[FICTIF] ancien", ordre=1)
    from app.curriculum.model import Domaine, Notion
    dom = Domaine(id="dom:fictif:ancien", programme_id=ancien.id, titre="[FICTIF] ancien", ordre=1)
    chap = Chapitre(id="chap:fictif:ancien", programme_id=ancien.id, theme_id=th.id,
                    niveau=Niveau.SIXIEME, titre="[FICTIF] ancien", ordre=1)
    vieille = Notion(id="notion:fictif:ancienne", programme_id=ancien.id, chapitre_id=chap.id,
                     niveau=Niveau.SIXIEME, matiere=Matiere.MATHEMATIQUES,
                     texte="[FICTIF] Notion de l'ancienne version.")
    return ref.model_copy(update={
        "programmes": ref.programmes + (ancien,), "domaines": ref.domaines + (dom,),
        "themes": ref.themes + (th,), "chapitres": ref.chapitres + (chap,),
        "notions": ref.notions + (vieille,),
    })


def test_ancienne_version_non_chevauchante_acceptee(ref):
    assert _codes(_ajouter_ancienne_version(ref)) == set()


def test_version_melangee_detectee(ref):
    ref2 = _ajouter_ancienne_version(ref)
    n = _notion(ref2, "notion:fictif:sans-preuve").model_copy(update={"prerequis": ("notion:fictif:ancienne",)})
    assert "VERSION_MELANGEE" in _codes(_remplacer(ref2, "notions", n.id, n))


def test_programmes_chevauchants_detectes(ref):
    ref2 = _ajouter_ancienne_version(ref)
    p = next(p for p in ref2.programmes if p.id.endswith("2016")).model_copy(update={"rentree_fin": 2025})
    assert "PROGRAMMES_CHEVAUCHANTS" in _codes(_remplacer(ref2, "programmes", p.id, p))


def test_id_duplique_detecte(ref):
    n = _notion(ref, "notion:fictif:sans-preuve")
    ref2 = ref.model_copy(update={"notions": ref.notions + (n,)})
    assert "ID_DUPLIQUE" in _codes(ref2)


def test_optionnelles_non_comptees(ref):
    assert compter_notions(ref) == 3
    assert compter_notions(ref, inclure_optionnelles=True) == 4


# --------------------------------------------------------------------------- #
# Migration de l'existant : rien d'inventé
# --------------------------------------------------------------------------- #
def test_migration_existant_honnete():
    m = migrer_existant()
    assert len(m.notions) == 42
    assert {r[1] for r in m.non_migrables} == {"niveau_ambigu:primaire"}
    assert all(n.preuve is None and n.statut_preuve == StatutPreuve.NOT_EVIDENCED for n in m.notions)
    assert all(n.chapitre_id is None for n in m.notions)
    ids = {n.id for n in m.notions}
    assert all(p in ids for n in m.notions for p in n.prerequis)


def test_mauvais_niveau_notion_hors_programme_meme_si_chapitre_coherent(ref):
    # Revue session 2 (R2-29) : le test précédent était aussi satisfait par le contrôle
    # notion/chapitre ; ici notion ET chapitre sont en 5e, hors du programme cycle 3 :
    # seule la règle « niveau hors programme » peut produire l'anomalie SUR LA NOTION.
    from app.curriculum.structure import valider_referentiel

    chap = ref.chapitres[0].model_copy(update={"niveau": Niveau.CINQUIEME})
    n = _notion(ref, "notion:fictif:sans-preuve").model_copy(update={"niveau": Niveau.CINQUIEME})
    ref2 = _remplacer(_remplacer(ref, "chapitres", chap.id, chap), "notions", n.id, n)
    assert any(a.code == "MAUVAIS_NIVEAU" and a.objet_id == n.id and "hors" in a.detail
               for a in valider_referentiel(ref2))
