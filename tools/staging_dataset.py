#!/usr/bin/env python3
"""
staging_dataset.py — Jeu de données SYNTHÉTIQUE de staging (cf. STAGING_DATASET.md).

  python -m tools.staging_dataset generer --sortie <dossier> [--graine G]
      écrit <dossier>/contenu (lot d'import v2 publiable, sans donnée utilisateur) et
      <dossier>/utilisateurs (familles + progression fictives) ; affiche les deux SHA.
  python -m tools.staging_dataset verifier --dossier <d> --sha <sha contenu> [--rentree 2026]
      import strict épinglé de <d>/contenu (autoriser_fictif) + intégrité + quiz complémentaires.
  python -m tools.staging_dataset charger --dossier <d> [--sha-utilisateurs <sha>]
      vérifie les empreintes de <d>/utilisateurs (refus si altéré, code 1) puis insère familles (comptes parents @example.com, e-mail vérifié, mot de passe aléatoire haché
      JAMAIS affiché, liens compte ↔ élève) et tentatives (+ états de maîtrise recalculés) dans
      les bases désignées par MIKA_DB_URL / BILLING_DB_URL. Idempotent.

Garde-fous du chargement :
  - MIKA_ENV = production | prod                  ⇒ refus, code 2 (aucune connexion ouverte) ;
  - base billing contenant un compte hors @example.com ⇒ refus, code 3 (base non synthétique) ;
  - fichiers du lot différents du manifest, ou données non synthétiques ⇒ refus, code 1.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import secrets
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

CODE_PRODUCTION = 2
CODE_BASE_NON_SYNTHETIQUE = 3
_PSEUDO = re.compile(r"^eleve-synth-\d{3}$")
_EMAIL = re.compile(r"^parent-synth-\d{3}@example\.com$")


class RefusChargement(RuntimeError):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def en_production() -> bool:
    return os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod")


# --------------------------------------------------------------------------- #
# generer / verifier
# --------------------------------------------------------------------------- #
def _cmd_generer(args) -> int:
    from app.curriculum import staging_synthetique as s

    sortie = Path(args.sortie)
    try:
        lot = s.ecrire_lot_staging(sortie, args.graine)
    except FileExistsError as exc:
        print(f"erreur: {exc}", file=sys.stderr)
        return 1
    ref = s.referentiel_staging(args.graine)
    ex, qz = s.exercices_staging(ref, args.graine), s.quiz_staging(ref, args.graine)
    qc = s.quiz_complementaires_staging(ref, args.graine)
    fam = s.familles_staging()
    hist = s.historiques_staging(ref, fam, args.graine)
    print(f"lot: {sortie}")
    print(f"contenu: {sortie / s.DOSSIER_CONTENU}")
    print(f"sha256_manifest_contenu: {lot.sha_contenu}   (à épingler : verifier --sha)")
    print(f"utilisateurs: {sortie / s.DOSSIER_UTILISATEURS}")
    print(f"sha256_manifest_utilisateurs: {lot.sha_utilisateurs}")
    print(f"programmes: {len(ref.programmes)} · chapitres: {len(ref.chapitres)} · notions: {len(ref.notions)}"
          f" · exercices: {len(ex)} · qcm: {len(qz)} · quiz complémentaires: {len(qc)}")
    print(f"familles: {len(fam['parents'])} parents · {len(fam['eleves'])} élèves · tentatives: {len(hist)}")
    print(_tableau(s.statistiques(ref, ex, qz, qc), s.CLES_STATS))
    return 0


def _tableau(stats: Dict[str, Dict[str, Dict[str, int]]], cles) -> str:
    lignes = [f"{'matière':<26}{'niveau':<8}" + "".join(f"{k:>12}" for k in cles)]
    for m in sorted(stats):
        for niv in sorted(stats[m]):
            lignes.append(f"{m:<26}{niv:<8}" + "".join(f"{stats[m][niv][k]:>12}" for k in cles))
    return "\n".join(lignes)


def verifier_lot(dossier: Path, sha: str, rentree: Optional[int] = 2026) -> Dict[str, Any]:
    """`dossier` = racine générée (son sous-dossier `contenu/` est importé) ou le lot de contenu."""
    from app.curriculum.importers import importer
    from app.curriculum.quiz_types import valider
    from app.curriculum.staging_synthetique import DOSSIER_CONTENU, lire_quiz_complementaires

    if (dossier / DOSSIER_CONTENU).is_dir():
        dossier = dossier / DOSSIER_CONTENU
    res = importer(dossier, sha256_manifest=sha, rentree=rentree, autoriser_fictif=True)
    rapport: Dict[str, Any] = {"statut": res.statut, "anomalies": [tuple(a) for a in res.anomalies],
                               "fichiers_en_echec": {k: v for k, v in res.fichiers.items() if v["etat"] != "DONE"}}
    if res.statut == "FAILED":
        return rapport
    idx = res.referentiel.index()
    compl = lire_quiz_complementaires(dossier / "quiz_complementaires.jsonl")
    rapport.update({
        "notions": len(res.referentiel.notions), "generables": len(res.integrite.generables),
        "exercices": len(res.exercices), "qcm": len(res.quiz), "quiz_complementaires": len(compl),
        "anomalies_quiz_complementaires": [(q.id, r) for q in compl
                                           for r in valider(q, idx, autoriser_fictif=True)],
        "rattachements": sorted(set(res.rattachements.values())),
    })
    return rapport


def _cmd_verifier(args) -> int:
    rap = verifier_lot(Path(args.dossier), args.sha, args.rentree)
    print(f"import: {rap['statut']}")
    for chemin, info in rap["fichiers_en_echec"].items():
        print(f"  FAILED {chemin}: {info.get('raison', '')}")
    if rap["statut"] == "FAILED":
        return 1
    print(f"anomalies: {len(rap['anomalies'])} · notions générables: {rap['generables']}/{rap['notions']}")
    print(f"exercices: {rap['exercices']} · qcm: {rap['qcm']} · quiz complémentaires: "
          f"{rap['quiz_complementaires']} (anomalies: {len(rap['anomalies_quiz_complementaires'])})")
    print(f"chapitrage: {', '.join(rap['rattachements'])}")
    for a in rap["anomalies"][:20]:
        print(f"  {a[0]} {a[1]} {a[2] if len(a) > 2 else ''}")
    ok = rap["statut"] == "VALIDATED" and not rap["anomalies_quiz_complementaires"] \
        and rap["generables"] == rap["notions"]
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# charger
# --------------------------------------------------------------------------- #
def _lire_lot(dossier: Path, sha_utilisateurs: Optional[str] = None) -> tuple[dict, List[dict]]:
    """Lit `dossier/utilisateurs/` après contrôle de ses empreintes (refus si altéré)."""
    from app.curriculum.staging_synthetique import DOSSIER_UTILISATEURS, verifier_utilisateurs

    util = dossier / DOSSIER_UTILISATEURS
    try:
        verifier_utilisateurs(util, sha_utilisateurs)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RefusChargement(f"donnees_utilisateurs_alterees_ou_absentes:{exc}") from exc
    familles = json.loads((util / "familles.json").read_text("utf-8"))
    lignes = [json.loads(li) for li in (util / "progression.jsonl").read_text("utf-8").splitlines() if li.strip()]
    # Données strictement synthétiques, sinon refus (jamais de chargement de données réelles).
    pseudos = {e["pseudo_id"] for e in familles["eleves"]}
    if not all(_PSEUDO.fullmatch(p) for p in pseudos):
        raise RefusChargement("pseudo_id_non_synthetique")
    if not all(_EMAIL.fullmatch(p["email"]) for p in familles["parents"]):
        raise RefusChargement("email_non_synthetique")
    if any(li["pseudo_id"] not in pseudos for li in lignes):
        raise RefusChargement("tentative_d_un_eleve_inconnu")
    return familles, lignes


def _ts_naif_utc(iso: str) -> _dt.datetime:
    return _dt.datetime.fromisoformat(iso).astimezone(_dt.timezone.utc).replace(tzinfo=None)


def charger(dossier: Path, *, sha_utilisateurs: Optional[str] = None, mika_sessions: Optional[Callable] = None,
            billing_sessions: Optional[Callable] = None) -> Dict[str, int]:
    """Charge familles + tentatives. Idempotent : relancer n'insère rien de nouveau."""
    if en_production():
        raise RefusChargement("MIKA_ENV=production : chargement du jeu synthétique interdit", CODE_PRODUCTION)
    familles, lignes = _lire_lot(Path(dossier), sha_utilisateurs)

    from sqlalchemy import func, not_, select

    from app.api.v1.mikamike import crud, moteur
    from app.api.v1.mikamike.store import TentativeExercice
    from app.core.pseudonymisation import hmac_eleve
    from paiement_comptes import crud_billing, liens
    from paiement_comptes.models_billing import Compte

    if mika_sessions is None:
        from app.api.v1.mikamike.store import SessionLocal as mika_sessions
    if billing_sessions is None:
        from paiement_comptes.database import SessionLocal as billing_sessions

    stats = {"parents_crees": 0, "liens_crees": 0, "tentatives_inserees": 0, "etats_recalcules": 0}
    hmacs = {e["pseudo_id"]: hmac_eleve(e["pseudo_id"]) for e in familles["eleves"]}

    bdb = billing_sessions()
    try:
        etrangers = bdb.execute(select(func.count()).select_from(Compte)
                                .where(not_(Compte.email.like("%@example.com")))).scalar_one()
        if etrangers:
            raise RefusChargement(f"base_billing_non_synthetique:{etrangers}_compte(s)_hors_example.com",
                                  CODE_BASE_NON_SYNTHETIQUE)
        for p in familles["parents"]:
            compte = crud_billing.get_compte_par_email(bdb, p["email"])
            if compte is None:
                # Mot de passe aléatoire, haché, jamais affiché ni conservé : connexion via
                # « mot de passe oublié » seulement (comptes de démonstration).
                compte = crud_billing.creer_compte(bdb, p["email"], secrets.token_urlsafe(32), role="parent")
                stats["parents_crees"] += 1
            if not compte.email_verifie:
                compte.email_verifie = True
                bdb.commit()
            for pseudo in p["enfants"]:
                if liens.relation(bdb, compte.id, hmacs[pseudo]) is None:
                    liens.lier(bdb, compte.id, hmacs[pseudo], "parent")
                    stats["liens_crees"] += 1
    finally:
        bdb.close()

    mdb = mika_sessions()
    try:
        existantes = {
            (h, exo, comp, ts, bool(ok), bool(aide))
            for h, exo, comp, ts, ok, aide in mdb.execute(
                select(TentativeExercice.eleve_hmac, TentativeExercice.exercice_id, TentativeExercice.competence,
                       TentativeExercice.ts, TentativeExercice.est_correct, TentativeExercice.avec_aide)
                .where(TentativeExercice.eleve_hmac.in_(list(hmacs.values()))))
        }
        for li in lignes:
            h, ts = hmacs[li["pseudo_id"]], _ts_naif_utc(li["ts"])
            cle = (h, li["exercice_id"], li["competence"], ts, bool(li["est_correct"]), bool(li["avec_aide"]))
            if cle in existantes:
                continue
            mdb.add(TentativeExercice(eleve_hmac=h, exercice_id=li["exercice_id"], matiere=li["matiere"],
                                      niveau=li["niveau"], competence=li["competence"],
                                      est_correct=bool(li["est_correct"]), avec_aide=bool(li["avec_aide"]), ts=ts))
            existantes.add(cle)
            stats["tentatives_inserees"] += 1
        mdb.commit()
        # État de maîtrise recalculé par le moteur sur l'historique (jamais déclaré par le lot).
        for pseudo, comp in sorted({(li["pseudo_id"], li["competence"]) for li in lignes}):
            etat, _diag = moteur.evaluer(mdb, hmacs[pseudo], comp)
            crud.upsert_etat(mdb, hmacs[pseudo], comp, etat.value)
            stats["etats_recalcules"] += 1
    finally:
        mdb.close()
    return stats


def _cmd_charger(args) -> int:
    from sqlalchemy.exc import OperationalError, ProgrammingError

    try:
        stats = charger(Path(args.dossier), sha_utilisateurs=args.sha_utilisateurs)
    except RefusChargement as exc:
        print(f"refus: {exc}", file=sys.stderr)
        return exc.code
    except (OperationalError, ProgrammingError) as exc:
        print(f"erreur: base inaccessible ou schéma absent ({type(exc).__name__}) ; "
              "appliquer d'abord `python -m tools.db upgrade`", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"erreur: {exc}", file=sys.stderr)
        return 1
    print(" · ".join(f"{k}: {v}" for k, v in stats.items()))
    return 0


def main(argv=None) -> int:
    from app.curriculum.staging_synthetique import GRAINE_DEFAUT

    ap = argparse.ArgumentParser(prog="tools.staging_dataset")
    sous = ap.add_subparsers(dest="cmd", required=True)
    g = sous.add_parser("generer")
    g.add_argument("--sortie", required=True)
    g.add_argument("--graine", default=GRAINE_DEFAUT)
    v = sous.add_parser("verifier")
    v.add_argument("--dossier", required=True)
    v.add_argument("--sha", required=True)
    v.add_argument("--rentree", type=int, default=2026)
    c = sous.add_parser("charger")
    c.add_argument("--dossier", required=True)
    c.add_argument("--sha-utilisateurs", default=None,
                   help="SHA épinglé de utilisateurs/UTILISATEURS_MANIFEST.json (recommandé)")
    args = ap.parse_args(argv)
    if args.cmd == "charger" and en_production():
        # Refus AVANT tout import applicatif ou connexion à une base.
        print("refus: MIKA_ENV=production : chargement du jeu synthétique interdit", file=sys.stderr)
        return CODE_PRODUCTION
    return {"generer": _cmd_generer, "verifier": _cmd_verifier, "charger": _cmd_charger}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
