# MikaMike — déploiement frontend micro + PWA

## Portée stricte

Ce pack déploie uniquement le frontend élève validé par la CI : `index.html`, `app.js`, `styles.css`, `manifest.webmanifest`, `service-worker.js`, `native-bridge.js` et les deux icônes MikaMike.

Destination production connue : `/home/mike/mikamike/app/frontend/`.

Il **ne touche pas** à `parent.html`, `parent.js`, `parent.css`, `.well-known/`, au backend, à la base, à Caddy, au DNS ou à WordPress.

## Précheck obligatoire

L'utilisateur SSH `ubuntu` n'a pas la lecture directe de tous les fichiers du frontend. Le précheck doit donc utiliser `sudo -n` :

```bash
sudo -n sha256sum /home/mike/mikamike/app/frontend/index.html
sudo -n find /home/mike/mikamike/app/frontend -maxdepth 2 -type f -printf '%P\n' | sort
```

Le script refuse d'écrire si le SHA a changé entre le précheck et l'activation.

## Verrouillage de la release

Le lanceur Windows résout d'abord le HEAD de la branche release, puis récupère **ce SHA exact** et checkout en mode détaché. Il ne déploie donc jamais un commit apparu après le précheck Git.

Pour imposer un SHA attendu :

```powershell
.\ops\deploy_frontend_micro_pwa_windows.ps1 -ExpectedReleaseSha <SHA40>
```

Si la branche ne pointe plus vers ce SHA, le script s'arrête avant toute écriture.

## Exécution serveur

```bash
sudo bash ops/deploy_frontend_micro_pwa.sh \
  --source /CHEMIN/checkout/frontend-vnext \
  --expected-index-sha SHA_RELEVE_AU_PRECHECK
```

Une sauvegarde est créée sous `/home/mike/mikamike/ops-backups/FRONTEND_MICRO_PWA_BEFORE_<UTC>/` avec SHA avant/après et `ROLLBACK.sh`.

Les smoke tests serveur vérifient la racine, `app.js`, `native-bridge.js`, le manifest, le service worker et `/api/health` (avec fallback historique `/health`). Un échec déclenche le rollback automatique.

Le lanceur Windows exécute ensuite sa propre seconde série de smoke tests. **Si cette validation Windows échoue après une activation serveur réussie, il exécute lui aussi immédiatement le `ROLLBACK.sh` de la sauvegarde.**

### Particularité Windows PowerShell 5.1

L'appel SSH de l'étape de déploiement capture stdout et stderr avec `2>&1`. Sous Windows PowerShell 5.1, un message natif envoyé sur stderr peut être converti en erreur PowerShell si `$ErrorActionPreference = "Stop"`, même lorsque `ssh` termine avec le code 0.

Le lanceur passe donc temporairement `$ErrorActionPreference` à `Continue` autour de cet appel précis, restaure immédiatement la valeur précédente, puis décide du succès ou de l'échec **uniquement à partir de `$LASTEXITCODE`**. Les autres garde-fous restent sous `Stop`.

## Validation avant production

- web contract PASS ;
- Chromium 375 px PASS : permission micro + dictée + énoncé + PWA ;
- matrice téléphone / tablette / PC PASS ;
- Android AAB release PASS ;
- iOS archive release sans signature PASS ;
- pack de déploiement Bash/PowerShell PASS.

Le précheck VPS réel reste obligatoire avant chaque activation.
