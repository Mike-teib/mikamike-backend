# CLOUD_ARCHITECTURE — Architecture MikaMike backend (après mission cloud)

## Vue d'ensemble

```
main.py (FastAPI, /api/v1)
│
├── app/core/                     socle transverse
│   ├── security_config.py        secrets fail-closed (MIKA_PSEUDO_SECRET ≠ MIKA_JWT_SECRET)
│   └── validation.py             types d'entrée bornés (identifiants sans PII possible)
│
├── app/api/v1/                   COUCHE HTTP (état élève en SQLite, pseudonymisé HMAC)
│   ├── mikamike/                 exercices/soumettre, parents/dashboard, parcours/prochaine-etape
│   ├── escalier/                 orchestrateur « 8 étapes » (déterministe)
│   ├── parcours/                 graphe de compétences historique (NON sourcé)
│   ├── memory/                   répétition espacée
│   ├── session/                  heartbeat / sauvegarde / reconnexion (contrôle propriétaire)
│   ├── rgpd/                     export + effacement (registre TABLES_ELEVE exhaustif)
│   └── security/                 garde JWT fail-closed, validation OCR (non câblées)
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
│   ├── importers.py              import strict d'artefacts (manifest, checkpoint, PII)
│   ├── legacy.py                 migration honnête de l'existant (NOT_EVIDENCED)
│   ├── fixtures.py               référentiel FICTIF (jamais prouvable en prod)
│   └── pedagogie/                tuteur Mika (machine à états) + récurrence
│
├── paiement_comptes/             comptes (bcrypt, PyJWT) + Stripe (optionnel)
└── tools/                        CLI : content_check, rapports, secret_scan,
                                  verifier_manifest, mutation_check
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

## Flux cible (quand les sources officielles seront importées)

```
Artefacts locaux (registre, mappings, index, C02, V3, M01)
   └─ IMPORT_MANIFEST.json ─► importers.importer ─► Referentiel (VALIDATED)
          ├─► structure.valider_referentiel / text_quality / provenance
          ├─► backlog.calculer_backlog ─► NEED_EXERCISE / NEED_QUIZ
          └─► (génération humaine ou assistée) ─► exercices.creer_exercice / quiz.valider_question
                  └─► pedagogie.TuteurMika (PlanGuidage validé) ─► API élève (à câbler, cf. backlog)
```

## CI (`.github/workflows/ci.yml`)
- job **tests** : ruff, pytest (3 462 tests, hors ligne), `tools.content_check`, rapports ×2 + diff ;
- job **sécurité** : scan de secrets (arbre + historique), bandit (≥ moyenne), pip-audit.
Aucun secret réel requis (secrets de test factices).
