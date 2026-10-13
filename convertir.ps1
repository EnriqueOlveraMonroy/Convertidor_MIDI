# Examples: .\convertir.ps1 'C:\Musica\cancion.mp3' --duracion 30
$ErrorActionPreference = "Stop"
$Python = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Primero ejecuta .\instalar.ps1"
}
& $Python (Join-Path $PSScriptRoot "audio_a_midi.py") @args
exit $LASTEXITCODE
