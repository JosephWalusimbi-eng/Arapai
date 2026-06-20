# Run Arapai with the project venv (Windows)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
$venvStreamlit = Join-Path $PSScriptRoot "venv\Scripts\streamlit.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv..."
    python -m venv venv
}

Write-Host "Installing requirements..."
& $venvPython -m pip install -q -r requirements.txt

$model = Join-Path $PSScriptRoot "model\tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
if (-not (Test-Path $model)) {
    Write-Host "Downloading model..."
    & $venvPython scripts\download_models.py
}

Write-Host "Starting Streamlit (venv)..."
& $venvStreamlit run app.py
