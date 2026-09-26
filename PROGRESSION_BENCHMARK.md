# PROGRESSION_BENCHMARK — progression multi-jours (LOT 15)

Moteur étudié : `app/curriculum/pedagogie/progression.py` (`diagnostiquer`, règles R1–R8), branché
sur l'API par `app/api/v1/mikamike/moteur.py` (`/exercices/soumettre`, `/escalier/etape`, fin de
tutorat Mika). Tests : `tests_cloud/test_bench_progression_jours.py` (moteur pur ET API réelle ;
les tentatives déjà journalisées sont re-datées en base avant chaque soumission). Le banc de
conversations du tuteur (LOT 10) est dans `tests_cloud/test_bench_mika_conversations.py`.

Aucun code applicatif modifié. Tout ce qui suit décrit le comportement **actuel**, vérifié par test.

## 1. Scénarios et niveaux obtenus, réponse par réponse

Notation : `S` réussite autonome, `F` échec autonome, `SA`/`FA` réussite/échec avec aide.
`J1`, `J2`, `J7`, `J30` = jour de la réponse. Niveau du moteur (libellé historique `etat_maitrise`
exposé par l'API entre parenthèses quand il diffère). Niveaux et libellés sont **identiques**
entre le moteur pur et l'API (`test_scenarios_via_api_identiques_au_moteur`).

| Scénario | Réponses | Niveaux après chaque réponse |
|---|---|---|
| S1 autonome régulier | J1 S, J1 S, J2 S, J2 S, J7 S, J30 S | NE, NE, **MAITRISEE** (J2, 3e réponse), MAITRISEE ×3 |
| S2 aidé régulier | mêmes jours, toutes SA | NE, NE, EN_COURS ×4 — libellé `ACQUIS_ASSISTE` partout |
| S3 échecs | J1 F×3, J2 F×2, J7 F, J30 F | NE, NE, NON_ACQUISE ×5 (`A_REVOIR`) |
| S4 alternance | (S, F) à J1, J2, J7, J30 | NE, NE, EN_COURS ×6 |
| S5 absence après maîtrise | J1 S×3, J2 S×2, *28 jours d'absence*, J30 F, F, S, S | NE, NE, EN_COURS (`ACQUIS_AUTONOME`), MAITRISEE ×2, **EN_COURS**, FRAGILE, EN_COURS, EN_COURS |
| S6 retour après échecs | J1 F×3, J2 F, J7 S×2, J30 S×3 | NE, NE, NON_ACQUISE ×2, FRAGILE ×2, EN_COURS, MAITRISEE ×2 |
| S7 aide puis autonomie | J1 SA×3, J2 S×2, J7 S, J30 S | NE, NE, EN_COURS ×3 (`ACQUIS_ASSISTE` puis `EN_COURS`), MAITRISEE ×2 (J7) |
| S8 même jour | J1 S×8 | NE, NE, EN_COURS ×6 (`ACQUIS_AUTONOME`) — jamais MAITRISEE |
| S9 échecs aidés puis réussites aidées | J1 FA×3, J2 FA, J7 SA, J30 SA | NE, NE, NON_ACQUISE ×2, FRAGILE ×2 |

(NE = NON_EVALUEE ; libellé historique `EN_COURS`/`INCONNU`/`ACQUIS_ASSISTE`, jamais « solide ».)

## 2. Propriétés vérifiées

| Propriété | Vérification | Résultat |
|---|---|---|
| Pas de diagnostic avant 3 réponses (R1) | scénarios + 300 historiques aléatoires multi-jours (graines 1000–1299) | ✅ |
| ≤ 1 cran par réponse (R7) | mêmes 300 historiques, entre deux réponses successives évaluées ; via l'API sur les 9 scénarios | ✅ |
| MAITRISEE ⇒ réussites autonomes sur ≥ 2 jours (R4) | chaque préfixe des 300 historiques ; S8 (même jour) jamais MAITRISEE, via l'API aussi | ✅ |
| Aide jamais plus favorable (R8) | 200 historiques multi-jours × chaque tentative basculée « avec aide » : niveau final jamais plus haut ; tout aidé ⇒ jamais MAITRISEE ; S2 ≤ S1 réponse par réponse via l'API | ✅ |
| Stabilité : alternance stricte S/F | 2 phases × 1/2/3/100 réponses par jour : **0 changement** une fois la fenêtre (6 réponses) remplie, ≤ 3 pendant le remplissage | ✅ |
| Stabilité : tout motif périodique de période 2–4 (S/F × aide) | après la fenêtre, jamais **3** réponses consécutives qui changent chacune le niveau (borne 2 atteinte) | ✅ |

**Justification des bornes de stabilité.** En alternance stricte, la fenêtre de 6 contient toujours
3 réussites (≥ la moitié : pas R6), jamais deux échecs autonomes consécutifs (pas R6), et seulement
2 réussites parmi les 4 dernières tentatives autonomes (pas R4) : EN_COURS est un point fixe, donc
0 changement est la bonne borne. Pour les autres motifs, un niveau qui change à *chaque* réponse
sur 3 réponses consécutives serait une bascule A→B→A→B illisible pour l'élève et le parent ; la
borne retenue (≤ 2 changements consécutifs) est atteinte par le motif S,S,F (§3, C2).

## 3. Constats

- **C1 — Aucune décroissance temporelle (longue absence).** Le moteur ne dépend que de l'ordre des
  réponses et du nombre de *jours distincts* ; une absence de 1, 30 ou 365 jours donne exactement
  les mêmes niveaux (`test_constat_aucune_decroissance_temporelle`). Le niveau stocké reste
  MAITRISEE pendant toute l'absence (il n'est recalculé qu'à la réponse suivante), et au retour un
  échec ne retire qu'un cran (S5 : MAITRISEE → EN_COURS → FRAGILE). Rien n'a été inventé : c'est
  une décision produit à prendre (R-1).
- **C2 — Oscillation à 2 réussites sur 3.** Un élève qui réussit 2 fois sur 3 (autonome, sur
  plusieurs jours) est MAITRISEE 2 réponses sur 3 : chaque échec retire la maîtrise, la réussite
  suivante la rend — 12 changements sur 18 réponses, indéfiniment
  (`test_constat_oscillation_deux_reussites_sur_trois`). Cause : R4 exige que la *dernière*
  tentative autonome soit réussie, sans hystérésis.
- **C3 — Maîtrise rapide.** Deux jours *consécutifs* suffisent : S1 atteint MAITRISEE dès la 3e
  réponse (J1, J1, J2). Le premier diagnostic peut sauter directement de NON_EVALUEE à MAITRISEE
  (R7 ne borne que les variations entre niveaux évalués).
- **C4 — Espacement compté sur tout l'historique borné (60 tentatives).** Une réussite unique il y
  a 29 jours + 3 réussites aujourd'hui = MAITRISEE, même avec des échecs entre-temps
  (`test_constat_espacement_compte_une_reussite_ancienne`). Conforme au commentaire du code
  (choix délibéré de session 5), à confirmer.
- **C5 — Échecs aidés.** Un échec aidé compte comme un échec (R8) ; une réussite aidée compte dans
  la proportion de réussites (S9 remonte de NON_ACQUISE à FRAGILE) mais jamais comme preuve
  autonome (S2 plafonne à EN_COURS / `ACQUIS_ASSISTE`).

## 4. Défaut trouvé (test `xfail(strict=True)`)

**PROG-01 — gravité moyenne — « jours distincts » = dates UTC.** Trois réussites en 3 minutes de
part et d'autre de minuit UTC donnent MAITRISEE : le « retest espacé » de R4 n'est pas garanti.
Minuit UTC = 1 h/2 h à Paris (rare) mais **20 h en Guadeloupe/Martinique, 21 h en Guyane** (heure
des devoirs). Reproduction minimale :

```python
minuit = datetime(2030, 3, 18, tzinfo=timezone.utc).timestamp()
h = [Tentative(True, False, minuit - 120), Tentative(True, False, minuit - 60),
     Tentative(True, False, minuit + 60)]
diagnostiquer(h).niveau  # MAITRISEE
```
Test : `test_defaut_maitrise_en_trois_minutes_autour_de_minuit_utc`.

Défauts du banc de conversations (LOT 10) qui touchent la progression (détail dans
`tests_cloud/test_bench_mika_conversations.py`) :
- **BANC-01 (moyenne)** : abandonner un tutorat aidé puis en démarrer un nouveau (autre
  `requete_id`) sur le même exercice remet `avec_aide` à false ; le tutorat aidé n'étant jamais
  terminé, il n'est jamais versé ⇒ une réussite « autonome » après avoir reçu de l'aide.
- **BANC-02 (faible à moyenne)** : trois réponses illisibles (« donne-moi la réponse », hors sujet)
  terminent en REVUE_HUMAINE avec `tentatives=0`, mais un **échec autonome** est versé dans
  `mika_tentatives` (3 tutorats de ce type ⇒ NON_ACQUISE).
- **BANC-03 (moyenne, contenu)** : sur « Écris 7/10 sous forme décimale », recopier `7/10` est une
  réussite autonome (pas de `forme_requise`), et `valider_exercice` ne le détecte pas.

## 5. Recommandations produit (à décider par Mike)

- **R-1 — Longue absence.** Décider s'il faut une décroissance : par ex. au-delà de N jours sans
  réponse, afficher MAITRISEE comme « à revérifier » et exiger une réussite autonome avant de la
  réafficher (sans toucher à l'historique). Le moteur n'en a pas aujourd'hui.
- **R-2 — Hystérésis.** Pour éviter C2 : ne retirer MAITRISEE qu'après 2 échecs autonomes sur les
  3 dernières réponses, ou exiger un taux ≥ 3/4 sur la fenêtre pour l'obtenir.
- **R-3 — Espacement réel.** Remplacer « ≥ 2 dates UTC distinctes » par un écart minimal (ex. ≥ 20 h
  entre la première et la dernière réussite autonome retenue) ou par des jours dans le fuseau de
  l'élève (corrige PROG-01 et la variante « 2 jours consécutifs » de C3).
- **R-4 — Fenêtre d'espacement.** Limiter les réussites qui prouvent l'espacement à une fenêtre de
  temps (ex. 30 jours) plutôt qu'aux 60 dernières tentatives (C4).
- **R-5 — Premier diagnostic.** Envisager de plafonner le premier diagnostic (3e réponse) à
  EN_COURS pour que MAITRISEE ne soit jamais le tout premier niveau affiché (C3).
- **R-6 — Tutorat.** Décider du sort d'un tutorat aidé abandonné (BANC-01 : le verser à
  l'expiration, ou reprendre le tutorat ouvert au `start`) et ne pas verser d'échec pour une fin
  en REVUE_HUMAINE sans réponse évaluée (BANC-02).

## 6. Exécution

```
pytest tests_cloud/test_bench_progression_jours.py tests_cloud/test_bench_mika_conversations.py -q
45 passed, 4 xfailed in ~37 s
```
