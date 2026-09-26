# IMPORT_TEST_HARNESS_REPORT — Harnais d'import sur lots synthétiques (session cloud 3)

> **Aucun artefact réel n'est disponible ni inventé.** Le harnais fabrique des lots
> **synthétiques** (`[SYNTHÉTIQUE]`, source `fictive=True`, domaine `example.invalid`) qui ont la
> FORME attendue par IMPORT_CONTRACT.md. Ils éprouvent le pipeline, jamais la pédagogie ni le
> contenu officiel ; en mode production ils sont **refusés** (`SOURCE_FICTIVE_HORS_TEST`).

Code : `app/curriculum/harnais_import.py` · Tests : `tests_cloud/test_import_harnais.py` (40),
`tests_cloud/test_import_perf.py` (6).

## 1. Lot synthétique généré (`generer_lot`)
| Ordre | Chemin | Type | Rôle | Représente |
|---|---|---|---|---|
| 1 | `C02/resultats.bin` | opaque | c02 | C02 (format inconnu ⇒ empreinte seule) |
| 2 | `C02-6/resultats.bin` | opaque | c02_6 | C02-6 |
| 3 | `C02-6.1.jsonl` | index_contenus | c02_6_1 | C02-6.1 converti par le producteur |
| 4 | `M01_notions.jsonl` | registre_notions | m01_maths_cycle3 | M01 Maths cycle 3 (notions + preuves) |
| 5 | `ExtractionV3/rapport.json` | opaque | extraction_v3 | Extraction V3 |
| 6 | `sources/bo_synthetique.pdf` | source_document | source_pdf | PDF source (haché en flux) |
| 7 | `referentiel.json` | referentiel | referentiel | sources, programme, domaines, thèmes, chapitres |
| 8 | `mapping.jsonl` | mapping_notion_chapitre | mapping_chapitre_notion | rattachement notion → chapitre |
| 9 | `SHA256_SOURCE.txt` | manifest_sha256 | manifest_sha256 | manifest SHA-256 du chantier |

Manifest v2 écrit dans cet ordre (`ecrire_manifest_v2(..., trier=False)`), SHA-256 épinglé hors bande.
`executer_pipeline` rend l'état de chaque étape : manifest → C02 → C02-6 → C02-6.1 → M01 →
Extraction V3 → PDF → référentiel → mapping → manifest SHA256 → **provenance** → **mapping** → **backlog**.

## 2. Défauts injectés (chacun arrêté à la BONNE étape, sans contagion)
| Défaut | Statut | Étape | Raison |
|---|---|---|---|
| `sha_incorrect` (C02 modifié après signature) | FAILED | c02 | empreinte_differente |
| `fichier_manquant` | FAILED | mapping | fichier_manquant |
| `fichier_non_liste` | FAILED | manifest | fichiers_non_listes |
| `doublon_notion` (M01) | FAILED | m01 | notion_dupliquee |
| `doublon_manifest` | FAILED | manifest | fichier_liste_deux_fois |
| `doublon_contenu` (C02-6.1) | FAILED | c02_6_1 | schema_invalide |
| `mauvais_role` | FAILED | manifest | role_incompatible |
| `document_altere` (PDF) | FAILED | source_pdf | empreinte_differente |
| `json_invalide` (Extraction V3 déclarée canonique) | FAILED | extraction_v3 | erreur de parsing |
| `provenance_falsifiee` | REJECTED | provenance | HASH_EXTRAIT_INCOHERENT |
| `mapping_contradictoire` | REJECTED | mapping | MAPPING_CONTRADICTOIRE |
| `mapping_notion_inconnue` | REJECTED | mapping | MAPPING_NOTION_INCONNUE |
| manifest régénéré après falsification | FAILED | manifest | empreinte épinglée différente |

Aucun lot défectueux n'est publié (`test_defaut_jamais_publie`, ×12).

## 3. Import partiel, reprise, idempotence, rollback
| Scénario | Résultat |
|---|---|
| Un seul fichier FAILED | lot FAILED, aucun référentiel produit, les 8 autres fichiers restent DONE au checkpoint |
| Interruption (coupure pendant le PDF) puis relance avec checkpoint | 5 étapes marquées `reprise=true`, lot VALIDATED |
| Checkpoint d'un autre contenu (empreinte différente) | ignoré (`reprise=false`) |
| Import rejoué | résultat identique (référentiel, anomalies, opaques) |
| Republication du lot actif | refus `lot_deja_publie`, rien ne bouge |
| **Publication coupée entre copie et activation** | reprise : copie revalidée puis activée (S3-16, corrigé) |
| Reprise sur copie altérée | refus `copie_existante_invalide` |
| 25 publications puis 2 rollbacks | historique borné à 20 niveaux, rollbacks corrects (S3-16) |
| `ACTIF.json` imbriqué 5 000 niveaux | `DepotInvalide` (avant : `RecursionError` non rattrapée) |
| Rollback vers un lot altéré | refus, lot actif inchangé |

## 4. Performance / mémoire (corpus synthétique, `test_import_perf.py`)
Mesuré en local (tracemalloc actif) : 1 000 → 8 000 notions : 0,55 s → 5,4 s, pic 5,4 → 41,9 Mo,
**5,2 ko/notion constant** : croissance **linéaire** en temps et mémoire.
| Contrôle | Seuil testé |
|---|---|
| Temps ×4 notions | < ×8 (O(N²) donnerait ×16) |
| Mémoire ×4 notions | < ×5,5 ; < 16 ko/notion |
| Génération en flux (6 000 notions) | pic < 3 Mo |
| Lecture JSONL | jamais `read_text` d'un `.jsonl` (ligne à ligne, bornée) |
| Checkpoint | 1 écriture par fichier (pas par ligne) |
| Reprise sur 6 000 notions | VALIDATED, étapes déjà faites marquées `reprise=true` |
| Pipeline complet 6 000 notions | < 60 s (≈ 2 s mesurées) |

Limite assumée : la reprise **revalide** les fichiers déjà traités (re-hachage + re-parsing) :
fail-closed volontaire (un fichier peut avoir changé entre deux passes). Le checkpoint sert au
diagnostic et à la traçabilité, pas à sauter des contrôles.

## 5. Findings issus du harnais (CLOUD_REVIEW_SESSION2.md)
- **S3-15 (P1)** : un lot à source **fictive** était VALIDATED et publiable hors mode test.
- **S3-16 (P2)** : publication coupée impossible à reprendre ; chaîne `precedent` non bornée ;
  `ACTIF.json` trop imbriqué ⇒ exception non rattrapée.

Mutants dédiés (tous tués) : `source_fictive_publiable`, `republication_non_idempotente`,
`reprise_sans_revalidation`, `historique_non_borne`, `import_partiel_accepte`.

## 6. Quand les artefacts réels arriveront (R1/R2)
Remplacer `generer_lot` par le lot réel du chantier local, **sans changer les tests de pipeline** :
`executer_pipeline(<dossier réel>, <sha épinglé>, autoriser_fictif=False)` doit rendre VALIDATED.
Les adaptateurs typés C02 / Extraction V3 (R2) seront écrits à partir d'échantillons réels.
