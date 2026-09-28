param(
  [Parameter(Mandatory=$true)]
  [ValidatePattern("^[0-9a-f]{40}$")]
  [string]$ExpectedReleaseSha
)

$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "deploy_frontend_micro_pwa_windows.ps1"
if (-not (Test-Path -LiteralPath $runner)) {
  throw "Lanceur sécurisé introuvable : $runner"
}

& $runner -ExpectedReleaseSha $ExpectedReleaseSha
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
