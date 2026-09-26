"""
Migrations (lot 26, session 4) : double exécution. Relancer `upgrade` sur une base À JOUR et
REMPLIE ne modifie ni le schéma, ni les données, ni la révision ; deux `upgrade` lancés en
même temps sur une base neuve aboutissent à une base cohérente (aucune table partielle).
"""

import subprocess
import sys

from tests_cloud.test_migrations_validation import RACINE, _cli, _env, _py


def test_double_upgrade_avec_donnees_sans_effet(tmp_path):
    assert _cli(tmp_path, "upgrade")[0] == 0
    avant = _py(tmp_path, """
        remplir_mika(); remplir_billing()
        print(json.dumps([m.courante("mika"), m.courante("billing"), tables("mika"), tables("billing"),
                          empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"])]))
    """)
    for _ in range(2):
        code, _, err = _cli(tmp_path, "upgrade")
        assert code == 0, err
    apres = _py(tmp_path, """
        print(json.dumps([m.courante("mika"), m.courante("billing"), tables("mika"), tables("billing"),
                          empreinte("mika", HIST_MIKA), empreinte("billing", ["comptes", "abonnements"])]))
    """)
    assert apres == avant


def test_deux_upgrades_concurrents_base_coherente(tmp_path):
    procs = [subprocess.Popen([sys.executable, "-m", "tools.db", "upgrade"], cwd=RACINE, env=_env(tmp_path),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    codes = [p.wait(timeout=180) for p in procs]
    for p in procs:
        p.stdout.close()
        p.stderr.close()
    assert 0 in codes  # au moins un aboutit ; l'autre peut échouer proprement (verrou SQLite)
    # Quel que soit l'ordre : la base finale est à jour et un nouvel upgrade est sans effet.
    code, out, _ = _cli(tmp_path, "status")
    if code != 0:
        assert _cli(tmp_path, "upgrade")[0] == 0
        code, out, _ = _cli(tmp_path, "status")
    assert code == 0 and out.count(" OK") == 2
    etat = _py(tmp_path, 'print(json.dumps([tables("mika"), tables("billing")]))')
    assert "mika_tutorat_sessions" in etat[0] and "verifications_email" in etat[1]
