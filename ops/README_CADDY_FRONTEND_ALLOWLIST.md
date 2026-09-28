# MikaMike — prérequis Caddy pour le frontend installable

## Pourquoi ce document existe

Le frontend installable MikaMike sert plusieurs fichiers statiques à la racine de `app.mikamike.fr`.
Une allowlist Caddy trop restrictive peut laisser fonctionner l'ancienne page principale tout en bloquant
les nouveaux fichiers du pack micro/PWA.

Ce document ne modifie pas Caddy. Il fixe le contrat à respecter lors d'une intervention VPS séparée.

## Chemins frontend à autoriser

Le matcher statique qui protège `app.mikamike.fr` doit laisser passer au minimum :

- `/`
- `/index.html`
- `/app.js`
- `/native-bridge.js`
- `/styles.css`
- `/manifest.webmanifest`
- `/service-worker.js`
- `/icons/*`

Les routes API continuent d'être traitées séparément par le backend. Ne pas élargir l'allowlist au-delà
du besoin sans audit.

## Piège du bind-mount du Caddyfile

Sur le VPS MikaMike, le Caddyfile peut être monté dans le conteneur comme **fichier unique**.

Conséquence importante :

- remplacer le fichier hôte par une opération qui change son inode (par exemple certains `mv`, `cp`
  atomiques ou éditeurs qui recréent le fichier) peut laisser le conteneur attaché à l'ancien inode ;
- un simple `caddy reload` peut alors recharger l'ancien contenu vu dans le conteneur, même si le fichier
  hôte paraît correct.

Avant écriture :

1. sauvegarder le Caddyfile ;
2. relever inode + SHA côté hôte ;
3. relever inode + contenu/sha vu depuis le conteneur ;
4. valider la configuration Caddy avant activation.

Après écriture :

1. vérifier que le conteneur voit réellement le nouveau contenu ;
2. si l'inode hôte a changé et que le conteneur voit l'ancien fichier, rétablir le bind-mount/recréer le
   conteneur de façon contrôlée selon le runbook VPS ;
3. valider la configuration ;
4. recharger Caddy ;
5. vérifier les URLs publiques.

## Vérifications minimales après changement

Toutes les requêtes suivantes doivent être testées en lecture seule :

```text
https://app.mikamike.fr/
https://app.mikamike.fr/app.js
https://app.mikamike.fr/native-bridge.js
https://app.mikamike.fr/styles.css
https://app.mikamike.fr/manifest.webmanifest
https://app.mikamike.fr/service-worker.js
https://app.mikamike.fr/api/health
```

Le contrôle frontend doit aussi confirmer :

- présence de `micCheckButton` ;
- présence de `getUserMedia` / `SpeechRecognition` ;
- présence de `MikaNativeSpeech` ;
- cache service worker attendu ;
- aucun impact sur les routes parent, backend ou données.

## Rollback

Le changement Caddy est un lot distinct du déploiement frontend.

En cas d'échec :

1. restaurer uniquement le Caddyfile depuis sa sauvegarde ;
2. vérifier que le conteneur lit bien la restauration ;
3. valider puis recharger Caddy ;
4. confirmer le retour HTTP de l'état précédent ;
5. ne pas modifier le frontend, la base ou le backend pour masquer un problème de matcher Caddy.

## Gouvernance

Une modification du Caddyfile est une opération production séparée. Elle doit être auditée et prouvée
indépendamment du déploiement des fichiers frontend.
