# Download default model weights (Windows). Linux/macOS: bash download_model.sh
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelDir = Join-Path $Here "model"
$ModelFile = Join-Path $ModelDir "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
$AppFile = Join-Path $Here "models\lite\model.gguf"
$Url = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $AppFile) | Out-Null

if (-not (Test-Path $ModelFile)) {
    Write-Host "Downloading $Url"
    Write-Host "  -> $ModelFile (~637 MB)"
    Invoke-WebRequest -Uri $Url -OutFile "$ModelFile.part"
    Move-Item -Force "$ModelFile.part" $ModelFile
    Write-Host "done: $ModelFile"
} else {
    Write-Host "Model already present at $ModelFile"
}

if (-not (Test-Path $AppFile) -or ((Get-FileHash $ModelFile).Hash -ne (Get-FileHash $AppFile).Hash)) {
    Copy-Item -Force $ModelFile $AppFile
    Write-Host "copied to app path: $AppFile"
}

Write-Host "Ready. Activate venv, then: streamlit run app.py"
