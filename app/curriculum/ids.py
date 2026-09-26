"""
ids.py — Identifiants stables et empreintes.

Un identifiant canonique est DÉTERMINISTE : mêmes entrées ⇒ même identifiant,
sur toute machine, à toute date. Il ne dépend ni d'un compteur, ni de l'ordre
d'import, ni de l'horloge. Forme : `<type>:<segment>:<segment>…` (ASCII, minuscules).
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def slug(texte: str) -> str:
    """Slug ASCII stable : accents retirés, minuscules, séparateur « - »."""
    base = unicodedata.normalize("NFKD", str(texte)).encode("ascii", "ignore").decode("ascii")
    s = _NON_SLUG.sub("-", base.lower()).strip("-")
    if not s:
        raise ValueError("segment d'identifiant vide après normalisation")
    return s


def stable_id(type_objet: str, *segments: object) -> str:
    """Construit un identifiant canonique stable, ex. stable_id('chap', 'prog:x', 'Fractions')."""
    if not segments:
        raise ValueError("au moins un segment est requis")
    parts = [slug(type_objet)]
    for seg in segments:
        seg_s = str(seg)
        # Un identifiant déjà canonique (contenant « : ») est conservé tel quel.
        parts.append(seg_s if ":" in seg_s else slug(seg_s))
    return ":".join(parts)


def normaliser_pour_empreinte(texte: str) -> str:
    """Normalisation utilisée pour les empreintes et la déduplication (NFC, espaces)."""
    t = unicodedata.normalize("NFC", texte or "")
    return " ".join(t.split())


def sha256_texte(texte: str) -> str:
    """Empreinte SHA-256 hexadécimale d'un texte normalisé (espaces/NFC)."""
    return hashlib.sha256(normaliser_pour_empreinte(texte).encode("utf-8")).hexdigest()


def sha256_octets(donnees: bytes) -> str:
    return hashlib.sha256(donnees).hexdigest()
