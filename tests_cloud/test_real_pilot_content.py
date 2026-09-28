from app.api.v1.tutorat import contenu
from app.api.v1.tutorat.pilot_reel import EXERCICE_ID, NOTION_ID, catalogue_pilote_reel
from app.curriculum.model import StatutPreuve


def test_mini_pilote_reel_est_proven_et_serviable():
    cat = catalogue_pilote_reel()
    ex, plan = cat.obtenir(EXERCICE_ID)
    notion = cat.idx.notions[NOTION_ID]

    assert ex.id == EXERCICE_ID
    assert ex.enonce == "Calcule : 8 + 3 × 2"
    assert ex.reponse_attendue == "14"
    assert ex.niveau.value == "5e"
    assert ex.matiere.value == "mathematiques"
    assert notion.preuve is not None
    assert notion.preuve.statut == StatutPreuve.PROVEN
    assert notion.preuve.empreinte_coherente()
    assert plan.question_comprehension
    assert plan.reponse_comprehension == "6"


def test_catalogue_par_defaut_est_le_mini_pilote_reel():
    contenu.definir_catalogue(None)
    cat = contenu.catalogue()
    assert EXERCICE_ID in cat.exercices
    ex, _ = cat.obtenir(EXERCICE_ID)
    assert ex.notion_id == NOTION_ID
