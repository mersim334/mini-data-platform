# One-command local run (Windows) — no Docker required.
# Usage (from project root):  .\scripts\run_all.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

function Get-PsqlPath {
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        return (Get-Command psql).Source
    }
    foreach ($p in @(
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe"
    )) {
        if (Test-Path $p) { return $p }
    }
    throw "psql not found. Install PostgreSQL 17 with Command Line Tools."
}

$Psql = Get-PsqlPath

function Invoke-PsqlFile {
    param([string]$Database, [string]$SqlFile)
    & $Psql -U $script:PgUser -h $script:PgHost -p $script:PgPort -d $Database -f $SqlFile
    if ($LASTEXITCODE -ne 0) { throw "psql failed: $SqlFile on $Database" }
}

Write-Host "=== Mini Data Platform — local run ===" -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env - set PGPASSWORD in .env, then run again." -ForegroundColor Yellow
        exit 1
    }
    throw "Missing .env"
}

. (Join-Path $PSScriptRoot "load_env.ps1")

if (-not $env:PGPASSWORD -or $env:PGPASSWORD -eq "your_password_here") {
    throw "Set a real PGPASSWORD in .env"
}

$script:PgHost = if ($env:PGHOST) { $env:PGHOST } else { "localhost" }
$script:PgUser = if ($env:PGUSER) { $env:PGUSER } else { "postgres" }
$script:PgPort = if ($env:PGPORT) { $env:PGPORT } else { "5432" }

Write-Host "=== 1/5 DB connection ===" -ForegroundColor Cyan
python -c "from utils.db import get_connection; get_connection().close(); print('DB connection OK')"

Write-Host "=== 2/5 Databases + DDL ===" -ForegroundColor Cyan
foreach ($db in @("ecommerce_bronze", "ecommerce_silver", "ecommerce_gold")) {
    $exists = & $Psql -U $PgUser -h $PgHost -p $PgPort -d postgres -tAc `
        "SELECT 1 FROM pg_database WHERE datname='$db'"
    if ($exists.Trim() -ne "1") {
        Write-Host "Creating $db"
        & $Psql -U $PgUser -h $PgHost -p $PgPort -d postgres -c "CREATE DATABASE $db;"
        if ($LASTEXITCODE -ne 0) { throw "CREATE DATABASE $db failed" }
    }
}

Invoke-PsqlFile "ecommerce_bronze" "sql/bronze_setup.sql"
Invoke-PsqlFile "ecommerce_bronze" "sql/bronze_add_customer_type.sql"
Invoke-PsqlFile "ecommerce_silver" "sql/silver_v2_setup.sql"
Invoke-PsqlFile "ecommerce_gold" "sql/gold_setup.sql"

Write-Host "=== 3/5 pip install ===" -ForegroundColor Cyan
python -m pip install -q -r requirements.txt

Write-Host "=== 4/5 Generate CSV ===" -ForegroundColor Cyan
python jobs/generate_test_data.py

Write-Host "=== 5/5 Pipeline ===" -ForegroundColor Cyan
python jobs/run_pipeline.py

if (Test-Path "jobs/health_check.py") {
    Write-Host "=== Health check ===" -ForegroundColor Cyan
    python jobs/health_check.py
}

Write-Host "`nDONE -> reports\latest_dashboard.html" -ForegroundColor Green
