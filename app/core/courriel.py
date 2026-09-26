"""
courriel.py — Envoi de courriels, indépendant du fournisseur (R19).

AUCUN courriel réel n'est envoyé par ce dépôt aujourd'hui : aucun fournisseur n'est intégré.
Transports disponibles (MIKA_EMAIL_TRANSPORT) :
  - « faux »    (défaut hors production) : messages gardés EN MÉMOIRE (tests, CI, dev) ;
  - « journal » : n'envoie rien, journalise l'événement SANS destinataire en clair ni lien ;
  - tout autre nom : fournisseur à brancher via `enregistrer_transport(nom, fabrique)`.
En production (MIKA_ENV=production), « faux » et « journal » sont REFUSÉS : un fournisseur réel
doit être enregistré, sinon l'application refuse de démarrer (fail-closed : sans e-mail vérifiable,
aucun rattachement parent ne serait possible — mieux vaut le savoir au démarrage).

Intégration future d'un fournisseur (SMTP, API transactionnelle…) : implémenter
`TransportCourriel.envoyer(message)` (idempotent de préférence, sans journaliser le corps) et
l'enregistrer au démarrage ; aucun autre code ne change.

Session 5 : fournisseur SMTP générique « smtp » (`TransportSMTP`), configuré UNIQUEMENT par
variables d'environnement (EMAIL_PROVIDER_SETUP.md) — compatible avec tout relais SMTP
transactionnel. Aucune clé n'est présente dans le dépôt ; en production, une configuration
incomplète ou non chiffrée fait refuser le démarrage. Noms anglais équivalents exposés pour le
front et les runbooks : EmailProvider, FakeEmailProvider, SMTPEmailProvider.
"""

from __future__ import annotations

import hashlib
import logging
import os
import smtplib
import ssl
import threading
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Callable, Dict, List, Optional, Protocol

journal = logging.getLogger("mikamike.courriel")


@dataclass(frozen=True)
class Message:
    destinataire: str
    sujet: str
    corps: str
    type: str                      # ex. VERIFICATION_EMAIL
    metadonnees: Dict[str, str] = field(default_factory=dict)


class TransportCourriel(Protocol):
    def envoyer(self, message: Message) -> None: ...


class ConfigCourrielInvalide(RuntimeError):
    pass


class TransportFaux:
    """Boîte aux lettres en mémoire (bornée). Réservé aux tests / à la CI / au dev."""

    MAX = 1000

    def __init__(self):
        self._verrou = threading.Lock()
        self.messages: List[Message] = []

    def envoyer(self, message: Message) -> None:
        with self._verrou:
            self.messages.append(message)
            del self.messages[:-self.MAX]

    def derniers(self, destinataire: str) -> List[Message]:
        with self._verrou:
            return [m for m in self.messages if m.destinataire == destinataire]

    def vider(self) -> None:
        with self._verrou:
            self.messages.clear()


class TransportJournal:
    """N'envoie rien : trace l'événement avec une empreinte du destinataire (jamais l'adresse,
    jamais le corps, qui contient un jeton)."""

    def envoyer(self, message: Message) -> None:
        empreinte = hashlib.sha256(message.destinataire.encode("utf-8")).hexdigest()[:12]
        journal.info("courriel_non_envoye type=%s dest=%s", message.type, empreinte)


class EchecEnvoiCourriel(RuntimeError):
    """Le fournisseur a refusé ou n'a pas répondu. Le message d'erreur ne contient jamais
    l'adresse du destinataire, le corps, ni les identifiants SMTP."""


def _en_production() -> bool:
    return os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod")


def _sans_saut_de_ligne(nom: str, v: str) -> str:
    if "\r" in v or "\n" in v:
        raise ValueError(f"{nom}_invalide")  # injection d'en-têtes
    return v


@dataclass(frozen=True)
class ConfigSMTP:
    hote: str
    port: int
    securite: str                     # starttls | ssl | aucune (hors production uniquement)
    expediteur: str
    nom_expediteur: str
    utilisateur: Optional[str]
    mot_de_passe: Optional[str]
    delai_s: float

    SECURITES = ("starttls", "ssl", "aucune")

    @classmethod
    def depuis_env(cls) -> "ConfigSMTP":
        """Lecture fail-closed. N'inclut jamais la valeur du mot de passe dans une erreur."""
        hote = (os.getenv("MIKA_SMTP_HOST") or "").strip()
        expediteur = (os.getenv("MIKA_SMTP_FROM") or "").strip()
        securite = (os.getenv("MIKA_SMTP_SECURITE") or "starttls").strip().lower()
        if not hote:
            raise ConfigCourrielInvalide("MIKA_SMTP_HOST requis pour le transport smtp")
        if not expediteur or "@" not in expediteur:
            raise ConfigCourrielInvalide("MIKA_SMTP_FROM requis (adresse d'expédition)")
        _sans_saut_de_ligne("MIKA_SMTP_FROM", expediteur)
        if securite not in cls.SECURITES:
            raise ConfigCourrielInvalide("MIKA_SMTP_SECURITE invalide (starttls|ssl|aucune)")
        if securite == "aucune" and _en_production():
            raise ConfigCourrielInvalide("SMTP non chiffré interdit en production")
        port_brut = (os.getenv("MIKA_SMTP_PORT") or {"ssl": "465", "starttls": "587"}.get(securite, "25")).strip()
        if not port_brut.isdigit() or not 1 <= int(port_brut) <= 65535:
            raise ConfigCourrielInvalide("MIKA_SMTP_PORT invalide")
        delai_brut = (os.getenv("MIKA_SMTP_DELAI_S") or "10").strip()
        try:
            delai = float(delai_brut)
        except ValueError:
            raise ConfigCourrielInvalide("MIKA_SMTP_DELAI_S invalide") from None
        if not 1 <= delai <= 60:
            raise ConfigCourrielInvalide("MIKA_SMTP_DELAI_S hors bornes (1..60)")
        utilisateur = (os.getenv("MIKA_SMTP_USER") or "").strip() or None
        mot_de_passe = os.getenv("MIKA_SMTP_PASSWORD") or None
        if bool(utilisateur) != bool(mot_de_passe):
            raise ConfigCourrielInvalide("MIKA_SMTP_USER et MIKA_SMTP_PASSWORD vont ensemble")
        if utilisateur and securite == "aucune":
            raise ConfigCourrielInvalide("identifiants SMTP interdits sur une connexion non chiffrée")
        if _en_production() and not utilisateur:
            raise ConfigCourrielInvalide("identifiants SMTP requis en production")
        nom = _sans_saut_de_ligne("MIKA_SMTP_FROM_NAME", (os.getenv("MIKA_SMTP_FROM_NAME") or "MikaMike").strip())
        return cls(hote, int(port_brut), securite, expediteur, nom, utilisateur, mot_de_passe, delai)

    def __repr__(self) -> str:  # jamais le mot de passe dans une trace
        return (f"ConfigSMTP(hote={self.hote!r}, port={self.port}, securite={self.securite!r}, "
                f"expediteur={self.expediteur!r}, utilisateur={'***' if self.utilisateur else None})")


class TransportSMTP:
    """Fournisseur SMTP générique (session 5). Une connexion par message (volume faible :
    vérifications d'adresse), délai borné, TLS vérifié (certificat + nom d'hôte)."""

    def __init__(self, config: Optional[ConfigSMTP] = None, fabrique_smtp=None):
        self.config = config or ConfigSMTP.depuis_env()
        self._smtp = fabrique_smtp  # injection pour les tests (aucun réseau)

    def construire(self, message: Message) -> EmailMessage:
        c = self.config
        em = EmailMessage()
        em["From"] = formataddr((c.nom_expediteur, c.expediteur))
        em["To"] = _sans_saut_de_ligne("destinataire", message.destinataire)
        em["Subject"] = _sans_saut_de_ligne("sujet", message.sujet)
        em["Message-ID"] = make_msgid(domain=c.expediteur.rsplit("@", 1)[1])
        em["X-MikaMike-Type"] = _sans_saut_de_ligne("type", message.type)
        em["Auto-Submitted"] = "auto-generated"
        em.set_content(message.corps)
        return em

    def _connexion(self):
        c = self.config
        if self._smtp is not None:
            return self._smtp(c)
        if c.securite == "ssl":
            return smtplib.SMTP_SSL(c.hote, c.port, timeout=c.delai_s, context=ssl.create_default_context())
        return smtplib.SMTP(c.hote, c.port, timeout=c.delai_s)

    def envoyer(self, message: Message) -> None:
        c = self.config
        em = self.construire(message)
        try:
            with self._connexion() as smtp:
                if c.securite == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                if c.utilisateur:
                    smtp.login(c.utilisateur, c.mot_de_passe)
                smtp.send_message(em)
        except (smtplib.SMTPException, OSError) as e:
            journal.warning("courriel_echec type=%s erreur=%s", message.type, type(e).__name__)
            raise EchecEnvoiCourriel(f"envoi_impossible:{type(e).__name__}") from None
        journal.info("courriel_envoye type=%s", message.type)


# Noms anglais (documentation front / runbooks) — mêmes objets.
EmailProvider = TransportCourriel
FakeEmailProvider = TransportFaux
SMTPEmailProvider = TransportSMTP

_FAUX = TransportFaux()
_FABRIQUES: Dict[str, Callable[[], TransportCourriel]] = {
    "faux": lambda: _FAUX, "journal": TransportJournal, "smtp": TransportSMTP}
_TRANSPORTS_DE_TEST = {"faux", "journal"}


def enregistrer_transport(nom: str, fabrique: Callable[[], TransportCourriel]) -> None:
    if nom in _TRANSPORTS_DE_TEST:
        raise ValueError("nom_reserve")
    _FABRIQUES[nom] = fabrique


def nom_transport() -> str:
    en_prod = _en_production()
    nom = (os.getenv("MIKA_EMAIL_TRANSPORT") or ("" if en_prod else "faux")).strip().lower()
    if not nom:
        raise ConfigCourrielInvalide("MIKA_EMAIL_TRANSPORT requis en production")
    if en_prod and nom in _TRANSPORTS_DE_TEST:
        raise ConfigCourrielInvalide(f"transport « {nom} » interdit en production")
    if nom not in _FABRIQUES:
        raise ConfigCourrielInvalide(f"transport inconnu : {nom}")
    if nom == "smtp":
        ConfigSMTP.depuis_env()  # configuration incomplète ⇒ refus de démarrer (aucune connexion)
    return nom


def transport() -> TransportCourriel:
    return _FABRIQUES[nom_transport()]()


def boite_de_test() -> TransportFaux:
    return _FAUX
