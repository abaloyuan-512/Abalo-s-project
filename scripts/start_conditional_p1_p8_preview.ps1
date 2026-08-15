param(
    [ValidateRange(1, 65535)]
    [int]$EnginePort = 8000,
    [ValidateRange(1, 65535)]
    [int]$SitePort = 3000,
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
$SharedPython = "C:\Users\27622\.codex\worktrees\059f\Abalo-s-project\.venv\Scripts\python.exe"
$Python = if ($PythonPath) { $PythonPath } elseif (Test-Path -LiteralPath $LocalPython) { $LocalPython } else { $SharedPython }
$Node = "C:\Users\27622\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$SiteRoot = Join-Path $Root "sites\hosted-app"
$LocalVarsPath = Join-Path $SiteRoot ".dev.vars"
$EngineKey = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$EngineLog = Join-Path $env:TEMP "abalo-conditional-preview-$RunId-engine.log"
$EngineErrorLog = Join-Path $env:TEMP "abalo-conditional-preview-$RunId-engine-error.log"
$SiteLog = Join-Path $env:TEMP "abalo-conditional-preview-$RunId-site.log"
$SiteErrorLog = Join-Path $env:TEMP "abalo-conditional-preview-$RunId-site-error.log"

if (-not $env:OPENAI_API_KEY) {
    throw "OPENAI_API_KEY is required for the local conditional preview."
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "The shared project Python environment is unavailable."
}
if (-not (Test-Path -LiteralPath $Node -PathType Leaf)) {
    throw "The bundled Node runtime is unavailable."
}

$env:ABALO_ENGINE_KEY = $EngineKey
$env:ABALO_DIRECT_READING_V2_ENABLED = "true"
$env:ABALO_CONDITIONAL_INTAKE_ENABLED = "true"
$env:PYTHONPATH = Join-Path $Root "src"
$engine = Start-Process -FilePath $Python -ArgumentList @(
    "scripts/run_hosted_api.py", "--host", "127.0.0.1", "--port", [string]$EnginePort
) -WorkingDirectory $Root -WindowStyle Hidden -RedirectStandardOutput $EngineLog -RedirectStandardError $EngineErrorLog -PassThru

$env:PYTHON_ENGINE_URL = "http://127.0.0.1:$EnginePort"
$env:PYTHON_ENGINE_KEY = $EngineKey
$env:ABALO_DIRECT_READING_V2_PREVIEW_ENABLED = "true"
$env:ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED = "true"
$env:ABALO_LOCAL_PREVIEW_BYPASS_AUTH = "true"
$env:ABALO_PREVIEW_OWNER_EMAIL = "local-owner@example.com"
[IO.File]::WriteAllLines($LocalVarsPath, @(
    "PYTHON_ENGINE_URL=http://127.0.0.1:$EnginePort",
    "PYTHON_ENGINE_KEY=$EngineKey",
    "ABALO_DIRECT_READING_V2_PREVIEW_ENABLED=true",
    "ABALO_CONDITIONAL_INTAKE_PREVIEW_ENABLED=true",
    "ABALO_LOCAL_PREVIEW_BYPASS_AUTH=true",
    "ABALO_PREVIEW_OWNER_EMAIL=local-owner@example.com"
))
$site = Start-Process -FilePath $Node -ArgumentList @(
    "node_modules/vinext/dist/cli.js", "dev", "--hostname", "127.0.0.1", "--port", [string]$SitePort
) -WorkingDirectory $SiteRoot -WindowStyle Hidden -RedirectStandardOutput $SiteLog -RedirectStandardError $SiteErrorLog -PassThru

[pscustomobject]@{
    url = "http://127.0.0.1:$SitePort/"
    engine_pid = $engine.Id
    site_pid = $site.Id
    engine_log = $EngineLog
    engine_error_log = $EngineErrorLog
    site_log = $SiteLog
    site_error_log = $SiteErrorLog
    local_vars = $LocalVarsPath
    network_scope = "LOOPBACK_ONLY"
    deployment = $false
}
