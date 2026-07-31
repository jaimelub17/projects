# Runs any dbt command against the Databricks target, loading connection
# details from the gitignored .env file first.
#   usage:  .\dbt-databricks.ps1 debug
#           .\dbt-databricks.ps1 build
#           .\dbt-databricks.ps1 seed --full-refresh
param([Parameter(ValueFromRemainingArguments = $true)]$dbtArgs)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) {
    Write-Host "No .env file found. Copy .env.example to .env and fill in your workspace values." -ForegroundColor Yellow
    exit 1
}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim())
    }
}
$env:DBT_PROFILES_DIR = Join-Path $root 'dbt'
Set-Location (Join-Path $root 'dbt')
& (Join-Path $root 'venv\Scripts\dbt.exe') @dbtArgs --target databricks
