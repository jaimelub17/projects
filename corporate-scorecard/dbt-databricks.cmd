@echo off
rem Runs any dbt command against the Databricks target, loading connection
rem details from the gitignored .env file first.
rem   usage:  dbt-databricks.cmd debug
rem           dbt-databricks.cmd build
rem           dbt-databricks.cmd seed --full-refresh
setlocal
if not exist "%~dp0.env" (
    echo No .env file found. Copy .env.example to .env and fill in your workspace values.
    exit /b 1
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%~dp0.env") do set "%%a=%%b"
set "DBT_PROFILES_DIR=%~dp0dbt"
cd /d "%~dp0dbt"
"%~dp0venv\Scripts\dbt.exe" %* --target databricks
