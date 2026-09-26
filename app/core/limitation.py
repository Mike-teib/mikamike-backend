"""
limitation.py — Limitation des tentatives (R7 / D3bis) : connexion, émission de jetons élève,
jetons invalides répétés. Sans service externe (état en mémoire du processus).

Modèle (par limiteur, par clé) :
  - fenêtre d'inactivité : les échecs sont oubliés après `fenetre_s` secondes SANS nouvel échec ;
  - seuil : à partir de `max_echecs` échecs dans la fenêtre, la clé est BLOQUÉE ;
  - backoff exponentiel : blocage = base × 2^(échecs − seuil), plafonné à `backoff_max_s` ;
  - reset : un succès (connexion réussie) efface l'historique de la clé ;
  - mémoire bornée : au plus `max_cles` clés (éviction de la plus ancienne), historique
    par clé borné ; les clés sont HACHÉES (aucune adresse e-mail en clair en mémoire).

Anti-DoS contre un autre utilisateur : la connexion n'est JAMAIS bloquée par le seul
e-mail (sinon un tiers verrouillerait le compte de la victime). Clés utilisées :
  - (IP, e-mail) : force brute ciblée depuis une source ;
  - IP seule    : pulvérisation (« credential stuffing ») depuis une source ;
  - e-mail seul : désactivé par défaut (MIKA_RL_EMAIL_GLOBAL=0) — à activer seulement avec
    un second facteur / CAPTCHA, faute de quoi il redevient un moyen de verrouiller autrui.

Limites connues (documentées, CLOUD_SECURITY_REPORT.md) : l'état est PAR PROCESSUS (N
workers ⇒ N fois la limite) et remis à zéro au redémarrage ; derrière un reverse proxy,
régler MIKA_PROXY_HOPS pour lire la bonne adresse dans X-Forwarded-For.

Configuration : MIKA_RATE_LIMIT = on (défaut) | off (refusé si MIKA_ENV=production).
"""

from __future__ import annotations

import hashlib
import math
import os
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Optional

from fastapi import HTTPException, Request, status


class ConfigLimitationInvalide(RuntimeError):
    pass


def actif() -> bool:
    brut = (os.getenv("MIKA_RATE_LIMIT") or "on").strip().lower()
    if brut not in ("on", "off"):
        raise ConfigLimitationInvalide("MIKA_RATE_LIMIT invalide (attendu : on | off)")
    if brut == "off" and os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod"):
        raise ConfigLimitationInvalide("MIKA_RATE_LIMIT=off interdit quand MIKA_ENV=production")
    return brut == "on"


@dataclass
class _Etat:
    echecs: Deque[float] = field(default_factory=deque)
    bloque_jusqua: float = 0.0


class Limiteur:
    def __init__(self, nom: str, *, max_echecs: int, fenetre_s: float, backoff_base_s: float,
                 backoff_max_s: float, max_cles: int = 100_000,
                 horloge: Callable[[], float] = time.monotonic):
        if max_echecs < 1 or fenetre_s <= 0 or backoff_base_s <= 0 or backoff_max_s < backoff_base_s:
            raise ValueError("paramètres de limitation invalides")
        self.nom = nom
        self.max_echecs = max_echecs
        self.fenetre_s = fenetre_s
        self.backoff_base_s = backoff_base_s
        self.backoff_max_s = backoff_max_s
        self.max_cles = max_cles
        self.horloge = horloge
        self._etats: "OrderedDict[str, _Etat]" = OrderedDict()
        self._verrou = threading.Lock()
        # Historique par clé borné : au-delà, le backoff est de toute façon au plafond.
        self._max_hist = max_echecs + int(math.log2(backoff_max_s / backoff_base_s)) + 2

    @staticmethod
    def _cle(brute: str) -> str:
        return hashlib.sha256(brute.encode("utf-8")).hexdigest()[:32]

    def _purger(self, e: _Etat, maintenant: float) -> None:
        # Fenêtre d'INACTIVITÉ : l'historique n'est oublié que si AUCUN échec n'est survenu
        # depuis `fenetre_s`. Une fenêtre glissante simple oubliait les premiers échecs pendant
        # que l'attaquant patientait (blocages cumulés > fenêtre) : le backoff retombait à la base.
        # L'inactivité se mesure à partir de la FIN du dernier blocage (sinon un blocage plus
        # long que la fenêtre effaçait l'historique).
        if e.echecs and max(e.echecs[-1], e.bloque_jusqua) <= maintenant - self.fenetre_s:
            e.echecs.clear()

    def attente(self, cle: str) -> int:
        """Secondes à attendre (0 = autorisé). Ne modifie pas le compteur."""
        k = self._cle(cle)
        with self._verrou:
            e = self._etats.get(k)
            if e is None:
                return 0
            maintenant = self.horloge()
            if e.bloque_jusqua > maintenant:
                return max(1, math.ceil(e.bloque_jusqua - maintenant))
            self._purger(e, maintenant)
            if not e.echecs:
                del self._etats[k]
            return 0

    def echec(self, cle: str) -> None:
        k = self._cle(cle)
        with self._verrou:
            maintenant = self.horloge()
            e = self._etats.pop(k, None) or _Etat()
            self._etats[k] = e  # fin de l'OrderedDict : clé la plus récente
            self._purger(e, maintenant)
            e.echecs.append(maintenant)
            while len(e.echecs) > self._max_hist:
                e.echecs.popleft()
            n = len(e.echecs)
            if n >= self.max_echecs:
                duree = min(self.backoff_max_s, self.backoff_base_s * (2 ** (n - self.max_echecs)))
                e.bloque_jusqua = max(e.bloque_jusqua, maintenant + duree)
            while len(self._etats) > self.max_cles:
                self._etats.popitem(last=False)

    def succes(self, cle: str) -> None:
        with self._verrou:
            self._etats.pop(self._cle(cle), None)

    def reinitialiser(self) -> None:
        with self._verrou:
            self._etats.clear()

    def __len__(self) -> int:
        return len(self._etats)


def _env_int(nom: str, defaut: int) -> int:
    try:
        return int(os.getenv(nom, str(defaut)))
    except ValueError as exc:
        raise ConfigLimitationInvalide(f"{nom} non entier") from exc


# --------------------------------------------------------------------------- #
# Limiteurs de l'application (paramètres documentés dans CLOUD_SECURITY_REPORT.md)
# --------------------------------------------------------------------------- #
CONNEXION_IP_EMAIL = Limiteur("connexion_ip_email", max_echecs=5, fenetre_s=900,
                              backoff_base_s=30, backoff_max_s=900)
CONNEXION_IP = Limiteur("connexion_ip", max_echecs=30, fenetre_s=900, backoff_base_s=60, backoff_max_s=3600)
CONNEXION_EMAIL = Limiteur("connexion_email", max_echecs=100, fenetre_s=3600,
                           backoff_base_s=60, backoff_max_s=3600)
# Émission de jetons élève : on compte TOUTES les demandes (succès compris) par compte.
JETON_COMPTE = Limiteur("jeton_eleve_compte", max_echecs=30, fenetre_s=600, backoff_base_s=60, backoff_max_s=1800)
JETON_IP = Limiteur("jeton_eleve_ip", max_echecs=60, fenetre_s=600, backoff_base_s=60, backoff_max_s=1800)
# Jetons invalides / expirés répétés (sondage de jetons) par IP.
JETON_INVALIDE_IP = Limiteur("jeton_invalide_ip", max_echecs=50, fenetre_s=300, backoff_base_s=30, backoff_max_s=900)
# Inscriptions (bcrypt coûteux + oracle d'existence d'e-mail) : toutes les demandes, par IP.
INSCRIPTION_IP = Limiteur("inscription_ip", max_echecs=20, fenetre_s=3600, backoff_base_s=60, backoff_max_s=3600)

# Invitations (D8) : émission par élève et par IP ; ÉCHECS d'acceptation par compte et par IP
# (le code fait 120 bits : ces limites rendent la force brute vaine même à grande échelle).
INVITATION_EMISSION = Limiteur("invitation_emission", max_echecs=10, fenetre_s=3600, backoff_base_s=60,
                               backoff_max_s=3600)
INVITATION_ACCEPTATION_COMPTE = Limiteur("invitation_acceptation_compte", max_echecs=5, fenetre_s=900,
                                         backoff_base_s=60, backoff_max_s=3600)
INVITATION_ACCEPTATION_IP = Limiteur("invitation_acceptation_ip", max_echecs=20, fenetre_s=900,
                                     backoff_base_s=60, backoff_max_s=3600)

TOUS = (CONNEXION_IP_EMAIL, CONNEXION_IP, CONNEXION_EMAIL, JETON_COMPTE, JETON_IP, JETON_INVALIDE_IP,
        INSCRIPTION_IP, INVITATION_EMISSION, INVITATION_ACCEPTATION_COMPTE, INVITATION_ACCEPTATION_IP)


def reinitialiser_tout() -> None:
    for lim in TOUS:
        lim.reinitialiser()


def ip_client(request: Optional[Request]) -> str:
    """Adresse du client. Derrière N proxys de confiance (MIKA_PROXY_HOPS=N), on lit la N-ième
    adresse en partant de la DROITE de X-Forwarded-For (les entrées de gauche sont forgeables)."""
    if request is None:
        return "inconnue"
    hops = _env_int("MIKA_PROXY_HOPS", 0)
    if hops > 0:
        xff = [x.strip() for x in request.headers.get("x-forwarded-for", "").split(",") if x.strip()]
        if len(xff) >= hops:
            return xff[-hops][:64]
    return (request.client.host if request.client else "inconnue")[:64]


def trop_de_tentatives(attente_s: int) -> HTTPException:
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="trop_de_tentatives",
                         headers={"Retry-After": str(attente_s)})


def exiger(*paires) -> None:
    """Refus 429 si l'une des (limiteur, clé) est bloquée. Aucun effet si MIKA_RATE_LIMIT=off."""
    try:
        if not actif():
            return
    except ConfigLimitationInvalide:
        raise HTTPException(status_code=500, detail="limitation_mal_configuree")
    attente = max((lim.attente(cle) for lim, cle in paires), default=0)
    if attente:
        raise trop_de_tentatives(attente)


def email_global_actif() -> bool:
    return _env_int("MIKA_RL_EMAIL_GLOBAL", 0) == 1


def cles_connexion(request: Optional[Request], email: str):
    ip = ip_client(request)
    em = (email or "").strip().lower()
    paires = [(CONNEXION_IP_EMAIL, f"{ip}|{em}"), (CONNEXION_IP, ip)]
    if email_global_actif():
        paires.append((CONNEXION_EMAIL, em))
    return paires


def enregistrer(paires, *, reussi: bool) -> None:
    if not actif():
        return
    for lim, cle in paires:
        if reussi:
            if lim is not CONNEXION_IP:  # un succès n'efface pas la pulvérisation depuis l'IP
                lim.succes(cle)
        else:
            lim.echec(cle)


def jeton_invalide(request: Optional[Request]) -> None:
    if actif():
        JETON_INVALIDE_IP.echec(ip_client(request))


def exiger_jeton_non_sonde(request: Optional[Request]) -> None:
    exiger((JETON_INVALIDE_IP, ip_client(request)))


def compter(paires) -> None:
    """Événement compté quel qu'en soit le résultat (quota d'émission de jetons)."""
    if not actif():
        return
    for lim, cle in paires:
        lim.echec(cle)

