# CLOUD_DATA_MODEL — Modèle canonique des programmes (France)

Code : `app/curriculum/model.py`. Tous les objets sont immuables (`frozen`) et refusent les
champs inconnus (`extra="forbid"`).

## Pipeline

```
SOURCE_OFFICIELLE → PROGRAMME → NIVEAU → MATIÈRE → DOMAINE → THÈME → CHAPITRE → NOTION
→ PRÉREQUIS → EXERCICE → QUIZ → VÉRIFICATION → PÉDAGOGIE_MIKA
```

| Objet | Champs clés | Rattachement |
|---|---|---|
| `SourceOfficielle` | id, titre, éditeur, url (https/file), référence (n° BO), date, sha256 du document, `fictive` | — |
| `Programme` | id, source_id, matière, niveaux, rentree_debut, rentree_fin | source |
| `Domaine` | id, programme_id, titre, ordre | programme |
| `Theme` | id, programme_id, domaine_id | domaine (même programme) |
| `Chapitre` | id, programme_id, theme_id, niveau, `ambigu` | thème (même programme) |
| `Notion` | id, programme_id, chapitre_id, niveau, matière, texte, statut_texte, preuve, prérequis, optionnelle, disciplines_mobilisees, id_historique | chapitre |
| `Preuve` | source_id, document, url, page, section, **extrait verbatim**, sha256_extrait, statut, date | source |
| `Exercice` (`exercices.py`) | notion, matière, niveau, programme, chapitre, difficulté 1–5, objectif, prérequis, énoncé, réponse, type de vérification, indices, erreurs fréquentes, sha256 de la source | notion |
| `QuestionQuiz` (`quiz.py`) | notion, matière, niveau, choix (3–6), index_correct, **réponse de référence indépendante**, explication | notion |

## Identifiants stables (`ids.py`)
`<type>:<segments>` en ASCII minuscule, dérivés du contenu hiérarchique, jamais d'un compteur ni
de l'horloge (ex. `chap:prog:x:y:fractions-et-decimaux`). Même entrée ⇒ même ID sur toute machine.

## Versionnement par rentrée
`Programme.en_vigueur(rentree)` ; une rentrée = année de septembre (2025 ⇒ 2025-2026).
Contrôles : `PROGRAMMES_CHEVAUCHANTS` (deux versions en vigueur la même année pour une même
matière/niveau) et `VERSION_MELANGEE` (prérequis pris dans une version jamais en vigueur en même
temps).

## Statuts de preuve
| Statut | Condition (recalculée par `evaluer_preuve`, jamais lue telle que déclarée) |
|---|---|
| PROVEN | source enregistrée, URL cohérente, empreinte de l'extrait exacte, texte de la notion présent dans l'extrait, source non fictive (hors mode test) |
| NOT_EVIDENCED | aucune preuve, ou source non enregistrée |
| AMBIGUOUS | ambiguïté déclarée, ou texte absent de l'extrait |
| QUARANTINED | empreinte falsifiée, URL incohérente, source fictive en production, quarantaine déclarée |

## Statuts de texte
TEXT_EXACT, TEXT_RECOVERED (réparations sans perte seulement), TEXT_TRUNCATED, TEXT_FRAGMENTED,
FORMULA_CORRUPTED, COLUMN_CONTAMINATION (colonnes, en-têtes/pieds de page, concaténations),
SOURCE_NOT_EVIDENCED, AMBIGUOUS. Seuls EXACT/RECOVERED autorisent la génération.

## Applicabilité matière × niveau (`NIVEAUX_PAR_MATIERE`)
| Matière | Niveaux |
|---|---|
| Mathématiques | CM1 → Tle |
| Physique-Chimie | 5e → Tle |
| SVT | 5e → Tle |
| Sciences et technologie | CM1, CM2, 6e (cycle 3) |
| Enseignement scientifique | 1re, Tle |

⚠ Tableau d'**organisation** (quelle matière existe à quel niveau), pas de contenu de programme.
**À confirmer contre les textes officiels** lors du premier import de sources (décision D6) ;
notamment l'évolution récente des intitulés au cycle 3 / en 6e.

## Existant migré (`legacy.py`)
42 notions de `parcours/curriculum_dataset.py` → `notion:historique:<id>`, programme
`prog:non-source:<matière>:<niveau>` (non enregistré), chapitre absent, statut NOT_EVIDENCED.
5 notions « primaire » non migrées (niveau CM1/CM2 indéterminable, cycle 2 hors périmètre).

## Format d'import (`importers.py`)
`IMPORT_MANIFEST.json` : `{"version": 1, "fichiers": [{"chemin", "sha256", "type"}]}` avec
`type ∈ {referentiel, registre_notions, mapping_notion_chapitre, index_contenus, opaque}`.
Les formats C02 / C02-6.1 / Extraction V3 / M01 **ne sont pas documentés dans ce dépôt** : ils
s'importent en `opaque` (empreinte vérifiée, non interprétés) jusqu'à ce qu'un adaptateur soit
écrit à partir d'échantillons réels.
