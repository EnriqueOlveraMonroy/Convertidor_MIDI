param(
    [string]$Python = "python",
    [switch]$CPU
)
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    & $Python -c "import sys; assert (3, 10) <= sys.version_info[:2] <= (3, 13), 'Usa Python 3.10 a 3.13 (recomendado: 3.12)'"
    if ($LASTEXITCODE -ne 0) { throw "No se encontró un Python compatible. Usa -Python con la ruta a python.exe." }
    & $Python -m venv --without-pip .venv
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno virtual." }
    # Use the base interpreter's pip to avoid ensurepip issues in embedded Python.
    & $Python -m pip --python .venv/Scripts/python.exe install --cache-dir .cache/pip pip
    if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar pip." }
    $TorchIndex = if ($CPU) { "https://download.pytorch.org/whl/cpu" } else { "https://download.pytorch.org/whl/cu128" }
    & ./.venv/Scripts/python.exe -m pip install --cache-dir .cache/pip "torch==2.11.0" "torchaudio==2.11.0" --index-url $TorchIndex
    if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar PyTorch." }
    & ./.venv/Scripts/python.exe -m pip install --cache-dir .cache/pip -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias." }
    & ./.venv/Scripts/python.exe audio_a_midi.py --diagnostico
    if ($LASTEXITCODE -ne 0) { throw "Falló el diagnóstico." }
} finally { Pop-Location }
