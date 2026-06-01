# Optional: load .env into PowerShell for psql / terminal commands (Python loads .env via utils/db.py).
# Usage: . .\scripts\load_env.ps1
#
# From project root:
#   Copy-Item .env.example .env   # first time only
#   . .\scripts\load_env.ps1
#   python utils/db.py

$EnvFile = Join-Path $PSScriptRoot "..\.env" | Resolve-Path -ErrorAction SilentlyContinue

if (-not $EnvFile -or -not (Test-Path $EnvFile)) {
    throw "Missing .env - run: Copy-Item .env.example .env"
}

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $parts = $line -split "=", 2
    if ($parts.Count -lt 2) { return }
    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    Set-Item -Path "env:$name" -Value $value
}

Write-Host "Loaded .env (PGHOST=$env:PGHOST PGUSER=$env:PGUSER PGDATABASE=$env:PGDATABASE)"
