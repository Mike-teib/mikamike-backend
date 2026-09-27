# MikaMike — interface responsive V1

Branche isolée créée pendant l'indisponibilité de Claude Code. Ce dossier ne modifie pas le backend et n'est pas déployé automatiquement en production.

## Objectif

Une seule interface web responsive/PWA pour :
- PC / Mac ;
- iPhone / iPad ;
- Android / tablettes ;
- installation possible depuis le navigateur quand la plateforme le permet.

Palette : vert, turquoise, bleu, orange, blanc. **Aucun violet.**

## Ce qui est implémenté

- écran de connexion élève par code ;
- appel réel prévu vers `POST /api/v1/auth/eleve/jeton` ;
- shell élève : Accueil, Matières, Mika, Progrès ;
- navigation mobile type app ;
- écran parent de prévisualisation ;
- mode démonstration local `?demo=1` avec données fictives clairement marquées ;
- PWA : manifest + service worker ;
- accessibilité de base : skip-link, focus, labels, reduced-motion ;
- aucune API payante et aucune donnée réelle intégrée.

## Source de vérité backend

Créé à partir de la branche distante :
`cloud/mikamike-session6-production-hardening` (PR #8, SHA 894fa382...)

Contrats consultés :
- `frontend-contract/types.ts`
- `frontend-contract/validators.ts`
- `contrat_front/contrat.json`
- `QUIZ_API_CONTRACT.md`

## Limite volontaire importante

Le contrat visible ne fournit pas encore, dans les fichiers consultés, un endpoint clair permettant au front de parcourir :
`niveau → matière → chapitre → notion → exercice`.

L'interface n'invente donc pas ce catalogue. Les cartes matières sont prêtes visuellement mais le branchement réel reste en attente du contrat de navigation pédagogique.

De même, le dashboard parent accepte un `student_pseudo_id`, mais il faut confirmer le parcours de récupération durable des identifiants des enfants liés après reconnexion d'un parent. Ne pas bricoler ce point côté client.

## Test local

Servir ce dossier avec n'importe quel serveur statique.

- `/` : connexion réelle si le proxy `/api/v1` est disponible.
- `/?demo=1` : démonstration avec données fictives, sans appel au backend.
- `/parent.html` : aperçu de l'espace parent.

## Déploiement

Ne pas remplacer `app.mikamike.fr` tant que :
1. la revue n'est pas faite ;
2. le contrat de navigation pédagogique n'est pas confirmé ;
3. les tests responsive et accessibilité ne sont pas passés ;
4. le déploiement VPS et son rollback ne sont pas documentés.
