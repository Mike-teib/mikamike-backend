# MikaMike — déploiement frontend micro + PWA

## Portée stricte

Ce pack déploie uniquement le frontend élève validé par la CI : `index.html`, `app.js`, `styles.css`, `manifest.webmanifest`, `service-worker.js`, `native-bridge.js` et les deux icônes MikaMike.

Destination production connue : `/home/mike/mikamike/app/frontend/`.

Il **ne touche pas** à `parent.html`, `parent.js`, `parent.css`, `.well-known/`, au backend, à la base, à Caddy, au DNS ou à WordPress.

## Précheck obligatoire

Le VPS doit être relu avant écriture. Relever d’abord le SHA réel de `index.html` :

```bash
sha256sum /home/mike/mikamike/app/frontend/index.html
find /home/mike/mikamike/app/frontend -maxdepth 2 -type f -printf '%P\n' | sort
```

Le script refuse d’écrire si le SHA a changé entre le précheck et l’activation.

## Exécution

```bash
sudo bash ops/deploy_frontend_micro_pwa.sh \
  --source /CHEMIN/checkout/frontend-vnext \
  --expected-index-sha SHA_RELEVE_AU_PRECHECK
```

Une sauvegarde est créée sous `/home/mike/mikamike/ops-backups/FRONTEND_MICRO_PWA_BEFORE_<UTC>/` avec SHA avant/après et `ROLLBACK.sh`.

Les smoke tests vérifient la racine, `app.js`, `native-bridge.js`, le manifest, le service worker et la santé API. Un échec déclenche le rollback automatique.

## Validation avant production

- web contract PASS ;
- Chromium 375 px PASS : micro + dictée + énoncé + PWA ;
- Android `assembleDebug` PASS ;
- iOS Xcode simulateur PASS ;
- APK debug produit.

Ce runbook ne constitue pas une activation production : le précheck VPS réel reste obligatoire.
