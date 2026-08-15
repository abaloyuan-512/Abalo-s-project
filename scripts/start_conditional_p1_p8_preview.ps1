param(
    [ValidateRange(1, 65535)]
    [int]$EnginePort = 8890,
    [ValidateRange(1, 65535)]
    [int]$SitePort = 4180,
    [string]$PythonPath = "",
    [string]$NodePath = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
$Python = if ($PythonPath) { $PythonPath } else { $LocalPython }
$NodeCommand = if ($NodePath) { $null } else { Get-Command node.exe -ErrorAction SilentlyContinue }
$Node = if ($NodePath) { $NodePath } elseif ($NodeCommand) { $NodeCommand.Source } else { "" }
$SiteRoot = Join-Path $Root "sites\hosted-app"
$VinextCli = Join-Path $SiteRoot "node_modules\vinext\dist\cli.js"
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
    throw "Project Python was not found. Create .venv or pass -PythonPath explicitly."
}
if (-not $Node -or -not (Test-Path -LiteralPath $Node -PathType Leaf)) {
    throw "Node.js was not found. Add node.exe to PATH or pass -NodePath explicitly."
}
if (-not (Test-Path -LiteralPath $VinextCli -PathType Leaf)) {
    throw "Site dependencies are missing. Run pnpm install in sites/hosted-app first."
}
if (Get-NetTCPConnection -State Listen -LocalPort @($EnginePort, $SitePort) -ErrorAction SilentlyContinue) {
    throw "EnginePort or SitePort is already in use. Choose two free loopback ports."
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
try {
    $site = Start-Process -FilePath $Node -ArgumentList @(
        $VinextCli, "dev", "--hostname", "127.0.0.1", "--port", [string]$SitePort
    ) -WorkingDirectory $SiteRoot -WindowStyle Hidden -RedirectStandardOutput $SiteLog -RedirectStandardError $SiteErrorLog -PassThru

    $EngineReady = $false
    $SiteReady = $false
    for ($Attempt = 0; $Attempt -lt 60 -and -not ($EngineReady -and $SiteReady); $Attempt += 1) {
        Start-Sleep -Milliseconds 500
        if (-not $EngineReady) {
            try { $EngineReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$EnginePort/healthz" -TimeoutSec 2).StatusCode -eq 200 } catch { $EngineReady = $false }
        }
        if (-not $SiteReady) {
            try { $SiteReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$SitePort/" -TimeoutSec 3).StatusCode -eq 200 } catch { $SiteReady = $false }
        }
    }
    if (-not ($EngineReady -and $SiteReady)) { throw "Local preview did not become ready. Check the generated log files." }
} catch {
    if ($site -and -not $site.HasExited) { Stop-Process -Id $site.Id -Force }
    if ($engine -and -not $engine.HasExited) { Stop-Process -Id $engine.Id -Force }
    throw
}

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
