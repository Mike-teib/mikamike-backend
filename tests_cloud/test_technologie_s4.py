"""
Sciences et technologie (lot 16) : bilans énergétiques restreints aux grandeurs énergétiques,
niveaux/cycles non modélisés refusés (aucun programme inventé).
"""

import pytest

from app.curriculum.model import CYCLE_DU_NIVEAU, NIVEAUX_PAR_MATIERE, Cycle, Matiere, Niveau
from app.curriculum.verifiers.base import Verdict as V
from app.curriculum.verifiers.technologie import verifier_bilan_energetique


@pytest.mark.parametrize("a,u,verdict", [
    ("100 J", "80 J", V.VALID), ("100 W", "80 W", V.VALID), ("2 kWh", "1 kWh", V.VALID),
    ("100 m", "80 m", V.INVALID), ("100 kg", "80 kg", V.INVALID), ("10 V", "8 V", V.INVALID),
    ("100 W", "80 J", V.INVALID),
])
def test_bilan_limite_aux_grandeurs_energetiques(a, u, verdict):
    assert verifier_bilan_energetique(a, u).verdict == verdict


def test_sciences_et_technologie_limite_au_cycle_3_modelise():
    # Le modèle ne connaît que le cycle 3 pour cette matière ; cycle 2 et technologie de cycle 4
    # restent WAITING_FOR_ARTIFACT (aucun programme officiel fourni) : pas de niveau inventé.
    niveaux = NIVEAUX_PAR_MATIERE[Matiere.SCIENCES_ET_TECHNOLOGIE]
    assert {CYCLE_DU_NIVEAU[n] for n in niveaux} == {Cycle.CYCLE_3}
    assert Niveau.CINQUIEME not in niveaux
    assert "cycle2" not in {c.value for c in Cycle}
    assert "technologie" not in {m.value for m in Matiere}
