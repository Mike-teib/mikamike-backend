"""
Performance (lot 22, session 4) : beaucoup d'élèves. Le coût d'une lecture pour UN élève
(tableau de bord, états) ne dépend pas du nombre total d'élèves (index eleve_hmac) ; la purge
de rétention reste linéaire. Mesures RELATIVES (robustes à la machine de CI). Données FICTIVES.
"""

import datetime as dt
import time

from sqlalchemy import insert

from app.api.v1.mikamike import crud
from app.api.v1.mikamike.store import SessionLocal, TentativeExercice
from app.api.v1.session.session_manager import MikaSessionState
from app.core import retention
from app.db.registre import creer_tables_pour_tests

T0 = dt.datetime(2030, 1, 1)


def _peupler(n_eleves, par_eleve=10):
    creer_tables_pour_tests(reinitialiser=True)
    with SessionLocal() as db:
        lignes = [{"eleve_hmac": f"{e:016x}", "exercice_id": f"exo-{i}", "competence": f"c{i % 4}",
                   "est_correct": i % 3 == 0, "avec_aide": False, "ts": T0 + dt.timedelta(minutes=i)}
                  for e in range(n_eleves) for i in range(par_eleve)]
        db.execute(insert(TentativeExercice), lignes)
        db.execute(insert(MikaSessionState), [
            {"session_id": f"s{e}", "eleve_hmac": f"{e:016x}", "is_active": False,
             "last_activity_ts": T0 - dt.timedelta(days=60 * (e % 2)), "created_at": T0, "state_json": "{}"}
            for e in range(n_eleves)])
        db.commit()


def _mesure_dashboard(repetitions=200):
    with SessionLocal() as db:
        t = time.perf_counter()
        for k in range(repetitions):
            crud.agreger_dashboard(db, f"{k % 50:016x}")
        return time.perf_counter() - t


def test_dashboard_independant_du_nombre_d_eleves():
    _peupler(100)
    petit = _mesure_dashboard()
    _peupler(5000)
    grand = _mesure_dashboard()
    creer_tables_pour_tests(reinitialiser=True)
    # 50× plus d'élèves : sans index ce serait ≈ 50× ; on exige < 4× (bruit CI compris).
    assert grand / petit < 4, (petit, grand)


def test_purge_retention_lineaire():
    durees = {}
    for n in (1000, 4000):
        _peupler(n, par_eleve=1)
        with SessionLocal() as db:
            t = time.perf_counter()
            r = retention.purger_mika(db, appliquer=True, maintenant=T0)
            durees[n] = time.perf_counter() - t
        assert r["mika_session_states"] == n // 2
    creer_tables_pour_tests(reinitialiser=True)
    assert durees[4000] / durees[1000] < 12, durees  # linéaire ⇒ ≈ 4× ; quadratique ⇒ 16×
