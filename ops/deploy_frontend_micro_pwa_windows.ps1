param(
  [string]$Ref = "ui/mikamike-react-illustrated-v2-clean-20260927",
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

New-Item -ItemType Directory -Force -Path $work | Out-Null

try {
  Write-Host "[1/7] Récupération du ref validé $Ref"
  & git clone --quiet --depth 1 --branch $Ref "https://github.com/Mike-teib/mikamike-backend.git" $repoDir
  Assert-LastExitCode "git clone"

  $sourceDir = Join-Path $repoDir "frontend-vnext"
  $deployScript = Join-Path $repoDir "ops\deploy_frontend_micro_pwa.sh"
  if (-not (Test-Path $sourceDir)) { throw "frontend-vnext absent du ref $Ref" }
  if (-not (Test-Path $deployScript)) { throw "script de déploiement absent du ref $Ref" }

  $ssh = @("-i", $KeyPath, "-p", "$Port", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", $remote)
  $scp = @("-i", $KeyPath, "-P", "$Port", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes")

  Write-Host "[2/7] Précheck production en lecture seule"
  $shaLine = (& ssh @ssh "sha256sum /home/mike/mikamike/app/frontend/index.html").Trim()
  Assert-LastExitCode "précheck SHA"
  if ($shaLine -notmatch "^([0-9a-f]{64})\s") {
    throw "SHA production illisible : $shaLine"
  }
  $expectedSha = $Matches[1]
  Write-Host "index_sha_before=$expectedSha"

  Write-Host "[3/7] Création du staging distant"
  & ssh @ssh "mkdir -p '$remoteStage'"
  Assert-LastExitCode "création staging"

  Write-Host "[4/7] Copie ciblée frontend + script"
  & scp @scp -r $sourceDir "${remote}:$remoteStage/"
  Assert-LastExitCode "copie frontend"
  & scp @scp $deployScript "${remote}:$remoteStage/"
  Assert-LastExitCode "copie script"

  Write-Host "[5/7] Déploiement atomique avec sauvegarde et rollback"
  $remoteCommand = "sed -i 's/\r$//' '$remoteStage/deploy_frontend_micro_pwa.sh' && sudo -n bash '$remoteStage/deploy_frontend_micro_pwa.sh' --source '$remoteStage/frontend-vnext' --expected-index-sha '$expectedSha'"
  & ssh @ssh $remoteCommand
  Assert-LastExitCode "déploiement frontend"

  Write-Host "[6/7] Smoke tests publics"
  foreach ($url in @(
    "https://app.mikamike.fr/",
    "https://app.mikamike.fr/manifest.webmanifest",
    "https://app.mikamike.fr/service-worker.js"
  )) {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 20
    if ($response.StatusCode -ne 200) { throw "Smoke KO $url : $($response.StatusCode)" }
    Write-Host "200 $url"
  }

  Write-Host "[7/7] Nettoyage staging"
  & ssh @ssh "rm -rf '$remoteStage'"
  Assert-LastExitCode "nettoyage distant"

  Write-Host "DEPLOY_FRONTEND_MICRO_PWA_OK"
}
finally {
  if (Test-Path $work) {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
  }
}
