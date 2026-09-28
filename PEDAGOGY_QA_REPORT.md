# Rapport QA pédagogique MikaMike

Généré par `pedagogy.qa v0.1.0` — données : `pedagogy/data`.

**Verdict : PASS** (code de sortie 0) — bank_ready : **false**

Règle : exit 1 si au moins une issue BLOCKER ou ERROR (verdict FAIL), sinon exit 0 (verdict PASS). L'absence de preuve officielle (NOTION_UNPROVEN, NOTIONS_UNPROVEN_SUMMARY, SOURCE_NOT_RETRIEVED) est INFO et ne fait jamais échouer ; les WARNING non plus.

## Totaux

| Élément | Nombre |
|---|---:|
| Notions | 404 |
| Fichiers de notions | 24 |
| Sources officielles déclarées | 7 |
| Sources récupérées | 1 |
| Exercices | 0 |
| Quiz | 0 |
| Erreurs de chargement | 0 |
| Issues | 786 (BLOCKER 0, ERROR 0, WARNING 0, INFO 786) |

### Notions par statut de preuve

| Statut | Notions |
|---|---:|
| UNPROVEN | 404 |

### Notions par matière

| Matière | Notions |
|---|---:|
| ENSEIGNEMENT_SCIENTIFIQUE | 28 |
| MATHS | 150 |
| PHYSIQUE_CHIMIE | 112 |
| SCIENCES_TECHNOLOGIE | 25 |
| SVT | 89 |

### Notions par niveau

| Niveau | Notions |
|---|---:|
| 1RE | 66 |
| 2NDE | 57 |
| 3E | 48 |
| 4E | 49 |
| 5E | 52 |
| 6E | 48 |
| TLE | 84 |

## Issues

### Par sévérité

| Sévérité | Issues |
|---|---:|
| INFO | 786 |

### Par code

| Code | Issues |
|---|---:|
| NOTIONS_UNPROVEN_SUMMARY | 1 |
| NOTION_UNPROVEN | 404 |
| SOURCE_NOT_RETRIEVED | 381 |

### Par matière

| Matière | Issues |
|---|---:|
| - | 1 |
| ENSEIGNEMENT_SCIENTIFIQUE | 56 |
| MATHS | 277 |
| PHYSIQUE_CHIMIE | 224 |
| SCIENCES_TECHNOLOGIE | 50 |
| SVT | 178 |

### Par niveau

| Niveau | Issues |
|---|---:|
| - | 1 |
| 1RE | 132 |
| 2NDE | 114 |
| 3E | 96 |
| 4E | 98 |
| 5E | 104 |
| 6E | 73 |
| TLE | 168 |

## Principales anomalies (BLOCKER / ERROR / WARNING, 60 premières)

Aucune anomalie BLOCKER, ERROR ou WARNING.

## Ce qui n'a PAS pu être vérifié

- Aucune notion PROVEN_OFFICIAL : la banque d'exercices/quiz ne peut pas être alimentée (bank_ready=false).
- Aucun exercice dans la banque : contrôles d'exercices non exercés.
- Aucune question de quiz dans la banque : contrôles de quiz non exercés.
- Adéquation au niveau (TOO_ADVANCED / TOO_SIMPLE) : heuristique lexicale, revue humaine requise ; l'exactitude scientifique des contenus n'est vérifiée que par les validateurs automatiques disponibles.
