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
"""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Protocol

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


_FAUX = TransportFaux()
_FABRIQUES: Dict[str, Callable[[], TransportCourriel]] = {"faux": lambda: _FAUX, "journal": TransportJournal}
_TRANSPORTS_DE_TEST = {"faux", "journal"}


def enregistrer_transport(nom: str, fabrique: Callable[[], TransportCourriel]) -> None:
    if nom in _TRANSPORTS_DE_TEST:
        raise ValueError("nom_reserve")
    _FABRIQUES[nom] = fabrique


def nom_transport() -> str:
    en_prod = os.getenv("MIKA_ENV", "").strip().lower() in ("production", "prod")
    nom = (os.getenv("MIKA_EMAIL_TRANSPORT") or ("" if en_prod else "faux")).strip().lower()
    if not nom:
        raise ConfigCourrielInvalide("MIKA_EMAIL_TRANSPORT requis en production")
    if en_prod and nom in _TRANSPORTS_DE_TEST:
        raise ConfigCourrielInvalide(f"transport « {nom} » interdit en production")
    if nom not in _FABRIQUES:
        raise ConfigCourrielInvalide(f"transport inconnu : {nom}")
    return nom


def transport() -> TransportCourriel:
    return _FABRIQUES[nom_transport()]()


def boite_de_test() -> TransportFaux:
    return _FAUX
