# TUTOR_CONTENT_CONTRACT — Contrat de contenu du professeur Mika

> Statut : **contrat de conception**. Aucun branchement du tuteur, aucun appel LLM réel
> dans ce lot. Ce document fixe ce que le contenu pédagogique (`pedagogy/`) doit fournir
> et ce que le tuteur a le droit d'en faire.

## 0. Principes non négociables

1. **Contenu prouvé uniquement.** Le tuteur ne sert que des exercices / quiz dont la notion est
   `PROVEN_OFFICIAL`, dont `qa_status ∈ {AUTO_PASSED, HUMAN_APPROVED}` et qui ne sont pas des
   `FIXTURE_TEST`. Source : `GET /pedagogy/exercises` et `/pedagogy/quiz` (déjà filtrés).
2. **Vérification déterministe.** Une réponse est jugée par `pedagogy.checks.answers.check_answer`
   (SymPy, unités, texte exact…). Un LLM ne peut **jamais** déclarer une réponse juste.
   Verdicts : `VALID`, `INVALID`, `AMBIGUOUS`, `NEEDS_HUMAN_REVIEW` — jamais VALID par défaut.
3. **Pas de solution d'emblée.** La correction complète n'est montrée qu'après épuisement des
   indices et de la remédiation (ou à la demande explicite, tracée `avec_aide=true`).
4. **Monotonie.** Plus l'élève reçoit d'aide, moins la difficulté proposée ensuite peut monter.
5. **Aucune donnée personnelle** dans le contenu ni dans les traces envoyées à un modèle ;
   identifiant élève = pseudonyme HMAC.

## 1. Données consommées (par étape)

| # | Étape | Champs du contenu utilisés | Source |
|---|---|---|---|
| 1 | Identifier la notion travaillée | `notion_id`, `title`, `subject`, `level`, `chapter` | registre notions |
| 2 | Vérifier les prérequis | `prerequisites`, `cross_subject_links` ; `learning_path(graph, target, mastered)` | `prerequisite_graph.json`, `pedagogy.graph` |
| 3 | Choisir la difficulté | `Exercise.difficulty` (DISCOVERY → APPLICATION → CONSOLIDATION → ADVANCED), historique élève | banque |
| 4 | Proposer un exercice | `statement`, `exercise_type`, `choices`, `estimated_time_min` | banque |
| 5 | Analyser la réponse | `expected_answer` (kind, value, unit, tolérance, CS, forme requise) | `check_answer` |
| 6 | Identifier l'erreur | `common_errors` (réponse fausse → diagnostic), `Notion.common_mistakes`, `QuizItem.common_error_target` | banque + notion |
| 7 | Proposer un indice | `hints` (ordonnés du plus léger au plus explicite) | banque |
| 8 | Proposer une remédiation | `remediation`, prérequis manquant (`learning_path`) | banque + graphe |
| 9 | Proposer un exercice similaire | même `notion_id`, même `difficulty`, `exercise_id` différent, similarité < seuil (QA `TOO_SIMILAR`) | banque |
| 10 | Augmenter progressivement | bande de difficulté suivante si réussite **sans aide** | banque |

## 2. Machine à états (référence)

```
DEBUT
  └─ prérequis non maîtrisé ? ──oui──► REMEDIER_PREREQUIS(notion la plus basse de learning_path)
  └─ non ► PROPOSER(exercice, bande = f(maîtrise))
REPONSE
  ├─ VALID sans aide        ► CONSOLIDER / MONTER_DE_BANDE
  ├─ VALID avec aide        ► VERIFIER_COMPREHENSION ► EXERCICE_SIMILAIRE (même bande)
  ├─ INVALID + erreur connue (common_errors) ► DIAGNOSTIC_CIBLE ► INDICE(1)
  ├─ INVALID inconnue       ► QUESTION_INTERMEDIAIRE / INDICE(n+1)
  ├─ AMBIGUOUS / NEEDS_HUMAN_REVIEW ► DEMANDER_REFORMULATION (max 2) ► REVUE_HUMAINE
  └─ indices épuisés        ► REMEDIATION ► CORRECTION_COMMENTEE ► EXERCICE_SIMILAIRE (bande ≤ actuelle)
```

Invariants testables (à reprendre du tuteur existant sur la branche session6) :
aucun message répété ; réponse jamais divulguée avant la correction commentée ; bande
proposée non croissante tant que l'aide augmente ; une réussite avec aide ne compte jamais
comme maîtrise autonome.

## 3. Contrat d'interface (futur, non implémenté ici)

```python
class TutorContentPort(Protocol):
    def notion(self, notion_id: str) -> Notion: ...
    def learning_path(self, target: str, mastered: set[str]) -> list[str]: ...
    def pick_exercise(self, notion_id: str, band: DifficultyBand, exclude: set[str]) -> Exercise | None: ...
    def similar_exercise(self, exercise_id: str, exclude: set[str]) -> Exercise | None: ...
    def check(self, exercise: Exercise, answer: str) -> Verdict: ...
    def diagnose(self, exercise: Exercise, answer: str) -> str | None: ...   # via common_errors
```
Toutes les méthodes sont **déterministes** et en lecture seule. `pick_exercise` renvoie `None`
(jamais un contenu non prouvé) quand la banque est vide pour la notion : le tuteur doit alors
dire honnêtement que le contenu n'est pas encore disponible.

## 4. Rôle éventuel d'un modèle de langage (lot ultérieur, sous conditions)

Autorisé seulement pour : reformuler un indice **déjà validé**, adapter le ton, résumer une
remédiation. Interdit pour : juger une réponse, inventer un exercice, un indice ou une
solution, citer un programme. Toute sortie de modèle affichée à l'élève doit être traçable
vers un contenu validé de la banque.

## 5. Exigences de contenu pour qu'une notion soit « prête tuteur »

- notion `PROVEN_OFFICIAL`, `review_status = APPROVED` ;
- ≥ 1 exercice par bande DISCOVERY / APPLICATION / CONSOLIDATION (cible banque : 5/5/5/3) ;
- chaque exercice : ≥ 2 indices gradués, `remediation`, ≥ 1 `common_errors`, corrigé pas à pas,
  `expected_answer` auto-vérifiable (sauf RUBRIC, alors revue humaine) ;
- ≥ 10 questions de quiz, chaque distracteur justifié (`distractor_rationale`) ;
- QA `python -m pedagogy.qa` sans BLOCKER ni ERROR pour la notion.
