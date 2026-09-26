# CLOUD_PEDAGOGY_MIKA — Professeur virtuel Mika

## Ce qui existait
- Learning engine : 7 états de maîtrise, règle LE-06 (réussite avec aide ⇒ jamais MAITRISE),
  remontée du graphe de prérequis (« marche manquante »).
- Escalier « 8 étapes » : en pratique une évaluation + un message fixe + l'explication unique
  de l'exercice. **Pas de dialogue** : ni indices gradués, ni question intermédiaire, ni seconde
  méthode, ni vérification de compréhension.

## Ce qui a été ajouté — `app/curriculum/pedagogie/tuteur.py`
Machine à états **déterministe** (aucun LLM, aucune API). Entrées : un `Exercice` validé + un
`PlanGuidage` validé. Sorties : une `Action` + un message + une difficulté proposée.

| Étape | Action | Déclencheur |
|---|---|---|
| 1. Ce que l'élève sait | `PRESENTER_EXERCICE` (liste des prérequis acquis) ou `REMEDIER_PREREQUIS` | démarrage |
| 2. Blocage | `IDENTIFIER_BLOCAGE` (erreur fréquente reconnue ⇒ diagnostic ciblé) | 1re erreur |
| 3. Question intermédiaire | `QUESTION_INTERMEDIAIRE` | erreur suivante / demande d'aide |
| 4. Indice | `DONNER_INDICE` (gradué, du plus léger au plus explicite) | puis |
| 5. Réessayer | chaque aide se termine par une invitation à réessayer | — |
| 6. Autre méthode | `AUTRE_METHODE` (jamais deux fois la même) | indices épuisés, ou compréhension ratée |
| 7. Compréhension | `VERIFIER_COMPREHENSION` | réussite **avec** aide |
| 8. Consolidation | `CONSOLIDATION` | réussite (autonome ou compréhension validée) |
| dernier recours | `CORRECTION_COMMENTEE` | toutes les aides épuisées |
| sécurité | `DEMANDER_REFORMULATION` → `REVUE_HUMAINE` | réponse illisible (non comptée comme erreur) |

Suivi : `tentatives`, `erreurs`, `erreurs_frequentes_vues`, `avec_aide`, `niveau_aide`,
`niveau_estime` (ACQUIS_AUTONOME / ACQUIS_ASSISTE / FRAGILE), `prerequis_manquant`.

### Garanties vérifiées par les tests (3 125 séquences de réponses exhaustives)
1. aucun message n'est répété ;
2. la réponse n'apparaît jamais avant la correction commentée ;
3. **monotonie** : la difficulté proposée ne croît jamais quand l'aide augmente ;
4. LE-06 : toute aide reçue interdit « ACQUIS_AUTONOME » ;
5. prérequis non solide ⇒ on n'avance pas.
`valider_plan` refuse en amont un plan qui divulgue la réponse, se répète ou n'offre aucune aide.

## Récurrence — `pedagogie/recurrence.py`
- Diagnostic de rédaction en 4 parties (initialisation, hypothèse, hérédité, conclusion) :
  11 confusions détectées (P(n) vs P(n+1), hypothèse « pour tout n », objectif de l'hérédité,
  hypothèse non utilisée, conclusion sur un seul rang…). Écritures `P(n+1)`, `P_{n+1}`, `P( n + 1 )`
  reconnues.
- Une **question de guidage** par confusion, jamais la réponse ; posées dans l'ordre de la preuve.
- Vérification SymPy : formule explicite (`u(n+1)=f(u(n))`, initialisation + hérédité
  symboliques) et hérédité par **fonction auxiliaire** (f croissante sur [a,b], f(a) ≥ a, f(b) ≤ b).

## Vérificateurs par matière (utilisés par le tuteur via `verifiers/dispatch.py`)
Maths (équivalence symbolique, formes requises), Physique-Chimie (unités, dimensions, CS, notation
scientifique, homogénéité), SVT (vocabulaire, causalité, niveaux d'organisation, classification,
prudence), Sciences & technologie (chaînes, affectations, bilan énergétique, cycle de vie, vues),
Enseignement scientifique (rattachement pluridisciplinaire justifié par la source).

## Reste à faire
- Câbler le tuteur dans l'API (état de tutorat dans `mika_session_states`) — décision de contrat front.
- Rédiger les `PlanGuidage` réels (humain) pour les notions PROVEN.
- Brancher `niveau_estime` sur le learning engine persistant (aujourd'hui : calcul local cohérent LE-06).
