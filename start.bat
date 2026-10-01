@echo off
REM Windows start script: apply schema, then run waitress bound to port 8000.
cd /d "%~dp0"

if "%PORT%"=="" set PORT=8000

echo Applying database schema...
python apply_schema.py
if errorlevel 1 exit /b 1

echo Starting waitress on 0.0.0.0:%PORT%...
waitress-serve --host=0.0.0.0 --port=%PORT% wsgi:app
