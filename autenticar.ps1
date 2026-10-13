$ErrorActionPreference = "Stop"
$Hf = Join-Path $PSScriptRoot ".venv/Scripts/hf.exe"
if (-not (Test-Path -LiteralPath $Hf)) { throw "Primero ejecuta .\instalar.ps1" }
$env:HF_HOME = Join-Path $PSScriptRoot ".cache/huggingface"
& $Hf auth login
exit $LASTEXITCODE
