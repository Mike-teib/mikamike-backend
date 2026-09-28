param(
  [string]$Ref = "ui/mikamike-react-illustrated-v2-clean-20260927",
  [string]$ExpectedReleaseSha = "",
  [string]$VpsHost = "79.137.79.200",
  [int]$Port = 2222,
  [string]$VpsUser = "ubuntu",
  [string]$KeyPath = "$HOME\.ssh\id_ed25519"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Assert-LastExitCode([string]$Step) {
  if ($LASTEXITCODE -ne 0) {
    throw "$Step a échoué (code $LASTEXITCODE)."
  }
}

if (-not (Test-Path -LiteralPath $KeyPath)) {
  throw "Clé SSH introuvable : $KeyPath"
}

$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$work = Join-Path $env:TEMP "mikamike-frontend-deploy-$stamp"
$repoDir = Join-Path $work "repo"
$remoteStage = "/tmp/mikamike-frontend-release-$stamp"
$remote = "$VpsUser@$VpsHost"
$repoUrl = "https://github.com/Mike-teib/mikamike-backend.git"
$backupPath = $null
$deployed = $false

New-Item -ItemType Directory -Force -Path $work | Out-Null

try {
  Write-Host "[1/8] Résolution et verrouillage du commit release"
  $remoteLine = (& git ls-remote $repoUrl "refs/heads/$Ref").Trim()
  Assert-LastExitCode "git ls-remote"
  if ($remoteLine -notmatch "^([0-9a-f]{40})\s") {
    throw "Impossible de résoudre le SHA de $Ref : $remoteLine"
  }
  $releaseSha = $Matches[1]

  if ($ExpectedReleaseSha) {
    if ($ExpectedReleaseSha -notmatch "^[0-9a-f]{40}$") {
      throw "ExpectedReleaseSha invalide : $ExpectedReleaseSha"
    }
    if ($releaseSha -ne $ExpectedReleaseSha) {
      throw "STOP : le HEAD de $Ref vaut $releaseSha, attendu $ExpectedReleaseSha."
    }
  }
  Write-Host "release_sha=$releaseSha"

  Write-Host "[2/8] Checkout propre et détaché du SHA exact"
  & git init --quiet $repoDir
  Assert-LastExitCode "git init"
  & git -C $repoDir remote add origin $repoUrl
  Assert-LastExitCode "git remote add"
  & git -C $repoDir fetch --quiet --depth 1 origin $releaseSha
  Assert-LastExitCode "git fetch du SHA release"
  & git -C $repoDir checkout --quiet --detach FETCH_HEAD
  Assert-LastExitCode "git checkout détaché"
  $checkedOutSha = (& git -C $repoDir rev-parse HEAD).Trim()
  Assert-LastExitCode "git rev-parse HEAD"
  if ($checkedOutSha -ne $releaseSha) {
    throw "STOP : checkout=$checkedOutSha, release=$releaseSha"
  }

  $sourceDir = Join-Path $repoDir "frontend-vnext"
  $deployScript = Join-Path $repoDir "ops\deploy_frontend_micro_pwa.sh"
  if (-not (Test-Path $sourceDir)) { throw "frontend-vnext absent du commit $releaseSha" }
  if (-not (Test-Path $deployScript)) { throw "script de déploiement absent du commit $releaseSha" }

  $ssh = @("-i", $KeyPath, "-p", "$Port", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", $remote)
  $scp = @("-i", $KeyPath, "-P", "$Port", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes")

  Write-Host "[3/8] Précheck production en lecture seule"
  $shaLine = (& ssh @ssh "sudo -n sha256sum /home/mike/mikamike/app/frontend/index.html").Trim()
  Assert-LastExitCode "précheck SHA avec sudo -n"
  if ($shaLine -notmatch "^([0-9a-f]{64})\s") {
    throw "SHA production illisible : $shaLine"
  }
  $expectedSha = $Matches[1]
  Write-Host "index_sha_before=$expectedSha"

  Write-Host "[4/8] Inventaire production en lecture seule"
  & ssh @ssh "sudo -n find /home/mike/mikamike/app/frontend -maxdepth 2 -type f -printf '%P\n' | sort"
  Assert-LastExitCode "inventaire frontend"

  Write-Host "[5/8] Création du staging distant"
  & ssh @ssh "mkdir -p '$remoteStage'"
  Assert-LastExitCode "création staging"

  Write-Host "[6/8] Copie ciblée frontend + script"
  & scp @scp -r $sourceDir "${remote}:$remoteStage/"
  Assert-LastExitCode "copie frontend"
  & scp @scp $deployScript "${remote}:$remoteStage/"
  Assert-LastExitCode "copie script"

  Write-Host "[7/8] Déploiement atomique avec sauvegarde et rollback serveur"
  $remoteCommand = "sed -i 's/\r$//' '$remoteStage/deploy_frontend_micro_pwa.sh' && sudo -n bash '$remoteStage/deploy_frontend_micro_pwa.sh' --source '$remoteStage/frontend-vnext' --expected-index-sha '$expectedSha'"
  $deployOutput = @(& ssh @ssh $remoteCommand 2>&1)
  $deployExit = $LASTEXITCODE
  $deployOutput | ForEach-Object { Write-Host $_ }
  if ($deployExit -ne 0) {
    throw "Déploiement serveur échoué (code $deployExit). Le script serveur gère son rollback sur échec interne."
  }

  foreach ($line in $deployOutput) {
    if ("$line" -match "^backup=(.+)$") {
      $backupPath = $Matches[1].Trim()
    }
  }
  if (-not $backupPath) {
    throw "Déploiement annoncé réussi mais chemin de sauvegarde absent ; arrêt avant validation."
  }
  $deployed = $true
  Write-Host "backup_path=$backupPath"
  Write-Host "rollback_path=$backupPath/ROLLBACK.sh"

  Write-Host "[8/8] Smoke tests publics Windows"
  try {
    foreach ($url in @(
      "https://app.mikamike.fr/",
      "https://app.mikamike.fr/app.js",
      "https://app.mikamike.fr/native-bridge.js",
      "https://app.mikamike.fr/manifest.webmanifest",
      "https://app.mikamike.fr/service-worker.js",
      "https://app.mikamike.fr/api/health"
    )) {
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
      if ($response.StatusCode -ne 200) {
        throw "Smoke KO $url : $($response.StatusCode)"
      }
      Write-Host "200 $url"
    }
  }
  catch {
    if ($deployed -and $backupPath) {
      Write-Warning "Smoke Windows en échec : rollback distant immédiat."
      & ssh @ssh "sudo -n bash '$backupPath/ROLLBACK.sh'"
      $rollbackExit = $LASTEXITCODE
      if ($rollbackExit -ne 0) {
        throw "SMOKE_FAIL puis ROLLBACK_FAIL (code $rollbackExit). Intervention manuelle requise. Erreur initiale : $($_.Exception.Message)"
      }
      Write-Host "ROLLBACK_OK $backupPath"
      $deployed = $false
      throw "SMOKE_FAIL -> rollback exécuté. $($_.Exception.Message)"
    }
    throw
  }

  $indexAfterLine = (& ssh @ssh "sudo -n sha256sum /home/mike/mikamike/app/frontend/index.html").Trim()
  Assert-LastExitCode "SHA final"
  if ($indexAfterLine -notmatch "^([0-9a-f]{64})\s") {
    throw "SHA final illisible : $indexAfterLine"
  }
  Write-Host "index_sha_after=$($Matches[1])"

  & ssh @ssh "rm -rf '$remoteStage'"
  Assert-LastExitCode "nettoyage staging"

  Write-Host "DEPLOY_FRONTEND_MICRO_PWA_OK"
}
finally {
  if (Test-Path $work) {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  }
}
