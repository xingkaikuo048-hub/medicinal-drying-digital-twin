$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Invoke-Validation([string]$RelativePath) {
    & $Python (Join-Path $ProjectRoot $RelativePath)
    if ($LASTEXITCODE -ne 0) {
        throw "Validation failed: $RelativePath (exit code $LASTEXITCODE)"
    }
}

& $Python -m pip check
if ($LASTEXITCODE -ne 0) { throw "pip check failed" }
& $Python -m pyoomph check compiler tccbox
if ($LASTEXITCODE -ne 0) { throw "tccbox check failed" }
Invoke-Validation "tests\test_pyoomph_smoke.py"
Invoke-Validation "tests\test_axisymmetric.py"
Invoke-Validation "tests\test_ale_import.py"
Invoke-Validation "tests\test_design_generation.py"
Invoke-Validation "tests\test_scenario_generation.py"
Invoke-Validation "tests\test_coupled_drying_mvp.py"
Invoke-Validation "tests\test_operating_conditions.py"
Invoke-Validation "tests\test_batch_runner.py"
Invoke-Validation "scripts\validate_dependencies.py"
Write-Host "ALL CORE VALIDATIONS PASSED"
