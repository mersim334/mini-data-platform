# Run AFTER: gh auth login --web
# Usage: .\scripts\push_to_github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) { $gh = "gh" }

& $gh auth status | Out-Null

if (-not (git remote get-url origin 2>$null)) {
    & $gh repo create mini-data-platform `
        --public `
        --source=. `
        --remote=origin `
        --description "E-commerce ETL pipeline: Bronze-Silver-Gold with PostgreSQL and PySpark"
}

git push -u origin main
git push -u origin development
& $gh repo edit --default-branch development

Write-Host ""
Write-Host "Gotovo! Repozitorij:"
& $gh repo view --web 2>$null
& $gh repo view --json url -q ".url"
