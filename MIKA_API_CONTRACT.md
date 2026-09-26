# MIKA_API_CONTRACT — API du tuteur Mika, contrat `mika-tutorat/1`

Code : `app/api/v1/tutorat/{router,service,contenu,store}.py` · moteur : `app/curriculum/pedagogie/tuteur.py`
Tests : `tests_cloud/test_mika_api.py` (106 tests, dont 81 séquences de propriétés).
**Branché** dans `main.py` sous `/api/v1` : le contrat existant n'est pas modifié (routes nouvelles
uniquement). Aucune dépendance LLM, aucun appel réseau.

## 1. Routes
| Méthode | Chemin | Corps / paramètres | Succès |
|---|---|---|---|
| POST | `/api/v1/mika/session/start` | `student_pseudo_id`, `requete_id`, `exercice_id` | 201 (créé) · 200 (rejeu) |
| POST | `/api/v1/mika/session/answer` | `student_pseudo_id`, `requete_id`, `tutorat_id`, `version`, `reponse` (≤ 500) | 200 |
| POST | `/api/v1/mika/session/help` | `student_pseudo_id`, `requete_id`, `tutorat_id`, `version` | 200 |
| POST | `/api/v1/mika/session/comprehension` | idem + `reponse` | 200 |
| GET | `/api/v1/mika/session/{tutorat_id}?student_id=` | — | 200 |

Corps stricts (`extra="forbid"`), identifiants à alphabet restreint, `tutorat_id` = 32 hex,
`version` ∈ [1, 10 000]. Autorisation : action **apprentissage** (AUTH_CONTRACT.md) — en mode
`enforce`, jeton élève du même `student_pseudo_id`.

## 2. Réponse (toutes les routes)
```json
{
  "contract_version": "mika-tutorat/1",
  "tutorat_id": "…32 hex…",
  "version": 3,
  "exercice_id": "exo:…",
  "derniere_action": "DONNER_INDICE",
  "etat": {
    "tentatives": 1, "indices_donnes": 1, "questions_posees": 1, "methodes_donnees": 0,
    "niveau_aide": 2, "avec_aide": true, "resolu": false, "termine": false,
    "attend_comprehension": false, "comprehension_verifiee": null,
    "niveau_estime": "INCONNU", "prerequis_manquant": null, "messages": ["…"]
  },
  "reponse": {"action": "DONNER_INDICE", "message": "Indice : … Réessaie.",
              "difficulte_proposee": 3, "exercice_id": null, "notion_cible": null},
  "rejeu": false
}
```
`GET` renvoie la même structure sans `reponse` ni `rejeu`. **Jamais** : réponse attendue, clé de
compréhension, aides non encore données, correction avant épuisement des aides.

## 3. Machine à états (explicite, persistée)
Actions : `PRESENTER_EXERCICE`, `REMEDIER_PREREQUIS`, `IDENTIFIER_BLOCAGE`,
`QUESTION_INTERMEDIAIRE`, `DONNER_INDICE`, `LAISSER_REESSAYER`, `AUTRE_METHODE`,
`VERIFIER_COMPREHENSION`, `CONSOLIDATION`, `DEMANDER_REFORMULATION`, `CORRECTION_COMMENTEE`,
`REVUE_HUMAINE` (détail : CLOUD_PEDAGOGY_MIKA.md).

| Règle | Garantie (testée) |
|---|---|
| Aucune solution immédiate | la correction commentée n'arrive qu'après questions → indices → méthodes ; aucune graphie équivalente de la réponse (`0,7`, `0.70`, `7/10` hors énoncé) dans les messages antérieurs |
| Aide graduée | ordre fixe : question intermédiaire, indices du plus léger au plus explicite, autres méthodes, correction |
| Prérequis | prérequis non solide (`ACQUIS_AUTONOME`/`MAITRISE`) ⇒ `REMEDIER_PREREQUIS`, tutorat terminé |
| `avec_aide` monotone | ne repasse jamais à `false` (invariant vérifié à chaque transition, 500 sinon) ; LE-06 : aidé ⇒ jamais `ACQUIS_AUTONOME` |
| Difficulté | `difficulte_proposee` non croissante quand l'aide augmente |
| Compréhension | seulement après `VERIFIER_COMPREHENSION` ; réponse **vérifiée côté serveur** contre `PlanGuidage.reponse_comprehension` (un plan sans clé n'est pas servi) |
| Réponse illisible | `DEMANDER_REFORMULATION` (non comptée comme erreur), puis `REVUE_HUMAINE` |
| Fin | tutorat terminé ⇒ une tentative versée au learning engine (`mika_tentatives`, `mika_etats`) |

## 4. Idempotence et concurrence
- `requete_id` (choisi par le client, unique par action) : rejouer **la même requête** renvoie la
  réponse enregistrée (`rejeu: true`) sans nouvelle transition ; même `requete_id` avec un autre
  contenu ⇒ **409** `requete_id_reutilise_avec_un_autre_contenu`.
- `start` : `tutorat_id = SHA-256("start|" + HMAC(élève) + "|" + requete_id)[:32]` — un double envoi
  du démarrage ne crée pas deux tutorats ; deux élèves n'entrent jamais en collision.
- Verrou optimiste : `version` doit être la version courante, sinon **409**
  `{"code": "version_perimee", "version_courante": n}`. Mise à jour atomique
  (`UPDATE … WHERE version = v`) ; course sur le journal d'idempotence ⇒ rejeu.

## 5. Erreurs
| Code | `detail` | Cas |
|---|---|---|
| 401 / 403 | cf. AUTH_CONTRACT | jeton absent/invalide ; autre élève |
| 404 | `exercice_indisponible` | exercice inconnu, notion non PROVEN, plan invalide ou non vérifiable (raisons internes non divulguées) |
| 404 | `tutorat_inconnu` | inexistant **ou** appartenant à un autre élève (pas d'oracle) |
| 409 | `tutorat_termine`, `comprehension_non_demandee`, `comprehension_attendue`, `contenu_retire`, `version_perimee`, `requete_id_reutilise_avec_un_autre_contenu` | transitions invalides |
| 422 | — | validation (champ inconnu, longueur, format) |

## 6. Contenus servis (fail-closed)
`CatalogueTutorat` (`contenu.py`) ne sert un exercice que s'il passe `valider_exercice`
(notion PROVEN, texte **recalculé** utilisable, cohérences, vérificateur, anti-doublon) et si son
plan passe `valider_plan(..., exiger_cle_comprehension=True)`. **Catalogue par défaut vide** :
aucun contenu réel prouvé n'existe encore (artefacts absents) ⇒ `start` répond 404 en production
tant que l'import (IMPORT_CONTRACT.md, type `plans_guidage`) n'est pas fait. Contenu fictif
(`autoriser_fictif=True`) refusé si `MIKA_ENV=production`.

## 7. Stockage / RGPD
Tables `mika_tutorat_sessions` (état JSON, version, action, terminé) et `mika_tutorat_requetes`
(journal d'idempotence), migration `m0003_tutorat`, clé élève HMAC. Incluses dans l'export et
l'effacement RGPD.

## 8. Limites / décisions
- **R5** : les prérequis sont lus dans `mika_etats` par identifiant de notion ; les états
  historiques sont indexés par compétence legacy ⇒ un élève « neuf » est orienté en remédiation.
  Unification des identifiants à faire après import réel.
- **D7** (session 1) : ce contrat est une proposition backend ; à valider avec le front.
- Purge des tutorats anciens (rétention) : décision D13.
