"""
smoke.py — Smoke tests d'un déploiement (staging / production), bibliothèque standard seulement.

    python -m tools.smoke --url https://<hôte>                 # LECTURE SEULE (sûr en production)
    python -m tools.smoke --url https://<hôte> --ecriture --email <boîte de test contrôlée>
    python -m tools.smoke --url https://<hôte> --mode-auth enforce

Lecture seule : santé, en-têtes de sécurité, 422 sans écho de la saisie, champ inconnu refusé,
routes protégées fermées sans jeton (si enforce), route inconnue ⇒ 404 sans trace.
`--ecriture` (staging uniquement) : inscription d'une adresse de test, connexion, invitation
refusée tant que l'adresse n'est pas vérifiée, séance élève refusée sans lien. Aucun secret en
argument ; aucune donnée d'élève réelle. Code retour : 0 tout vert, 1 au moins un échec.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple

MOT_DE_PASSE_TEST_LONGUEUR = 24


def _appel(base: str, methode: str, chemin: str, corps: Optional[dict] = None,
           jeton: Optional[str] = None, delai: float = 10.0) -> Tuple[int, Dict[str, str], str]:
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    req = urllib.request.Request(base.rstrip("/") + chemin, data=donnees, method=methode)  # noqa: S310
    if donnees is not None:
        req.add_header("Content-Type", "application/json")
    if jeton:
        req.add_header("Authorization", f"Bearer {jeton}")
    try:
        # URL fournie par l'opérateur (http/https attendus) : B310 accepté.
        with urllib.request.urlopen(req, timeout=delai) as r:  # nosec B310
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace")


def verifications_lecture(base: str, mode_auth: str) -> List[Tuple[str, bool, str]]:
    out: List[Tuple[str, bool, str]] = []

    def ok(nom, cond, detail=""):
        out.append((nom, bool(cond), detail))

    code, entetes, texte = _appel(base, "GET", "/healthz")
    ok("sante_200", code == 200 and '"ok"' in texte, f"{code}")
    ok("entete_nosniff", entetes.get("x-content-type-options") == "nosniff")
    ok("entete_frame", entetes.get("x-frame-options", "").upper() in ("DENY", "SAMEORIGIN"),
       entetes.get("x-frame-options", ""))
    sonde = "sonde-" + secrets.token_hex(4)
    code, _, texte = _appel(base, "POST", "/api/v1/comptes/connexion", {"email": "pas-un-email", "mot_de_passe": sonde})
    ok("422_sans_echo", code == 422 and sonde not in texte, f"{code}")
    code, _, _ = _appel(base, "POST", "/api/v1/comptes/connexion",
                        {"email": "x@example.com", "mot_de_passe": "m", "role": "admin"})
    ok("champ_inconnu_422", code == 422, f"{code}")
    code, _, texte = _appel(base, "GET", "/api/v1/route-inexistante-" + secrets.token_hex(3))
    ok("404_sans_trace", code == 404 and "Traceback" not in texte, f"{code}")
    if mode_auth == "enforce":
        for methode, chemin, corps in (("GET", "/api/v1/parents/dashboard/eleve-smoke", None),
                                       ("GET", "/api/v1/rgpd/export/eleve-smoke", None),
                                       ("POST", "/api/v1/session/nouvelle", {"user_id": "eleve-smoke"})):
            code, _, _ = _appel(base, methode, chemin, corps)
            ok(f"ferme_sans_jeton {chemin}", code == 401, f"{code}")
    return out


def verifications_ecriture(base: str, email: str) -> List[Tuple[str, bool, str]]:
    out: List[Tuple[str, bool, str]] = []

    def ok(nom, cond, detail=""):
        out.append((nom, bool(cond), detail))

    mdp = secrets.token_urlsafe(MOT_DE_PASSE_TEST_LONGUEUR)  # jamais affiché
    code, _, texte = _appel(base, "POST", "/api/v1/comptes/inscription", {"email": email, "mot_de_passe": mdp})
    ok("inscription_201", code == 201, f"{code}")
    code, _, texte = _appel(base, "POST", "/api/v1/comptes/connexion", {"email": email, "mot_de_passe": mdp})
    ok("connexion_200", code == 200, f"{code}")
    jeton = json.loads(texte).get("token") if code == 200 else None
    if jeton:
        code, _, texte = _appel(base, "POST", "/api/v1/liens/accepter",
                                {"code": "AAAA-AAAA-AAAA-AAAA-AAAA-AAAA", "confirmation": True}, jeton)
        ok("invitation_refusee_email_non_verifie", code == 403 and "email_non_verifie" in texte, f"{code}")
        code, _, _ = _appel(base, "POST", "/api/v1/auth/eleve/jeton", {"student_pseudo_id": "eleve-smoke"}, jeton)
        ok("jeton_eleve_refuse_sans_lien", code == 403, f"{code}")
        code, _, _ = _appel(base, "GET", "/api/v1/comptes/verification-email", jeton=jeton)
        ok("etat_verification_200", code == 200, f"{code}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tools.smoke")
    ap.add_argument("--url", required=True)
    ap.add_argument("--mode-auth", choices=("off", "observe", "enforce"), default="enforce")
    ap.add_argument("--ecriture", action="store_true", help="staging uniquement : crée un compte de test")
    ap.add_argument("--email", help="adresse de TEST contrôlée par l'équipe (requis avec --ecriture)")
    try:
        args = ap.parse_args(argv)
    except SystemExit:
        return 2
    if args.ecriture and not args.email:
        print("--ecriture exige --email (boîte de test)", file=sys.stderr)
        return 2
    try:
        res = verifications_lecture(args.url, args.mode_auth)
        if args.ecriture:
            res += verifications_ecriture(args.url, args.email)
    except OSError as e:
        print(f"ECHEC connexion : {type(e).__name__}", file=sys.stderr)
        return 1
    for nom, bon, detail in res:
        print(f"{'OK ' if bon else 'KO '} {nom} {detail}".rstrip())
    echecs = [n for n, b, _ in res if not b]
    print(f"{len(res) - len(echecs)}/{len(res)} vérifications vertes")
    return 1 if echecs else 0


if __name__ == "__main__":
    raise SystemExit(main())
