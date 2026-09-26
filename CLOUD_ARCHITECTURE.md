# CLOUD_ARCHITECTURE — Architecture MikaMike backend (après sessions cloud 1 et 2)

## Vue d'ensemble

```
main.py (FastAPI, /api/v1)
│
├── app/core/                     socle transverse
│   ├── security_config.py        secrets fail-closed (MIKA_PSEUDO_SECRET ≠ MIKA_JWT_SECRET)
│   ├── validation.py             types d'entrée bornés (identifiants sans PII possible)
│   ├── pseudonymisation.py       [S2] HMAC élève : point unique (6 copies supprimées)
│   ├── auth.py                   [S2] jetons compte / séance élève, garde par route (AUTH_CONTRACT.md)
│   └── limites.py                [S2] taille max du corps des requêtes (413 avant lecture)
│
├── app/db/                       [S2] registre des schémas + migrations Alembic
│   ├── registre.py               metadata par base (mika, billing), sans effet de bord
│   └── migrations.py             upgrade / check au démarrage (MIKA_DB_INIT)
├── migrations/{mika,billing}/    [S2] révisions versionnées (CLOUD_DB_MIGRATION_PLAN.md)
│
├── app/api/v1/                   COUCHE HTTP (état élève en SQLite, pseudonymisé HMAC)
│   ├── mikamike/                 exercices/soumettre, parents/dashboard, parcours/prochaine-etape
│   ├── escalier/                 orchestrateur « 8 étapes » (déterministe)
│   ├── parcours/                 graphe de compétences historique (NON sourcé)
│   ├── memory/                   répétition espacée
│   ├── session/                  heartbeat / sauvegarde / reconnexion (contrôle propriétaire)
│   ├── rgpd/                     export + effacement (registre TABLES_ELEVE exhaustif, + tutorat, + liens)
│   ├── security/                 garde JWT historique (durcie), validation OCR (non câblées)
│   ├── auth/                     [S2] POST /auth/eleve/jeton (compte lié ⇒ jeton de séance élève)
│   └── tutorat/                  [S2] API tuteur Mika /mika/session/* (MIKA_API_CONTRACT.md)
│
├── app/curriculum/               CHAÎNE DE CONTENU (pure : ni base, ni réseau, ni LLM)
│   ├── model.py, ids.py          modèle canonique + identifiants stables + versions par rentrée
│   ├── provenance.py             preuve recalculée + verrou autorisation_generation
│   ├── structure.py              20 contrôles structurels
│   ├── text_quality.py           qualité du texte des notions (statuts TEXT_*)
│   ├── math_guard.py             préservation exacte des expressions mathématiques
│   ├── verifiers/                maths (SymPy), physique (unités), svt, technologie, ES, dispatch
│   ├── exercices.py, quiz.py     schémas + verrous de création
│   ├── dedup.py, audit.py        empreintes, quasi-doublons, orphelins
│   ├── backlog.py                indicateurs reproductibles
│   ├── importers.py              import strict d'artefacts (manifest v1/v2 épinglé, rôles, documents, PII)
│   ├── integrite.py              [S2] contrôles croisés ; `generables` fail-closed
│   ├── depot.py                  [S2] publication immuable, activation atomique, rollback
│   ├── legacy.py                 migration honnête de l'existant (NOT_EVIDENCED)
│   ├── fixtures.py               référentiel FICTIF (jamais prouvable en prod)
│   └── pedagogie/                tuteur Mika (machine à états) + récurrence
│
├── paiement_comptes/             comptes (bcrypt, PyJWT) + Stripe (optionnel) + liens compte↔élève [S2]
└── tools/                        CLI : content_check, rapports (--artefacts/--depot), secret_scan,
                                  verifier_manifest, mutation_check (40 mutants), db [S2]
```

## Principes

1. **Séparation contenu / applicatif.** `app/curriculum` ne dépend ni de FastAPI ni de SQLAlchemy.
   Il est testable en isolation et réutilisable par un pipeline d'ingestion hors ligne.
2. **Verrou unique de génération.** Toute création d'exercice/quiz passe par
   `provenance.autorisation_generation` : notion PROVEN, texte utilisable, chapitre non ambigu.
3. **Jamais VALID par défaut.** Tous les vérificateurs renvoient VALID / INVALID / AMBIGUOUS /
   NEEDS_HUMAN_REVIEW ; toute entrée non analysable ⇒ revue humaine.
4. **Déterminisme.** Mêmes données ⇒ mêmes identifiants, rapports, verdicts (vérifié en CI par
   double génération + `diff`).
5. **Privacy by design.** Identifiants élèves = HMAC ; alphabet des pseudo-ids sans PII possible ;
   effacement RGPD exhaustif par construction ; importeur qui refuse les données nominatives.
6. **Sécurité des entrées symboliques.** SymPy (`eval`) : liste blanche, espace de noms sans
   builtins, gardes anti-explosion.

## Session 2 — principes ajoutés
7. **Aucun effet de bord à l'import** : ni DDL (migrations explicites), ni lecture de secret
   par les paquets de modèles (`__init__` vides), ni routeur chargé par un simple import de paquet.
8. **Autorisation par construction** : chaque route élève appelle `garde.exiger(pseudo_id, action)` ;
   un test énumère le schéma OpenAPI et échoue si une route élève répond sans jeton.
9. **Contenu servi = contenu prouvé** : le tuteur ne sert qu'un exercice qui franchit le verrou
   (texte recalculé, preuve de la source du programme) avec un plan vérifiable côté serveur.
10. **Lots de contenu immuables** : publication revalidée, activation atomique, rollback revalidé.

## Flux cible (quand les sources officielles seront importées)

```
Artefacts locaux (registre, mappings, index, C02, V3, M01)
   └─ IMPORT_MANIFEST.json ─► importers.importer ─► Referentiel (VALIDATED)
          ├─► structure.valider_referentiel / text_quality / provenance
          ├─► backlog.calculer_backlog ─► NEED_EXERCISE / NEED_QUIZ
          ├─► integrite.verifier_integrite ─► generables (sinon aucune génération)
          ├─► depot.DepotContenu.publier ─► ACTIF.json (rollback possible)
          └─► (génération humaine ou assistée) ─► exercices.creer_exercice / quiz.valider_question
                  └─► depot.catalogue_depuis_import ─► CatalogueTutorat ─► /api/v1/mika/session/* (branché)
```

## CI (`.github/workflows/ci.yml`)
- job **tests** : ruff, pytest (hors ligne), `tools.content_check`, rapports ×2 + diff,
  migrations upgrade → status → downgrade base → upgrade sur SQLite jetables ;
- job **mutation** [S2] : `tools.mutation_check` (baseline verte exigée, mutants ciblés) ;
- job **sécurité** : scan de secrets (arbre + historique), bandit (≥ moyenne), pip-audit.
Aucun secret réel requis (secrets de test factices).
