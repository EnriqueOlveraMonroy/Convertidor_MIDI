"""Kaggle setup and result packaging; credentials stay in process memory."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile


GPU_CHECK = '''
import json
import torch
if not torch.cuda.is_available():
    raise SystemExit("GPU no disponible. Activa Accelerator > GPU en Kaggle y reinicia la sesión.")
try:
    x = torch.ones((32, 32), device="cuda")
    result = (x @ x).sum().item()
    torch.cuda.synchronize()
except Exception:
    raise SystemExit("PyTorch no puede calcular con esta GPU. Prueba GPU T4 x2 y reinicia la sesión.") from None
if result != 32768.0:
    raise SystemExit("La comprobación de cálculo CUDA falló.")
print(json.dumps({"torch": torch.__version__, "gpu": torch.cuda.get_device_name(0),
                  "vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)}))
'''


def run_checked(command: list[str], *, env: dict | None = None, cwd: Path | None = None) -> None:
    """Stream progress without placing tokens in command lines or exceptions."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace", env=env, cwd=cwd)
    try:
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
        code = process.wait()
    except BaseException:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    finally:
        if process.stdout is not None:
            process.stdout.close()
    if code:
        raise RuntimeError(f"El proceso terminó con código {code}. Revisa el mensaje anterior.")


def prepare_runtime(runtime_dir: Path) -> Path:
    """Reuse Kaggle's CUDA PyTorch in an isolated environment, without upgrading it."""
    if sys.version_info < (3, 10):
        raise RuntimeError("MuScriptor necesita Python 3.10 o posterior.")
    print("Comprobando la GPU antes de instalar o descargar modelos…", flush=True)
    run_checked([sys.executable, "-c", GPU_CHECK])
    versions = json.loads(subprocess.check_output([
        sys.executable, "-c",
        "import importlib.metadata as m, json; "
        "print(json.dumps({p:m.version(p) for p in ('torch','torchaudio','numpy')}))",
    ], text=True))
    runtime_dir = Path(runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    environment = runtime_dir / "venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        run_checked([sys.executable, "-m", "venv", "--system-site-packages", "--without-pip", str(environment)])
    constraints = runtime_dir / "constraints.txt"
    constraints.write_text("".join(f"{key}=={value}\n" for key, value in versions.items()), encoding="utf-8")
    run_checked([
        sys.executable, "-m", "pip", "--python", str(python), "install", "--disable-pip-version-check",
        "--constraint", str(constraints), "muscriptor==0.3.0", "mido>=1.3,<2",
        "imageio-ffmpeg>=0.6,<0.7", "huggingface-hub==2.2.0",
    ])
    run_checked([str(python), "-c", GPU_CHECK])
    run_checked([str(python), "-c", "import muscriptor, torchaudio, mido, imageio_ffmpeg; print('Dependencias listas.')"])
    return python


def find_audio(input_root: Path, selected: str = "") -> Path:
    """Auto-select a single audio file; require a choice when several exist."""
    if selected:
        source = Path(selected).expanduser()
        if not source.is_absolute():
            source = Path(input_root) / source
        if not source.is_file():
            raise ValueError(f"No existe el audio: {source}")
        return source.resolve()
    extensions = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".aiff", ".aif", ".opus"}
    files = sorted(path for path in Path(input_root).rglob("*") if path.is_file() and path.suffix.lower() in extensions)
    if not files:
        raise ValueError("No hay canciones en /kaggle/input. Añade un dataset privado con tu audio mediante Add Input.")
    if len(files) != 1:
        candidates = "\n".join(str(path) for path in files[:30])
        raise ValueError("Hay varias canciones. Copia una ruta en ARCHIVO_AUDIO:\n" + candidates)
    return files[0].resolve()


def conversion_command(python: Path, project: Path, source: Path, destination: Path, *,
                       model: str = "medium", start: float = 0.0, duration: float | None = None) -> list[str]:
    command = [str(python), "-u", str(Path(project) / "audio_a_midi.py"), str(source),
               "--salida", str(destination), "--modelo", model, "--dispositivo", "cuda",
               "--inicio", str(start)]
    if duration is not None:
        command.extend(["--duracion", str(duration)])
    return command


def new_destination(project: Path, source: Path, label: str) -> Path:
    from audio_a_midi import safe_name
    return Path(project) / "resultados" / f"{safe_name(Path(source).stem)}_{label}_{uuid.uuid4().hex[:10]}"


def package_result(destination: Path) -> Path:
    """Validate MIDI and zip an explicit allowlist; never include audio or caches."""
    import mido

    destination = Path(destination).resolve()
    report = json.loads((destination / "informe.json").read_text(encoding="utf-8"))
    combined = mido.MidiFile(destination / "cancion.mid")
    if combined.type != 1 or not report["pistas"]:
        raise ValueError("El resultado no contiene un MIDI tipo 1 con instrumentos.")
    files = [destination / "cancion.mid", destination / "informe.json"]
    for track in report["pistas"]:
        path = (destination / track["archivo"]).resolve()
        if not path.is_relative_to(destination / "instrumentos") or path.suffix != ".mid":
            raise ValueError("El informe contiene una ruta de instrumento no válida.")
        solo = mido.MidiFile(path)
        starts = [msg for tr in solo.tracks for msg in tr if msg.type == "note_on" and msg.velocity > 0]
        if len(starts) != track["notas"]:
            raise ValueError(f"Número de notas incorrecto en {path.name}.")
        expected_channel = 9 if track["bateria"] else 0
        if any(msg.channel != expected_channel for msg in starts):
            raise ValueError(f"Canal incorrecto en {path.name}.")
        files.append(path)
    readme = destination / "LEEME.txt"
    readme.write_text(
        "Canción a MIDI — MuScriptor 0.3.0\n\n"
        "cancion.mid: todas las pistas. instrumentos/: un MIDI por instrumento.\n"
        "Importa los archivos desde el mismo origen temporal. Batería: canal MIDI 10.\n"
        "120 BPM es una referencia técnica para mantener el tiempo original; no es una medición del tempo.\n"
        "Las notas no están cuantizadas. Los instrumentos y las notas son predicciones.\n"
        "MuScriptor, Kyutai y Mirelo: https://github.com/muscriptor/muscriptor\n"
        "Pesos CC BY-NC 4.0: uso no comercial.\n", encoding="utf-8")
    files.append(readme)
    archive = Path(str(destination) + ".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, arcname=path.relative_to(destination).as_posix())
    return archive
