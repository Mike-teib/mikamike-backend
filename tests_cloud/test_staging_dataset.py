"""
test_staging_dataset.py — Jeu de données SYNTHÉTIQUE de staging (app/curriculum/staging_synthetique.py,
tools/staging_dataset.py, STAGING_DATASET.md).

Couverture, déterminisme, intégrité (0 anomalie), absence de toute donnée réelle, import v2
VALIDATED, chargement idempotent en base jetable, refus en production / sur base non synthétique,
niveaux de progression variés, cohérence du tableau de bord parent avec les tentatives chargées.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.curriculum import staging_synthetique as s
from app.curriculum.importers import importer
from app.curriculum.integrite import verifier_integrite
from app.curriculum.model import CYCLE_DU_NIVEAU, NIVEAUX_PAR_MATIERE, Matiere, Niveau
from app.curriculum.pedagogie.progression import Niveau as NiveauProgression
from app.curriculum.pedagogie.progression import diagnostiquer
from app.curriculum.quiz import QuestionQuiz
from app.curriculum.quiz_types import valider as valider_quiz_type
from app.curriculum.structure import valider_referentiel
from tools import staging_dataset as cli

MARQUE = "[SYNTHÉTIQUE]"


@pytest.fixture(scope="module")
def jeu():
    ref = s.referentiel_staging()
    return {
        "ref": ref,
        "exercices": s.exercices_staging(ref),
        "quiz": s.quiz_staging(ref),
        "complementaires": s.quiz_complementaires_staging(ref),
        "familles": s.familles_staging(),
        "historiques": s.historiques_staging(ref),
    }


@pytest.fixture(scope="module")
def lot(tmp_path_factory):
    """(racine générée, SHA du manifest de contenu, SHA du manifeste utilisateurs)."""
    racine = tmp_path_factory.mktemp("staging") / "lot"
    res = s.ecrire_lot_staging(racine)
    return racine, res.sha_contenu, res.sha_utilisateurs


def _fichiers(d: Path):
    return sorted(p for p in d.rglob("*") if p.is_file())


# --------------------------------------------------------------------------- #
# Couverture
# --------------------------------------------------------------------------- #
def test_couverture_matieres_niveaux_chapitres_notions(jeu):
    ref = jeu["ref"]
    assert {n.matiere for n in ref.notions} == set(Matiere)
    niveaux_par_matiere = defaultdict(set)
    for c in ref.chapitres:
        prog = ref.index().programmes[c.programme_id]
        niveaux_par_matiere[prog.matiere].add(c.niveau)
        assert c.niveau in prog.niveaux
    for m, niveaux in niveaux_par_matiere.items():
        assert len(niveaux) >= 2, m
        assert niveaux <= NIVEAUX_PAR_MATIERE[m], m
    assert niveaux_par_matiere[Matiere.ENSEIGNEMENT_SCIENTIFIQUE] == {Niveau.PREMIERE, Niveau.TERMINALE}
    # Un programme ne couvre qu'un cycle (CYCLE_DU_NIVEAU), identifié dans son id.
    for p in ref.programmes:
        assert {CYCLE_DU_NIVEAU[n].value for n in p.niveaux} == {p.id.split(":")[3]}
        assert set(p.niveaux) <= NIVEAUX_PAR_MATIERE[p.matiere]

    chap_par_niveau = Counter((ref.index().programmes[c.programme_id].matiere, c.niveau) for c in ref.chapitres)
    assert min(chap_par_niveau.values()) >= 2
    notions_par_chap = Counter(n.chapitre_id for n in ref.notions)
    assert set(notions_par_chap) == {c.id for c in ref.chapitres}
    assert min(notions_par_chap.values()) >= 3


def test_prerequis_chaines_sans_cycle(jeu):
    ref = jeu["ref"]
    codes = {a.code for a in valider_referentiel(ref)}
    assert "PREREQUIS_CYCLE" not in codes and "PREREQUIS_INCONNU" not in codes
    avec = [n for n in ref.notions if n.prerequis]
    assert len(avec) >= len(ref.notions) // 2
    # Chaîne : chaque prérequis précède la notion (ordre topologique = ordre d'écriture).
    rang = {n.id: i for i, n in enumerate(ref.notions)}
    assert all(rang[p] < rang[n.id] for n in avec for p in n.prerequis)


def test_contenus_par_notion_et_par_chapitre(jeu):
    ref, exos, quiz, compl = jeu["ref"], jeu["exercices"], jeu["quiz"], jeu["complementaires"]
    exos_par_notion = Counter(e.notion_id for e in exos)
    assert set(exos_par_notion) == {n.id for n in ref.notions}
    assert min(exos_par_notion.values()) >= 1
    chap_de = {n.id: n.chapitre_id for n in ref.notions}
    qcm_par_chap = Counter(chap_de[q.notion_id] for q in quiz)
    autres_par_chap = Counter(chap_de[q.notion_id] for q in compl)
    for c in ref.chapitres:
        assert qcm_par_chap[c.id] >= 1 and autres_par_chap[c.id] >= 1, c.id
    assert all(isinstance(q, QuestionQuiz) for q in quiz)
    assert {q.type for q in compl} >= {"vrai_faux", "classement"}
    # Les vérificateurs employés correspondent aux matières (dispatch.TYPES_VERIFICATION).
    types = defaultdict(set)
    for e in exos:
        types[e.matiere].add(e.type_verification)
    assert "svt_vocabulaire" in types[Matiere.SVT]
    assert "physique_grandeur" in types[Matiere.PHYSIQUE_CHIMIE]
    assert types[Matiere.MATHEMATIQUES] == {"maths_symbolique"}


# --------------------------------------------------------------------------- #
# Déterminisme
# --------------------------------------------------------------------------- #
def test_deux_generations_memes_octets_meme_sha(tmp_path):
    sha_a = s.ecrire_lot_staging(tmp_path / "a")
    sha_b = s.ecrire_lot_staging(tmp_path / "b")
    assert sha_a == sha_b and sha_a.sha_contenu != sha_a.sha_utilisateurs
    fa = sorted(p.relative_to(tmp_path / "a") for p in (tmp_path / "a").rglob("*") if p.is_file())
    fb = sorted(p.relative_to(tmp_path / "b") for p in (tmp_path / "b").rglob("*") if p.is_file())
    assert fa == fb and len(fa) > 10
    for rel in fa:
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes(), rel
    # Une autre graine change les contenus (nombres), donc le SHA.
    autre = s.ecrire_lot_staging(tmp_path / "c", "autre-graine")
    assert autre.sha_contenu != sha_a.sha_contenu and autre.sha_utilisateurs != sha_a.sha_utilisateurs


def test_dossier_non_vide_refuse(tmp_path):
    (tmp_path / "intrus.txt").write_text("x", "utf-8")
    with pytest.raises(FileExistsError):
        s.ecrire_lot_staging(tmp_path)


# --------------------------------------------------------------------------- #
# Intégrité et import
# --------------------------------------------------------------------------- #
def test_integrite_zero_anomalie_toutes_notions_generables(jeu):
    ref = jeu["ref"]
    rap = verifier_integrite(ref, jeu["exercices"], jeu["quiz"], rentree=2026, autoriser_fictif=True)
    assert rap.anomalies == []
    assert rap.generables == frozenset(n.id for n in ref.notions)
    idx = ref.index()
    assert [(q.id, r) for q in jeu["complementaires"] for r in valider_quiz_type(q, idx, autoriser_fictif=True)] == []


def test_hors_mode_test_le_lot_fictif_est_refuse(jeu):
    rap = verifier_integrite(jeu["ref"], jeu["exercices"], jeu["quiz"], autoriser_fictif=False)
    assert "SOURCE_FICTIVE_HORS_TEST" in {a.code for a in rap.anomalies}
    assert rap.generables == frozenset()


def test_import_v2_validated(lot):
    dossier, sha = lot[0] / "contenu", lot[1]
    res = importer(dossier, sha256_manifest=sha, rentree=2026, autoriser_fictif=True)
    assert res.statut == "VALIDATED", res.anomalies[:5] or res.fichiers
    assert res.anomalies == []
    assert len(res.exercices) == 216 and len(res.quiz) == 108
    assert set(res.rattachements.values()) == {"PROUVE"}
    assert len(res.integrite.generables) == len(res.referentiel.notions) == 108
    roles = {o.get("role") for o in res.opaques if o["statut"] == "OPAQUE_A_MAPPER"}
    assert roles == {"rapport"}  # quiz complémentaires : empreinte seule, non interprétés
    assert {o["chemin"] for o in res.opaques if o["statut"] == "OPAQUE_A_MAPPER"} == {"quiz_complementaires.jsonl"}
    # Sans autorisation explicite du fictif (production) : jamais VALIDATED.
    assert importer(dossier, sha256_manifest=sha, autoriser_fictif=False).statut == "REJECTED"
    # Manifest non épinglé ou autre empreinte : FAILED.
    assert importer(dossier, sha256_manifest="0" * 64, autoriser_fictif=True).statut == "FAILED"


def test_cli_verifier(lot, capsys):
    racine, sha = lot[0], lot[1]
    for dossier in (racine, racine / "contenu"):  # racine générée ou lot de contenu directement
        assert cli.main(["verifier", "--dossier", str(dossier), "--sha", sha]) == 0
        sortie = capsys.readouterr().out
        assert "import: VALIDATED" in sortie and "108/108" in sortie
    # Le SHA des utilisateurs n'est pas celui du lot de contenu : refus.
    assert cli.main(["verifier", "--dossier", str(racine), "--sha", lot[2]]) == 1


def test_cli_generer_affiche_sha_et_statistiques(tmp_path, capsys, lot):
    assert cli.main(["generer", "--sortie", str(tmp_path / "g")]) == 0
    sortie = capsys.readouterr().out
    assert f"sha256_manifest_contenu: {lot[1]}" in sortie
    assert f"sha256_manifest_utilisateurs: {lot[2]}" in sortie
    for m in Matiere:
        assert m.value in sortie


# --------------------------------------------------------------------------- #
# Aucune donnée réelle
# --------------------------------------------------------------------------- #
def test_aucune_donnee_reelle(jeu, lot):
    ref, fam = jeu["ref"], jeu["familles"]
    for src in ref.sources:
        assert src.fictive and src.url.startswith("https://example.invalid/") and src.titre.startswith(MARQUE)
    for n in ref.notions:
        assert n.texte.startswith(MARQUE) and n.preuve.extrait.startswith(MARQUE)
        assert n.preuve.url.startswith("https://example.invalid/")
    for groupe in (ref.programmes, ref.domaines, ref.themes, ref.chapitres):
        assert all(o.titre.startswith(MARQUE) for o in groupe)
    for e in jeu["exercices"]:
        assert e.enonce.startswith(MARQUE) and e.objectif_pedagogique.startswith(MARQUE)
    for q in [*jeu["quiz"], *jeu["complementaires"]]:
        assert q.enonce.startswith(MARQUE) and q.explication.startswith(MARQUE)

    # Familles : e-mails réservés, pseudo-identifiants, aucun prénom (libellés « Élève 001 »).
    for p in fam["parents"]:
        assert re.fullmatch(r"parent-synth-\d{3}@example\.com", p["email"])
        assert re.fullmatch(r"Parent \d{3}", p["libelle"])
    for e in fam["eleves"]:
        assert re.fullmatch(r"eleve-synth-\d{3}", e["pseudo_id"])
        assert re.fullmatch(r"Élève \d{3}", e["libelle"])
    cles = set()
    for o in [*fam["parents"], *fam["eleves"], *jeu["historiques"]]:
        cles |= set(o)
    assert not cles & {"prenom", "nom", "telephone", "adresse", "date_naissance", "photo", "ip"}

    # Balayage de TOUS les fichiers du lot : aucune adresse hors example.com / example.invalid.
    for p in _fichiers(lot[0]):
        texte = p.read_text("utf-8")
        for adresse in re.findall(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", texte):
            assert adresse == "example.com", p
        for url in re.findall(r"https?://([^/\s\"]+)", texte):
            assert url == "example.invalid", p
        assert not re.search(r"(?<![\w.])(?:\+33\s?|0)[1-9](?:[\s.\-]?\d{2}){4}(?![\w.])", texte), p


def test_familles_structure():
    fam = s.familles_staging()
    assert len(fam["parents"]) >= 5 and len(fam["eleves"]) >= 8
    parents_de = Counter(e for p in fam["parents"] for e in p["enfants"])
    assert max(parents_de.values()) >= 2                         # un enfant avec 2 parents
    assert max(len(p["enfants"]) for p in fam["parents"]) >= 2   # un parent avec 2 enfants
    assert set(parents_de) == {e["pseudo_id"] for e in fam["eleves"]}  # chaque élève a un parent


# --------------------------------------------------------------------------- #
# Progression
# --------------------------------------------------------------------------- #
def test_historiques_produisent_des_niveaux_varies(jeu):
    lignes = jeu["historiques"]
    assert {li["avec_aide"] for li in lignes} == {True, False}
    par_comp = s.tentatives_par_competence(lignes)
    niveaux = Counter(diagnostiquer(h).niveau for h in par_comp.values())
    assert set(niveaux) == set(NiveauProgression)
    # Tentatives datées sur plusieurs jours.
    jours = {li["ts"][:10] for li in lignes}
    assert len(jours) >= 3
    # Le profil annoncé est celui que le moteur calcule effectivement.
    profil = {(li["pseudo_id"], li["competence"]): li["profil"] for li in lignes}
    assert all(diagnostiquer(h).niveau.value == profil[k] for k, h in par_comp.items())
    # Les tentatives visent des exercices et notions du référentiel, au niveau de l'élève.
    exos = {e.id: e for e in jeu["exercices"]}
    niveau_eleve = {e["pseudo_id"]: e["niveau"] for e in jeu["familles"]["eleves"]}
    for li in lignes:
        assert exos[li["exercice_id"]].notion_id == li["competence"]
        assert li["niveau"] == niveau_eleve[li["pseudo_id"]]
        assert len(li["exercice_id"]) <= 64 and len(li["competence"]) <= 64  # colonnes String(64)


# --------------------------------------------------------------------------- #
# Chargement en base
# --------------------------------------------------------------------------- #
def _bases_jetables(tmp_path: Path):
    from app.db.registre import metadatas

    fabriques = {}
    for cible in ("mika", "billing"):
        eng = create_engine(f"sqlite:///{tmp_path / (cible + '.db')}", future=True)
        for md in metadatas(cible):
            md.create_all(bind=eng)
        fabriques[cible] = sessionmaker(bind=eng, autoflush=False, future=True)
    return fabriques


def test_chargement_idempotent_en_base_jetable(lot, tmp_path, monkeypatch):
    from app.api.v1.mikamike.store import EtatCompetence, TentativeExercice
    from app.core.pseudonymisation import hmac_eleve
    from paiement_comptes.liens import LienCompteEleve
    from paiement_comptes.models_billing import Compte

    monkeypatch.delenv("MIKA_ENV", raising=False)
    dossier = lot[0]
    f = _bases_jetables(tmp_path)
    fam = s.familles_staging()
    n_tentatives = len((dossier / "utilisateurs" / "progression.jsonl").read_text("utf-8").splitlines())
    n_liens = sum(len(p["enfants"]) for p in fam["parents"])

    st1 = cli.charger(dossier, mika_sessions=f["mika"], billing_sessions=f["billing"])
    assert st1["parents_crees"] == len(fam["parents"])
    assert st1["liens_crees"] == n_liens
    assert st1["tentatives_inserees"] == n_tentatives
    st2 = cli.charger(dossier, mika_sessions=f["mika"], billing_sessions=f["billing"])
    assert (st2["parents_crees"], st2["liens_crees"], st2["tentatives_inserees"]) == (0, 0, 0)

    with f["billing"]() as b, f["mika"]() as m:
        comptes = b.execute(select(Compte)).scalars().all()
        assert len(comptes) == len(fam["parents"])
        for c in comptes:
            assert c.email.endswith("@example.com") and c.email_verifie and c.role == "parent"
            assert c.prenom is None
            assert c.mot_de_passe_hash and "synth" not in c.mot_de_passe_hash
        assert b.execute(select(func.count()).select_from(LienCompteEleve)).scalar_one() == n_liens
        h3 = hmac_eleve("eleve-synth-003")
        assert b.execute(select(func.count()).select_from(LienCompteEleve)
                         .where(LienCompteEleve.eleve_hmac == h3)).scalar_one() == 2
        assert m.execute(select(func.count()).select_from(TentativeExercice)).scalar_one() == n_tentatives
        etats = {e.etat for e in m.execute(select(EtatCompetence)).scalars()}
        assert {"MAITRISE", "A_REVOIR", "FRAGILE"} <= etats


def test_chargement_refuse_base_non_synthetique(lot, tmp_path, monkeypatch):
    from paiement_comptes import crud_billing

    monkeypatch.delenv("MIKA_ENV", raising=False)
    f = _bases_jetables(tmp_path)
    with f["billing"]() as b:
        crud_billing.creer_compte(b, "parent-reel@domaine-quelconque.test", "mot-de-passe-de-test-123")
    with pytest.raises(cli.RefusChargement) as exc:
        cli.charger(lot[0], mika_sessions=f["mika"], billing_sessions=f["billing"])
    assert exc.value.code == cli.CODE_BASE_NON_SYNTHETIQUE
    from app.api.v1.mikamike.store import TentativeExercice

    with f["mika"]() as m:
        assert m.execute(select(func.count()).select_from(TentativeExercice)).scalar_one() == 0


@pytest.mark.parametrize("alteration", ["familles", "progression", "intrus", "manquant"])
def test_chargement_refuse_utilisateurs_alteres(tmp_path, monkeypatch, alteration, capsys):
    from app.api.v1.mikamike.store import TentativeExercice

    monkeypatch.delenv("MIKA_ENV", raising=False)
    dossier = tmp_path / "lot"
    s.ecrire_lot_staging(dossier)
    util = dossier / "utilisateurs"
    if alteration == "familles":
        fam = json.loads((util / "familles.json").read_text("utf-8"))
        fam["parents"][0]["email"] = "quelqu-un@exemple-reel.test"
        (util / "familles.json").write_text(json.dumps(fam), "utf-8")
    elif alteration == "progression":
        with (util / "progression.jsonl").open("a", encoding="utf-8") as fh:
            fh.write("{}\n")
    elif alteration == "intrus":
        (util / "intrus.json").write_text("{}", "utf-8")
    else:
        (util / "progression.jsonl").unlink()
    f = _bases_jetables(tmp_path)
    with pytest.raises(cli.RefusChargement, match="donnees_utilisateurs_alterees") as exc:
        cli.charger(dossier, mika_sessions=f["mika"], billing_sessions=f["billing"])
    assert exc.value.code == 1
    with f["mika"]() as m:
        assert m.execute(select(func.count()).select_from(TentativeExercice)).scalar_one() == 0
    assert cli.main(["charger", "--dossier", str(dossier)]) == 1
    assert "refus" in capsys.readouterr().err


def test_chargement_sha_utilisateurs_epingle(lot, tmp_path, monkeypatch):
    monkeypatch.delenv("MIKA_ENV", raising=False)
    f = _bases_jetables(tmp_path)
    with pytest.raises(cli.RefusChargement, match="manifeste_utilisateurs_different"):
        cli.charger(lot[0], sha_utilisateurs="0" * 64, mika_sessions=f["mika"], billing_sessions=f["billing"])
    st = cli.charger(lot[0], sha_utilisateurs=lot[2], mika_sessions=f["mika"], billing_sessions=f["billing"])
    assert st["tentatives_inserees"] == 120


def test_manifeste_utilisateurs(lot):
    racine, sha_contenu, sha_util = lot
    brut = (racine / "utilisateurs" / "UTILISATEURS_MANIFEST.json").read_bytes()
    assert hashlib.sha256(brut).hexdigest() == sha_util
    m = json.loads(brut)
    assert m["format"] == "mika-staging-utilisateurs/1" and m["sha_lot_contenu"] == sha_contenu
    assert {f["chemin"] for f in m["fichiers"]} == {"familles.json", "progression.jsonl"}
    assert all(set(f) == {"chemin", "sha256", "taille"} for f in m["fichiers"])
    assert s.verifier_utilisateurs(racine / "utilisateurs", sha_util)["sha_lot_contenu"] == sha_contenu
    with pytest.raises(ValueError):
        s.verifier_utilisateurs(racine / "utilisateurs", "0" * 64)


# --------------------------------------------------------------------------- #
# Séparation contenu publiable / données utilisateurs
# --------------------------------------------------------------------------- #
def _sans_donnee_utilisateur(fichiers):
    assert fichiers
    for p in fichiers:
        assert p.name not in ("familles.json", "progression.jsonl", "UTILISATEURS_MANIFEST.json"), p
        texte = p.read_bytes().decode("utf-8")
        assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texte), p
        assert "eleve-synth" not in texte and "parent-synth" not in texte, p
        assert "Élève" not in texte and "pseudo_id" not in texte, p


def test_lot_de_contenu_sans_donnee_utilisateur(lot):
    racine = lot[0]
    assert sorted(p.name for p in racine.iterdir()) == ["contenu", "utilisateurs"]
    _sans_donnee_utilisateur(_fichiers(racine / "contenu"))
    manifest = json.loads((racine / "contenu" / "IMPORT_MANIFEST.json").read_text("utf-8"))
    assert not {f["chemin"] for f in manifest["fichiers"]} & {"familles.json", "progression.jsonl"}


def test_publication_depot_du_lot_de_contenu(lot, tmp_path):
    from app.curriculum.depot import DepotContenu

    contenu, sha = lot[0] / "contenu", lot[1]
    # Hors mode test : refusé (sources fictives), rien n'est copié ni activé.
    depot = DepotContenu(tmp_path / "depot")
    res = depot.publier(contenu, sha)
    assert res.statut == "REJECTED"
    assert depot.actif() is None and not (tmp_path / "depot" / "lots").exists()
    # Mode fictif explicite (API du dépôt) : publié, et la copie ne contient aucune donnée utilisateur.
    depot_test = DepotContenu(tmp_path / "depot-test", autoriser_fictif=True)
    assert depot_test.publier(contenu, sha).statut == "VALIDATED"
    assert depot_test.actif()["sha256_manifest"] == sha
    _sans_donnee_utilisateur(_fichiers(tmp_path / "depot-test" / "lots"))
    # Le lot publié reste servable (revalidé) et n'expose que des contenus.
    servi = depot_test.charger_actif()
    assert servi.statut == "VALIDATED" and len(servi.exercices) == 216


@pytest.mark.parametrize("env", ["production", "prod", "PRODUCTION"])
def test_chargement_refuse_en_production(lot, monkeypatch, env, capsys):
    monkeypatch.setenv("MIKA_ENV", env)
    assert cli.main(["charger", "--dossier", str(lot[0])]) == 2
    assert "refus" in capsys.readouterr().err
    with pytest.raises(cli.RefusChargement) as exc:
        cli.charger(lot[0])
    assert exc.value.code == 2


# --------------------------------------------------------------------------- #
# Tableau de bord parent (API) cohérent avec les tentatives chargées
# --------------------------------------------------------------------------- #
def test_dashboard_parent_coherent(client, lot, monkeypatch):
    from app.api.v1.mikamike import moteur

    monkeypatch.delenv("MIKA_ENV", raising=False)
    dossier = lot[0]
    cli.charger(dossier)  # bases configurées (MIKA_DB_URL / BILLING_DB_URL), réinitialisées par `client`
    lignes = [json.loads(li) for li in
              (dossier / "utilisateurs" / "progression.jsonl").read_text("utf-8").splitlines()]
    par_comp = s.tentatives_par_competence(lignes)
    for pseudo in ("eleve-synth-001", "eleve-synth-003", "eleve-synth-008"):
        r = client.get(f"/api/v1/parents/dashboard/{pseudo}")
        assert r.status_code == 200, r.text
        stats = r.json()["statistiques_pedagogiques"]
        miennes = [li for li in lignes if li["pseudo_id"] == pseudo]
        assert stats["exercices_tentes"] == len(miennes) > 0
        assert stats["exercices_reussis"] == sum(li["est_correct"] for li in miennes)
        comps = {li["competence"] for li in miennes}
        assert set(stats["competences"]) == comps
        for comp in comps:
            h = par_comp[(pseudo, comp)]
            attendu = moteur.etat_compatible(diagnostiquer(h), h).value
            c = stats["competences"][comp]
            assert c["etat"] == attendu, comp
            assert c["tentatives"] == len(h)
            assert c["reussites"] == sum(t.correcte for t in h)
        assert "email" not in r.text and "Élève" not in r.text
    # Un élève sans tentative chargée : tableau vide.
    vide = client.get("/api/v1/parents/dashboard/eleve-synth-999").json()["statistiques_pedagogiques"]
    assert vide["exercices_tentes"] == 0
