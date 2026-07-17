param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Server = Join-Path $PSScriptRoot "run_sites_phase3b_local_server.py"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    Write-Error "Project environment .venv was not found. Follow the first-time setup in README.md."
    exit 2
}

$Version = & $Python -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
if ($LASTEXITCODE -ne 0 -or -not $Version.StartsWith("3.12.")) {
    Write-Error "Python 3.12 is required. Detected: $Version"
    exit 2
}

& $Python -c "import lunar_python, pydantic"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dependencies are incomplete. Run: .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt"
    exit 2
}

if ($CheckOnly) {
    Write-Host "READY: Python $Version and core dependencies are available."
    exit 0
}

Write-Host "Starting the local product at http://127.0.0.1:$Port/"
Write-Host "Keep this window open. Press Ctrl+C to stop."
& $Python $Server --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
