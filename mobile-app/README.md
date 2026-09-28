# MikaMike mobile — Android / iOS

Ce dossier empaquette le même `frontend-vnext` que le web avec Capacitor 8.

- Une seule base UI web/PWA/native.
- Micro natif Android/iOS via `@capgo/capacitor-speech-recognition`.
- Requêtes API natives vers `https://app.mikamike.fr/api/v1`.
- Aucune donnée élève embarquée.

## Génération
```bash
cd mobile-app
npm install
npm run prepare
npx cap add android
npx cap add ios
npm run sync
```

Les signatures Google Play / App Store, comptes développeur, fiches store et validation sur appareils physiques restent des portes de release séparées.
