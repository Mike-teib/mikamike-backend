#!/usr/bin/env python3
"""
contrat_front.py — Contrat front EXÉCUTABLE (FRONT_IMPLEMENTATION_PACK.md).

Joue, dans le processus (TestClient, bases jetables, courriel FAUX, contenu FICTIF), le parcours
complet que le front doit implémenter, et enregistre pour chaque appel : méthode, chemin
(gabarit), en-tête d'auth attendu, corps envoyé et FORME de la réponse (types, valeurs
d'énumération conservées). Résultat : `contrat_front/contrat.json`, déterministe.

  python -m tools.contrat_front --ecrire      régénère le contrat
  python -m tools.contrat_front --verifier    échoue (code 1) si l'API a dérivé du contrat commité

Le test `tests_cloud/test_contrat_front.py` exécute `--verifier` : toute évolution de l'API qui
casse le contrat front est détectée en CI. `contrat_front/verifier_contrat.mjs` rejoue la partie
publique du contrat contre un serveur réel (Node ≥ 18, sans dépendance).
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

RACINE = Path(__file__).resolve().parents[1]
FICHIER = RACINE / "contrat_front" / "contrat.json"

# Clés dont la VALEUR fait partie du contrat (énumérations, codes d'erreur) : conservée telle quelle.
VALEURS_CONTRACTUELLES = {
    "detail", "statut", "relation", "typ", "token_type", "contract_version", "action", "derniere_action",
    "role", "usage_unique", "niveau_estime", "code",
}


def forme(v: Any, cle: Optional[str] = None) -> Any:
    if cle in VALEURS_CONTRACTUELLES and (isinstance(v, bool) or (
            isinstance(v, str) and re.fullmatch(r"[a-z][a-z0-9_:/.\-]{0,59}|[A-Z][A-Z_]{2,40}", v))):
        return v  # énumération / code d'erreur (jamais une valeur aléatoire comme un code d'invitation)
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, int):
        return "integer"
    if isinstance(v, float):
        return "number"
    if v is None:
        return "null"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return [forme(v[0])] if v else []
    if isinstance(v, dict):
        return {k: forme(x, k) for k, x in sorted(v.items())}
    return type(v).__name__


def _gabarit(chemin: str, remplacements: Dict[str, str]) -> str:
    for valeur, nom in remplacements.items():
        chemin = chemin.replace(valeur, "{" + nom + "}")
    return re.sub(r"\?.*$", "", chemin)


def _corps_normalise(corps: Any, remplacements: Dict[str, str]) -> Any:
    if isinstance(corps, dict):
        return {k: _corps_normalise(v, remplacements) for k, v in sorted(corps.items())}
    if isinstance(corps, str):
        for valeur, nom in remplacements.items():
            if valeur and valeur in corps:
                return "<" + nom + ">"
        return corps
    return corps


def generer() -> Dict[str, Any]:
    tmp = tempfile.mkdtemp(prefix="contrat-front-")
    os.environ.update({
        "MIKA_DB_URL": f"sqlite:///{tmp}/mika.db", "BILLING_DB_URL": f"sqlite:///{tmp}/billing.db",
        "MIKA_JWT_SECRET": os.environ.get("MIKA_JWT_SECRET", "test-jwt-secret-not-for-prod-0123456789"),
        "MIKA_PSEUDO_SECRET": os.environ.get("MIKA_PSEUDO_SECRET", "test-pseudo-secret-not-for-prod-0123456789"),
        "MIKA_DB_INIT": "none", "MIKA_AUTH_MODE": "enforce", "MIKA_RATE_LIMIT": "on",
        "MIKA_EMAIL_TRANSPORT": "faux", "MIKA_ENV": "",
    })
    import bcrypt
    from fastapi.testclient import TestClient

    from app.api.v1.mikamike import crud
    from app.api.v1.mikamike.store import SessionLocal
    from app.api.v1.tutorat import contenu
    from app.core import limitation
    from app.core.courriel import boite_de_test
    from app.core.pseudonymisation import hmac_eleve
    from app.curriculum.exercices import Exercice
    from app.curriculum.fixtures import referentiel_fictif
    from app.curriculum.pedagogie.tuteur import PlanGuidage
    from app.db.registre import creer_tables_pour_tests
    from main import create_app
    from paiement_comptes import crud_billing, liens
    from paiement_comptes.database import SessionLocal as BillingSession

    creer_tables_pour_tests(reinitialiser=True)
    limitation.reinitialiser_tout()
    boite_de_test().vider()
    gensalt = bcrypt.gensalt
    crud_billing._bcrypt.gensalt = lambda *a, **k: gensalt(4)  # coût minimal : comptes FICTIFS

    n = referentiel_fictif().index().notions["notion:fictif:fractions-decimales"]
    exo = Exercice(id="exo:fictif:contrat", notion_id=n.id, matiere=n.matiere, niveau=n.niveau,
                   programme_id=n.programme_id, chapitre_id=n.chapitre_id, difficulte=3,
                   objectif_pedagogique="[FICTIF] fraction décimale", prerequis=("notion:fictif:comparer-fractions",),
                   enonce="Écris 7/10 sous forme décimale.", reponse_attendue="0,7",
                   type_verification="maths_symbolique", indices=("Lis la fraction à voix haute.",),
                   source_sha256_extrait=n.preuve.sha256_extrait)
    plan = PlanGuidage(questions_intermediaires=("Que représente le 10 ?",),
                       question_comprehension="Et 9/10 ?", reponse_comprehension="0,9",
                       correction_commentee="7/10 = 0,7.")
    contenu.definir_catalogue(contenu.CatalogueTutorat(referentiel_fictif(), [exo], {exo.id: plan},
                                                       autoriser_fictif=True))
    appels: List[Dict[str, Any]] = []
    rempl: Dict[str, str] = {}
    app = create_app()

    with TestClient(app) as c:
        def appel(nom, methode, chemin, *, auth=None, corps=None, attendu):
            h = {"Authorization": f"Bearer {auth[1]}"} if auth else {}
            r = c.request(methode, chemin, json=corps, headers=h)
            assert r.status_code == attendu, (nom, r.status_code, r.text)
            try:
                rep = r.json() if r.content else None
            except ValueError:
                rep = r.text[:40]
            appels.append({
                "nom": nom, "methode": methode, "chemin": _gabarit(chemin, rempl),
                "auth": auth[0] if auth else None,
                "corps": _corps_normalise(corps, rempl) if corps is not None else None,
                "statut_http": attendu, "reponse": forme(rep),
                **({"retry_after": "Retry-After" in r.headers} if attendu == 429 else {}),
            })
            return rep

        EL, EM1, EM2, MDP = "eleve-contrat-01", "parent1@example.com", "parent2@example.com", "motdepasse-contrat-01"
        rempl.update({EL: "student_pseudo_id"})
        # --- comptes, vérification d'adresse
        t1 = appel("inscription", "POST", "/api/v1/comptes/inscription",
                   corps={"email": EM1, "mot_de_passe": MDP, "prenom": "Prénom", "role": "parent"}, attendu=201)["token"]
        appel("inscription_email_deja_utilise", "POST", "/api/v1/comptes/inscription",
              corps={"email": EM1, "mot_de_passe": MDP}, attendu=400)
        appel("inscription_invalide", "POST", "/api/v1/comptes/inscription",
              corps={"email": "pas-un-email", "mot_de_passe": "court"}, attendu=422)
        t1 = appel("connexion", "POST", "/api/v1/comptes/connexion", corps={"email": EM1, "mot_de_passe": MDP},
                   attendu=200)["token"]
        appel("connexion_refusee", "POST", "/api/v1/comptes/connexion",
              corps={"email": EM1, "mot_de_passe": "mauvais-mdp-00"}, attendu=401)
        appel("moi", "GET", "/api/v1/comptes/moi", auth=("compte", t1), attendu=200)
        appel("moi_sans_jeton", "GET", "/api/v1/comptes/moi", attendu=401)
        appel("etat_verification_email", "GET", "/api/v1/comptes/verification-email", auth=("compte", t1), attendu=200)
        appel("demander_verification_email", "POST", "/api/v1/comptes/verification-email", auth=("compte", t1),
              attendu=202)
        jeton = boite_de_test().derniers(EM1)[-1].metadonnees["jeton"]
        rempl[jeton] = "jeton_recu_par_courriel"
        appel("confirmer_email_invalide", "POST", "/api/v1/comptes/verification-email/confirmer",
              corps={"jeton": "jeton-inconnu"}, attendu=400)
        appel("confirmer_email", "POST", "/api/v1/comptes/verification-email/confirmer", corps={"jeton": jeton},
              attendu=200)
        # --- rattachement (premier code : opérateur)
        appel("jeton_eleve_sans_lien", "POST", "/api/v1/auth/eleve/jeton", auth=("compte", t1),
              corps={"student_pseudo_id": EL}, attendu=403)
        db = BillingSession()
        code, _ = liens.creer_invitation(db, EL, hmac_eleve(EL), emis_par="operateur")
        db.close()
        rempl[code] = "code_invitation"
        appel("accepter_invitation_sans_confirmation", "POST", "/api/v1/liens/accepter", auth=("compte", t1),
              corps={"code": code, "confirmation": False}, attendu=422)
        appel("accepter_invitation_code_invalide", "POST", "/api/v1/liens/accepter", auth=("compte", t1),
              corps={"code": "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", "confirmation": True}, attendu=400)
        appel("accepter_invitation", "POST", "/api/v1/liens/accepter", auth=("compte", t1),
              corps={"code": code, "confirmation": True}, attendu=201)
        appel("accepter_invitation_deja_utilisee", "POST", "/api/v1/liens/accepter", auth=("compte", t1),
              corps={"code": code, "confirmation": True}, attendu=400)
        je = appel("jeton_eleve", "POST", "/api/v1/auth/eleve/jeton", auth=("compte", t1),
                   corps={"student_pseudo_id": EL}, attendu=200)["token"]
        # --- séance, exercices
        sid = appel("nouvelle_seance", "POST", "/api/v1/session/nouvelle", auth=("eleve", je),
                    corps={"user_id": EL}, attendu=201)["session_id"]
        rempl[sid] = "session_id"
        appel("seance_inconnue", "POST", "/api/v1/session/heartbeat", auth=("eleve", je),
              corps={"session_id": "identifiant-client", "user_id": EL}, attendu=404)
        appel("heartbeat", "POST", "/api/v1/session/heartbeat", auth=("eleve", je),
              corps={"session_id": sid, "user_id": EL}, attendu=200)
        appel("sauver_etat", "POST", "/api/v1/session/save-state", auth=("eleve", je),
              corps={"session_id": sid, "user_id": EL, "state_data": {"ardoise": "x"}}, attendu=200)
        appel("reconnexion", "POST", "/api/v1/session/reconnect", auth=("eleve", je),
              corps={"session_id": sid, "user_id": EL}, attendu=200)
        appel("soumettre_exercice", "POST", "/api/v1/exercices/soumettre", auth=("eleve", je),
              corps={"exercice_id": "exo-maths-calcul-litteral-1", "student_pseudo_id": EL, "reponse": "5*x"},
              attendu=200)
        appel("soumettre_sans_jeton", "POST", "/api/v1/exercices/soumettre",
              corps={"exercice_id": "exo-maths-calcul-litteral-1", "student_pseudo_id": EL, "reponse": "5x"},
              attendu=401)
        appel("prochaine_etape", "GET", f"/api/v1/parcours/prochaine-etape?student_id={EL}", auth=("eleve", je),
              attendu=200)
        # --- tuteur Mika
        s = SessionLocal()
        crud.upsert_etat(s, hmac_eleve(EL), "notion:fictif:comparer-fractions", "ACQUIS_AUTONOME")
        s.close()
        t = appel("tuteur_start", "POST", "/api/v1/mika/session/start", auth=("eleve", je),
                  corps={"student_pseudo_id": EL, "requete_id": "req-1", "exercice_id": exo.id}, attendu=201)
        rempl[t["tutorat_id"]] = "tutorat_id"
        appel("tuteur_start_rejeu", "POST", "/api/v1/mika/session/start", auth=("eleve", je),
              corps={"student_pseudo_id": EL, "requete_id": "req-1", "exercice_id": exo.id}, attendu=200)
        base = {"student_pseudo_id": EL, "tutorat_id": t["tutorat_id"]}
        t2 = appel("tuteur_help", "POST", "/api/v1/mika/session/help", auth=("eleve", je),
                   corps={**base, "requete_id": "req-2", "version": 1}, attendu=200)
        appel("tuteur_version_perimee", "POST", "/api/v1/mika/session/answer", auth=("eleve", je),
              corps={**base, "requete_id": "req-3", "version": 1, "reponse": "0,7"}, attendu=409)
        t3 = appel("tuteur_answer", "POST", "/api/v1/mika/session/answer", auth=("eleve", je),
                   corps={**base, "requete_id": "req-4", "version": t2["version"], "reponse": "0,7"}, attendu=200)
        appel("tuteur_comprehension", "POST", "/api/v1/mika/session/comprehension", auth=("eleve", je),
              corps={**base, "requete_id": "req-5", "version": t3["version"], "reponse": "0,9"}, attendu=200)
        appel("tuteur_etat", "GET", f"/api/v1/mika/session/{t['tutorat_id']}?student_id={EL}", auth=("eleve", je),
              attendu=200)
        # --- invitation d'un second parent par l'enfant
        code2 = appel("emettre_invitation", "POST", "/api/v1/liens/invitations", auth=("eleve", je),
                      corps={"student_pseudo_id": EL}, attendu=201)["code"]
        rempl[code2] = "code_invitation"
        appel("inscription_parent2", "POST", "/api/v1/comptes/inscription",
              corps={"email": EM2, "mot_de_passe": MDP}, attendu=201)
        t2p = c.post("/api/v1/comptes/connexion", json={"email": EM2, "mot_de_passe": MDP}).json()["token"]
        appel("accepter_invitation_email_non_verifie", "POST", "/api/v1/liens/accepter", auth=("compte", t2p),
              corps={"code": code2, "confirmation": True}, attendu=403)
        # --- parent : tableau de bord, RGPD
        appel("dashboard_parent", "GET", f"/api/v1/parents/dashboard/{EL}", auth=("compte", t1), attendu=200)
        appel("dashboard_non_lie", "GET", f"/api/v1/parents/dashboard/{EL}", auth=("compte", t2p), attendu=403)
        appel("export_rgpd_eleve", "GET", f"/api/v1/rgpd/export/{EL}", auth=("compte", t1), attendu=200)
        appel("export_compte", "GET", "/api/v1/comptes/moi/export", auth=("compte", t1), attendu=200)
        appel("effacement_par_eleve_refuse", "DELETE", f"/api/v1/rgpd/effacer/{EL}", auth=("eleve", je), attendu=403)
        appel("effacement_rgpd", "DELETE", f"/api/v1/rgpd/effacer/{EL}", auth=("compte", t1), attendu=200)
        appel("jeton_eleve_revoque", "POST", "/api/v1/session/heartbeat", auth=("eleve", je),
              corps={"session_id": sid, "user_id": EL}, attendu=401)
        # --- compte : mot de passe, déconnexion
        nouveau = appel("changer_mot_de_passe", "POST", "/api/v1/comptes/mot-de-passe", auth=("compte", t1),
                        corps={"ancien": MDP, "nouveau": "nouveau-mdp-contrat"}, attendu=200)["token"]
        appel("ancien_jeton_revoque", "GET", "/api/v1/comptes/moi", auth=("compte", t1), attendu=401)
        appel("deconnexion", "POST", "/api/v1/comptes/deconnexion", auth=("compte", nouveau), attendu=204)
        # --- limitation
        for _ in range(5):
            c.post("/api/v1/comptes/connexion", json={"email": EM2, "mot_de_passe": "mauvais-mdp-00"})
        appel("trop_de_tentatives", "POST", "/api/v1/comptes/connexion",
              corps={"email": EM2, "mot_de_passe": "mauvais-mdp-00"}, attendu=429)
    contenu.definir_catalogue(None)
    return {"version_contrat": 1, "base": "/api/v1",
            "note": "Généré par tools/contrat_front.py — formes normalisées ; ne pas éditer à la main.",
            "appels": appels}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    contrat = generer()
    texte = json.dumps(contrat, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if argv[:1] == ["--ecrire"]:
        FICHIER.parent.mkdir(exist_ok=True)
        FICHIER.write_text(texte, encoding="utf-8")
        print(f"{len(contrat['appels'])} appels écrits dans {FICHIER.relative_to(RACINE)}")
        return 0
    if argv[:1] == ["--verifier"]:
        actuel = FICHIER.read_text(encoding="utf-8") if FICHIER.exists() else ""
        if actuel != texte:
            print("DÉRIVE : l'API ne correspond plus à contrat_front/contrat.json "
                  "(régénérer avec --ecrire si l'évolution est voulue, et prévenir le front)")
            return 1
        print(f"contrat front conforme ({len(contrat['appels'])} appels)")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
