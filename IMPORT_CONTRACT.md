# IMPORT_CONTRACT — Import des artefacts réels (programmes, notions, C02, M01, Extraction V3…)

Code : `app/curriculum/importers.py` (import), `app/curriculum/integrite.py` (contrôles croisés),
`app/curriculum/depot.py` (publication / rollback). Tests : `tests_cloud/test_import_v2_integrite.py`,
`tests_cloud/test_review_session1.py` (R2-04), `tests_cloud/test_backlog_audit_import.py`.

> **Aucun artefact réel n'est dans le dépôt.** Rien n'a été inventé : ce contrat décrit ce que
> l'importeur ACCEPTERA quand Mike fournira les artefacts du chantier local. Les formats internes
> de C02, C02-6, C02-6.1, M01 Maths Cycle 3 et Extraction V3 ne sont pas connus ici : ils entrent
> en **opaque** (empreinte vérifiée, non interprétés) ou **convertis par le producteur** vers un
> type canonique ci-dessous.

## 1. Principe fail-closed
- Tout fichier du lot est listé dans le manifest, avec empreinte **et** taille ; fichier non listé,
  manquant, modifié, hors du dossier (y compris via lien symbolique) ⇒ `FAILED`.
- Le manifest v2 est **épinglé hors bande** : son SHA-256 est transmis par un canal distinct
  (message à Mike, ticket…) et passé à l'import. Un manifest régénéré après falsification est refusé.
- Toute erreur de contenu (JSON invalide ou trop imbriqué, schéma, PII, ligne > 1 M caractères,
  encodage) ⇒ `FAILED` avec fichier, ligne et raison — jamais d'exception, jamais d'import partiel.
- `VALIDATED` seulement si **l'intégrité croisée est démontrée** (0 anomalie) ; sinon `REJECTED`
  avec la liste des anomalies. Aucune génération (exercice, quiz, tutorat) sans `VALIDATED`.

## 2. Manifest v2 (`IMPORT_MANIFEST.json`)
```json
{
  "version": 2,
  "lot_id": "c02-6-1-maths-cycle3-2026",          // [a-z0-9-]{3,64}
  "producteur": "chantier local Mike",
  "date": "2026-10-01",
  "fichiers": [
    {"chemin": "sources/BO_cycle3_maths.pdf", "sha256": "<64 hex>", "taille": 1234567,
     "type": "source_document", "role": "programme_officiel"},
    {"chemin": "SHA256_SOURCE.txt", "sha256": "…", "taille": 812, "type": "manifest_sha256", "role": "manifest_sha256"},
    {"chemin": "referentiel.json", "sha256": "…", "taille": 99, "type": "referentiel", "role": "referentiel"},
    {"chemin": "notions_M01.jsonl", "sha256": "…", "taille": 99, "type": "registre_notions", "role": "m01_maths_cycle3"},
    {"chemin": "mapping.jsonl", "sha256": "…", "taille": 99, "type": "mapping_notion_chapitre", "role": "mapping_chapitre_notion"},
    {"chemin": "exercices.jsonl", "sha256": "…", "taille": 99, "type": "index_contenus", "role": "index_exercices"},
    {"chemin": "quiz.jsonl", "sha256": "…", "taille": 99, "type": "index_contenus", "role": "index_quiz"},
    {"chemin": "plans.jsonl", "sha256": "…", "taille": 99, "type": "plans_guidage", "role": "plans_guidage"},
    {"chemin": "C02-6.1/resultats.xlsx", "sha256": "…", "taille": 99, "type": "opaque", "role": "c02_6_1"},
    {"chemin": "ExtractionV3/rapport.json", "sha256": "…", "taille": 99, "type": "opaque", "role": "extraction_v3"}
  ]
}
```
Le producteur génère le manifest avec `ecrire_manifest_v2(...)`, qui renvoie le SHA-256 à épingler.
Le manifest v1 (session 1, sans taille ni rôle ni épinglage) reste lisible pour compatibilité.

## 3. Types de fichiers
| Type | Format | Validation |
|---|---|---|
| `referentiel` | JSON ≤ 50 Mo : objet `Referentiel` (sources, programmes, domaines, thèmes, chapitres, notions — CLOUD_DATA_MODEL.md) | schéma strict (`extra=forbid`), PII |
| `registre_notions` | JSONL : une `Notion` par ligne | schéma, doublon d'ID, PII, lecture en flux |
| `mapping_notion_chapitre` | JSONL `{"notion_id", "chapitre_id"}` | notion/chapitre existants, **contradiction** détectée |
| `index_contenus` | JSONL `{"kind": "exercice"\|"quiz", "data": {…}}` | schémas `Exercice` / `QuestionQuiz` puis intégrité |
| `plans_guidage` | JSONL `{"exercice_id", "plan": PlanGuidage}` | schéma, doublon, exercice existant, pas de fuite, **clé de compréhension obligatoire** |
| `source_document` | tout binaire (PDF…) ≤ 500 Mo | haché **en flux**, jamais chargé ni interprété ; son SHA doit égaler `SourceOfficielle.sha256_document` |
| `manifest_sha256` | lignes `HASH␣␣chemin` (format `SHA256_*.txt`, BOM et `\` Windows tolérés) | chaque entrée = fichier du lot à empreinte identique ; vide ⇒ refus |
| `opaque` | quelconque | empreinte seulement ; statut `OPAQUE_A_MAPPER` |

## 4. Rôles (provenance) et types admis
| Rôle | Types admis |
|---|---|
| `programme_officiel`, `source_pdf` | `source_document` |
| `referentiel` / `registre_notions` / `mapping_chapitre_notion` | type homonyme |
| `index_exercices`, `index_quiz` | `index_contenus` |
| `plans_guidage` | `plans_guidage` |
| `manifest_sha256` | `manifest_sha256` |
| `rapport` | `opaque` |
| `c02`, `c02_6`, `c02_6_1`, `m01_maths_cycle3`, `extraction_v3` | `opaque` **ou** un type canonique (si le producteur les a convertis) |

Rôle inconnu ou incompatible ⇒ `FAILED` (`role_incompatible`).

## 5. Contrôles d'intégrité croisés (`integrite.verifier_integrite`)
Structure (20 contrôles de `structure.py` : programme/chapitre/notion, matière×niveau, chevauchement
de versions, prérequis, cycles, doublons, texte suspect) **plus** :
| Code | Contrôle |
|---|---|
| `SOURCE_DOCUMENT_ABSENT` | source non fictive dont le document n'est pas dans le lot (v2) — **bloque tout le lot** |
| `PREUVE_SOURCE_AUTRE_PROGRAMME` | preuve tirée d'une autre source que celle du programme de la notion |
| `HASH_EXTRAIT_INCOHERENT` | SHA-256 de l'extrait verbatim ≠ extrait (source falsifiée) |
| `TEXTE_DECLARE_INCOHERENT` | statut de texte déclaré EXACT/RECOVERED mais recalcul tronqué/fragmenté/contaminé |
| `PROGRAMME_HORS_RENTREE` | `--rentree` fournie et programme non en vigueur |
| `EXERCICE_INVALIDE` | notion inconnue / non prouvée, matière, niveau, programme, chapitre, source, prérequis, fuite, réponse non vérifiable, doublon exact ou équivalent |
| `QUIZ_INVALIDE` | cohérences + double bonne réponse, distracteur indécidable, fuite… |
| `CONTENU_ID_DUPLIQUE` | même identifiant pour deux contenus — **bloque tout le lot** |
| `PLAN_INVALIDE`, `PLAN_SANS_EXERCICE` | plan qui divulgue la réponse, sans clé de compréhension, orphelin |
| `IMPORT_NOTION_EN_CONFLIT`, `MAPPING_*` | fusion référentiel / registre / mappings |

`generables` = notions PROVEN, texte recalculé utilisable, **non touchées** par une anomalie (ni
elles, ni leur chapitre, ni leur programme, ni leurs contenus). Anomalie globale ⇒ ensemble vide.

## 6. Publication et rollback (`depot.py`)
```
<racine>/lots/<lot_id>-<sha8>/   copie immuable (revalidée sur le disque de destination)
<racine>/ACTIF.json              lot actif + empreinte épinglée + lot précédent (écriture atomique)
<racine>/HISTORIQUE.jsonl        journal append-only
```
- `publier(dossier, sha)` : import épinglé → `VALIDATED` requis → copie → revalidation → activation
  atomique. Lot invalide ⇒ **rien** n'est copié ni activé. Lot déjà publié ⇒ refus (jamais écrasé).
- `rollback()` : revalide puis réactive le lot précédent ; refus s'il n'y en a pas ou s'il est altéré.
- `charger_actif()` : ré-importe le lot actif avec son empreinte : une altération sur disque après
  publication ⇒ **refus de servir** (`DepotInvalide`).
- La base élève n'est jamais modifiée par un import (contenu et données élèves sont séparés) :
  aucun rollback de base n'est nécessaire pour revenir à un lot précédent.

## 7. Procédure prévue avec les artefacts réels (prochaine session, avec Mike)
1. Mike dépose les artefacts dans un dossier local hors dépôt (jamais commités).
2. Convertir ce qui est canonique (référentiel/notions/mappings/index) ; laisser C02/V3 en opaque.
3. `ecrire_manifest_v2(...)` ⇒ SHA épinglé communiqué séparément.
4. `python -m tools.rapports --artefacts <dossier> --sha-manifest <sha> --rentree 2026` : lire les
   anomalies, corriger à la source, recommencer jusqu'à `VALIDATED`.
5. `DepotContenu(<racine>).publier(<dossier>, <sha>)` ⇒ `python -m tools.rapports --depot <racine>`.
6. Écrire les adaptateurs typés C02 / Extraction V3 **à partir d'échantillons réels** (R2).

## 8. Import en deux temps (session 4) — prêt pour les artefacts réels
```
python -m tools.import_lot simuler --dossier <lot> --sha <sha-épinglé> --depot <racine> --rentree 2026 --sortie <dir>
   → rapport_import.json / .md : statut, fichiers, métriques (notions par statut de preuve, par
     matière/niveau, contenus, opaques par rôle, anomalies par code, générables), QUARANTAINE
     (toute notion non PROVEN ou touchée par une anomalie, avec raisons), COMPARAISON avec le lot
     actif (notions/contenus ajoutés, retirés, modifiés par empreinte ; changements de preuve),
     avertissement LOT_IDENTIQUE_AU_LOT_ACTIF (import répété). N'écrit RIEN d'autre.
python -m tools.import_lot publier ... --confirmer      → n'active que si VALIDATED
python -m tools.publication etat|publier|retirer ...    → garde READY_FOR_PUBLICATION / PUBLISHED
```
État des artefacts réels : **WAITING_FOR_ARTIFACT** (C02, C02-6, C02-6.1, M01, Extraction V3, PDF
officiels, index, manifests). Tests : `tests_cloud/test_rapport_import.py`, `test_publication.py`,
`test_import_harnais.py`.
