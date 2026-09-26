"""
validation.py — Types d'entrée bornés, partagés par toutes les routes.

Principe : toute chaîne venant du client est bornée (longueur) et, pour les
identifiants, restreinte à un alphabet sûr. Un identifiant élève ne doit jamais
contenir de PII (espace, @, accents d'un prénom…) : l'alphabet restreint le rend
impossible par construction et évite l'injection dans les logs.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

# Alphabet des identifiants opaques (pseudo-id élève, session, exercice, notion).
ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$"

Identifiant = Annotated[str, Field(min_length=1, max_length=128, pattern=ID_PATTERN)]

# Identifiants PERSISTÉS dans une colonne String(64) (séance, notion de la mémoire espacée,
# compétence/exercice de l'escalier) : au-delà, PostgreSQL lève une erreur (500) et SQLite
# stocke sans contrôle (revue session 3, S3-10).
Identifiant64 = Annotated[str, Field(min_length=1, max_length=64, pattern=ID_PATTERN)]

# Réponse libre d'élève (texte court ; les images passent par le canal OCR borné).
ReponseEleve = Annotated[str, Field(max_length=500)]

# Taille max de l'état de séance sérialisé (l'ardoise est bornée à 2 Mo côté OCR).
MAX_SESSION_STATE_BYTES = 2 * 1024 * 1024
