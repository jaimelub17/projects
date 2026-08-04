@echo off
rem Explore the local DuckDB database with one-line SQL queries.
rem   usage:  query.cmd "select * from stg_orders limit 5"
rem Opens the database READ-ONLY -- exploration can never change the data.
rem Use single quotes for SQL strings: where event_type = 'signup'
"%~dp0venv\Scripts\python.exe" -c "import sys, duckdb; con = duckdb.connect(r'%~dp0dbt\oura_scorecard.duckdb', read_only=True); print(con.sql(sys.argv[1]))" %1
