"""
security_config.py — Lecture et validation centralisées des secrets (fail-closed).

Principe : AUCUNE valeur de secours. Si un secret obligatoire est absent, vide,
trop court ou manifestement générique/démonstration, on lève une erreur explicite
et l'application refuse de démarrer. La valeur du secret n'est JAMAIS incluse dans
un message d'erreur ni journalisée, et aucun secret n'est généré automatiquement.

Deux secrets DISTINCTS :
  - MIKA_PSEUDO_SECRET : sel HMAC de pseudonymisation (RGPD).
  - MIKA_JWT_SECRET    : clé de signature des jetons JWT.
On n'utilise jamais l'un comme repli de l'autre.
"""

from __future__ import annotations

import os

# Longueur minimale exigée pour un secret (caractères).
MIN_SECRET_LEN = 16

# Valeurs manifestement génériques / de démonstration, refusées d'office.
_VALEURS_INTERDITES = {
    "changeme", "change-me", "secret", "password", "motdepasse",
    "default", "defaut", "demo", "test", "example", "azerty", "qwerty",
    "mikamike", "todo", "none", "null",
}
# Fragments interdits (rejette toute valeur les contenant).
_FRAGMENTS_INTERDITS = ("mikamike_secret_key", "changeme", "your-secret", "replace")


class SecretConfigError(RuntimeError):
    """Levée quand un secret obligatoire est absent ou invalide (fail-closed)."""


def _lire_secret(nom: str) -> str:
    """Lit et valide un secret depuis l'environnement. Ne révèle jamais sa valeur."""
    brut = os.getenv(nom)
    if brut is None:
        raise SecretConfigError(
            f"{nom} manquant : définissez cette variable d'environnement "
            f"(aucune valeur de secours n'est autorisée)."
        )
    valeur = brut.strip()
    if not valeur:
        raise SecretConfigError(f"{nom} vide : une valeur non vide est requise.")
    if len(valeur) < MIN_SECRET_LEN:
        raise SecretConfigError(
            f"{nom} trop court : au moins {MIN_SECRET_LEN} caractères requis."
        )
    bas = valeur.lower()
    if bas in _VALEURS_INTERDITES or any(fr in bas for fr in _FRAGMENTS_INTERDITS):
        raise SecretConfigError(
            f"{nom} rejeté : valeur générique ou de démonstration interdite."
        )
    return valeur


def get_pseudo_secret() -> str:
    """Secret de pseudonymisation HMAC (MIKA_PSEUDO_SECRET). Fail-closed."""
    return _lire_secret("MIKA_PSEUDO_SECRET")


def get_jwt_secret() -> str:
    """Secret de signature JWT (MIKA_JWT_SECRET). Fail-closed."""
    return _lire_secret("MIKA_JWT_SECRET")
