@echo off
call "%~dp0.venv\Scripts\activate.bat"
cd /d "%~dp0"
echo Medicinal drying development environment is active.
echo Run all checks: powershell -ExecutionPolicy Bypass -File scripts\run_validation.ps1
cmd /k
