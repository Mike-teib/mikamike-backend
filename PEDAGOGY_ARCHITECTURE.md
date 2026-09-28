# PEDAGOGY_ARCHITECTURE — Méga-pack pédagogique MikaMike (Maths · PC · SVT, 6e → Tle)

> Branche : `cloud/mikamike-pedagogy-megapack-20260928` (indépendante de la PR #3, partie de `main`).
> Paquet autonome `pedagogy/` : aucune dépendance à `app/`, aucune base de données, aucun appel
> réseau, aucune API payante. L'API n'est **pas** montée dans `main.py`.

## 1. Principe directeur : la preuve avant le contenu

```
PDF officiel local ──sha256──► OfficialSource (RETRIEVED/VERIFIED)
        │ pypdf, page par page, normalisation typographique
        ▼
Notion candidate (UNPROVEN) ──promote_notion(page, extrait exact)──► PROVEN_OFFICIAL
        │                                                              │ revue humaine
        │  interdit                                                     ▼
        ╳──────────► exercices / quiz                         review_status=APPROVED
                                                                        │
                                                                        ▼
                                                             banque (exercices, quiz)
                                                                       │ validateurs + QA
                                                                       ▼
                                                           API lecture seule / tuteur
```

- Une notion n'est `PROVEN_OFFICIAL` que si son `official_wording` figure **mot pour mot**
  sur la page déclarée d'un PDF officiel local dont l'empreinte SHA-256 est vérifiée.
  La promotion est explicite (`promote_notion`), jamais automatique.
- `UNPROVEN`, `CONFLICT` et les notions `PROVEN_OFFICIAL` non encore approuvées humainement n'entrent **jamais** dans le pipeline d'exercices (invariant `Notion.eligible_for_content`, validateurs `NOTION_NOT_PROVEN` / `NOTION_NOT_APPROVED` BLOCKER, filtres de l'API).
- Les anciens contenus MikaMike sont des **candidats** : correspondance tracée
  (`data/legacy/legacy_notions_map.json`), jamais réécrits.

## 2. Modules

| Module | Rôle |
|---|---|
| `pedagogy/models.py` | Contrat canonique Pydantic v2 (gelé, `extra="forbid"`) : `Notion`, `OfficialSource`, `Exercise`, `ExpectedAnswer`, `QuizItem`, `NotionFile` ; énumérations matière/niveau/cycle/parcours/statuts ; IDs stables `SUBJ.NIVEAU.DOMAINE.slug`. |
| `pedagogy/sources.py` | Empreintes, extraction PDF, normalisation, `verify_notion_against_source`, `propose_promotions`, `promote_notion`, `recompute_statuses`. |
| `pedagogy/sources_cli.py` | `python -m pedagogy.sources_cli status \| register \| propose \| verify`. |
| `pedagogy/registry.py` | Chargement de `pedagogy/data/` (sources, notions, banque) ; mode non strict = erreurs collectées. |
| `pedagogy/graph.py` + `prerequisite_graph_validator.py` | Graphe de prérequis, cycles, orphelins, sauts de niveau, `learning_path`. |
| `pedagogy/checks/*` | Vérificateurs déterministes : SymPy (maths), grandeurs/unités/CS (physique), notation LaTeX/Unicode, `check_answer`, similarité. Verdicts `VALID/INVALID/AMBIGUOUS/NEEDS_HUMAN_REVIEW`, jamais VALID par défaut. |
| `pedagogy/validators/{notions,exercise,quiz}.py` | Règles de conformité (liste d'`Issue` code/sévérité/objet/détail). |
| `pedagogy/qa/` | `python -m pedagogy.qa` → `PEDAGOGY_QA_REPORT.json/.md` (déterministes). |
| `pedagogy/coverage.py` | `python -m pedagogy.coverage` → `PEDAGOGY_COVERAGE_MATRIX.csv` + `PEDAGOGY_COVERAGE_REPORT.md`. |
| `pedagogy/legacy.py` | `python -m pedagogy.legacy` → correspondance des 47 notions historiques. |
| `pedagogy/api.py` | Routeur FastAPI GET-only `/pedagogy/*` (non monté). |
| `M01_346_COMPARISON_TOOL.py` | Comparaison publié ↔ ré-extrait des 346 notions M01 ; refuse de conclure sans les deux corpus (code 2). |

## 3. Données (`pedagogy/data/`)

```
sources/official_sources.json        7 sources attendues (EXPECTED, références à vérifier)
notions/<MATIÈRE>/<NIVEAU>[_<PARCOURS>].json   404 notions candidates (UNPROVEN)
notions/<MATIÈRE>/UNCERTAINTIES.md   incertitudes de découpage et de version, par matière
bank/exercises/*.json, bank/quizzes/*.json      vides tant qu'aucune notion n'est prouvée
pilot/<MATIÈRE>_pilot_plan.json      plan pilote 3 notions/niveau — BLOCKED_NO_PROVEN_NOTION
legacy/legacy_notions_map.json       correspondance indicative historique → candidates
```
`pedagogy/sources_local/official/` : dépôt des PDF officiels (documents publics ; les versionner permet à la CI de re-vérifier chaque preuve).

**6e :** pas de Physique-Chimie ni de SVT propres ; la matière est « Sciences et
technologie » (`ST.6E.*`), et la matrice l'indique explicitement (`NOT_APPLICABLE` + renvoi).
**Cycle 4 :** le programme est fixé pour le cycle ; la répartition 5e/4e/3e est une
progression MikaMike **indicative**, documentée dans les `UNCERTAINTIES.md`.

## 4. Mettre une notion en production — procédure

1. Déposer le PDF officiel dans `pedagogy/sources_local/official/`.
2. `python -m pedagogy.sources_cli register SRC-… chemin.pdf [--reference-verified]`
   (calcule le SHA-256, passe la source en RETRIEVED/VERIFIED).
3. `python -m pedagogy.sources_cli propose` : liste les pages candidates pour chaque notion.
4. `promote_notion(notion, texte_source, page, extrait_exact)` établit la preuve documentaire ; l'extrait est recopié depuis le PDF, jamais depuis la mémoire. La notion reste non éligible au contenu tant qu'une relecture humaine n'a pas passé `review_status=APPROVED`.
5. `python -m pedagogy.sources_cli verify` (échoue si une notion déclarée prouvée ne l'est pas).
6. Pilote : rédiger 5/5/5/3 exercices + 10 quiz pour 3 notions/niveau/matière,
   `generation_origin` tracée, `qa_status` calculé par `python -m pedagogy.qa`.
7. Revue humaine du pilote **avant** toute production de masse.

## 5. Garanties testées (`tests_pedagogy/`)

- Invariants du modèle (preuve incomplète refusée, libellé officiel interdit sur notion non
  prouvée, publication impossible sans preuve + approbation, fixtures non publiables).
- Chaîne de preuve de bout en bout sur PDF généré ; falsification du PDF → `CONFLICT`.
- Données réelles : toutes les notions `UNPROVEN`/`CANDIDATE_UNVERIFIED`, `official_wording`
  nul, IDs = `make_notion_id`, prérequis jamais d'un niveau supérieur, graphe acyclique.
- API : seules les notions prouvées et les contenus QA-validés non fictifs sont servis ;
  aucune route d'écriture (405).
- QA et matrice déterministes (octet pour octet).

Lancer : `.venv/bin/python -m pytest -q -p no:cacheprovider tests_pedagogy`
(dépendances : `requirements-pedagogy.txt`).
