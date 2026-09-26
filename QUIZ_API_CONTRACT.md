# QUIZ_API_CONTRACT — `mika-quiz/1` (session 6)

Routes (préfixe `/api/v1/quiz`, action « apprentissage » : jeton de séance de l'élève en enforce) :

| méthode | chemin | corps / paramètres | réponse |
|---|---|---|---|
| POST | `/tentatives` | `student_pseudo_id`, `requete_id`, `notion_id`, `question_id?` | 201 (200 = rejeu) : `tentative_id`, `version`, `etat=EN_COURS`, `question` (vue publique) |
| POST | `/aide` | `student_pseudo_id`, `requete_id`, `tentative_id`, `version` | `avec_aide=true` (définitif), `aides`, QCM : `question.choix_elimine` |
| POST | `/repondre` | `student_pseudo_id`, `requete_id`, `tentative_id`, `version`, `reponse` | `etat=TERMINEE`, `resultat{verdict, est_correct, explication, correction}`, `progression`, `etat_maitrise` |
| GET | `/tentatives/{tentative_id}?student_id=` | — | état public (résultat seulement si TERMINEE) |

Réponse selon le type : `qcm` ⇒ index (entier) ; `vrai_faux` ⇒ booléen ; `reponse_courte` ⇒ texte
(≤ 500) ; `classement` ⇒ liste d'index (≤ 10) ; `association` ⇒ objet `{"<index gauche>": index droite}`.
Verdicts : `CORRECT`, `INCORRECT`, `A_REVOIR` (réponse indécidable : jamais versée à la progression).

Garanties (tests `tests_cloud/test_quiz_api.py`, mutants `quiz_*`) :
- aucune clé de correction ni explication avant soumission ; une seule soumission ;
- idempotence `(tentative_id, requete_id)` ; même clé + autre contenu ⇒ 409 ;
- `version` : verrou optimiste (409 `version_perimee`) ;
- propriété : tentative d'un autre élève ⇒ 404 (aucun oracle) ; autre pseudo ⇒ 403 (enforce) ;
- catalogue fail-closed : notion PROVEN et question validée (sinon 404 `quiz_indisponible`),
  contenu retiré pendant la tentative ⇒ 409 `contenu_retire` ; contenu fictif interdit en production ;
- progression : tentative versée à l'historique (`avec_aide` compris), niveau par le moteur R1–R8 ;
- limitation par élève (`QUIZ_ELEVE`, 120 requêtes / 10 min) ; minimisation : la réponse saisie
  n'est jamais stockée (seul le verdict) ; RGPD : tables exportées et effacées.
- D14 : sans objet (pas de phase de compréhension dans un quiz).

Erreurs : 401/403 (auth), 404 `quiz_indisponible` / `tentative_inconnue`, 409 `tentative_terminee`
/ `version_perimee` / `contenu_retire` / `requete_id_reutilise_avec_un_autre_contenu`, 422 validation
ou `reponse_hors_bornes`, 429 `trop_de_tentatives`.
