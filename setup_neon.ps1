param(
    [string]$DatabaseUrl = $env:NEON_DATABASE_URL
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:DATABASE_URL
}

if (-not $DatabaseUrl) {
    $DatabaseUrl = $env:DB_URL
}

if (-not $DatabaseUrl -or $DatabaseUrl -like '*USER:PASSWORD@HOST:5432/DB_NAME*') {
    Write-Host 'Set NEON_DATABASE_URL, DATABASE_URL, or DB_URL to your Neon connection string first.' -ForegroundColor Red
    exit 1
}

Write-Host 'Testing PostgreSQL connection...' -ForegroundColor Cyan
$env:DB_URL = $DatabaseUrl

& .\.venv\Scripts\python.exe .\seed.py
