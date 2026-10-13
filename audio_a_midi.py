"""Transcribe audio locally with MuScriptor and export separate MIDI tracks."""

from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
# Keep model downloads and temporary data inside the project.
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(ROOT / ".cache" / "torch"))


class ConversionError(RuntimeError):
    """An actionable error that can be shown without a traceback."""


def safe_name(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("._")[:80]
    return value or "instrumento"


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Debe ser un número positivo y finito.")
    return number


def nonnegative_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("Debe ser un número finito mayor o igual a cero.")
    return number


def decode_audio(source: Path, destination: Path, start: float, duration: float | None) -> float:
    """Use bundled FFmpeg: MP3/WAV/FLAC/OGG/M4A -> mono PCM WAV, 16 kHz."""
    import imageio_ffmpeg
    import wave

    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin"]
    if start:
        command += ["-ss", str(start)]
    command += ["-i", str(source), "-map", "0:a:0", "-vn"]
    if duration is not None:
        command += ["-t", str(duration)]
    command += ["-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-y", str(destination)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise ConversionError(f"No se pudo leer el audio. FFmpeg: {result.stderr.strip()[-2000:]}")
    with wave.open(str(destination), "rb") as wav:
        seconds = wav.getnframes() / wav.getframerate()
    if seconds <= 0:
        raise ConversionError("El archivo no contiene audio en el intervalo indicado.")
    return seconds


def conductor_track(midi):
    """Collect global metadata at absolute ticks, including later tempo changes."""
    import mido

    global_types = {"set_tempo", "time_signature", "key_signature", "marker"}
    events = {}
    for track in midi.tracks:
        tick = 0
        for message in track:
            tick += message.time
            if message.type in global_types:
                key = (tick, str(message.copy(time=0)))
                events[key] = (tick, message)
    output = mido.MidiTrack([mido.MetaMessage("track_name", name="Tempo y compás", time=0)])
    previous = 0
    for tick, message in sorted(events.values(), key=lambda item: item[0]):
        output.append(message.copy(time=tick - previous))
        previous = tick
    return output


def export_midi(midi_bytes: bytes, destination: Path) -> list[dict]:
    """Keep one named track per predicted instrument; export solo files too.

    Separate MIDI ports avoid channel collisions when there are >15 melodic
    instruments. Solo files always use channel 1 (drums: channel 10).
    Delta times, control changes and global tempo events are preserved.
    """
    import mido

    midi = mido.MidiFile(file=io.BytesIO(midi_bytes))
    if midi.type == 2:
        raise ConversionError("Se esperaba un MIDI síncrono, pero el modelo devolvió MIDI tipo 2.")
    tracks = [track for track in midi.tracks if any(
        message.type == "note_on" and message.velocity > 0 for message in track
    )]
    if not tracks:
        raise ConversionError("El modelo no detectó notas. Prueba otro fragmento o un modelo mayor.")
    combined = mido.MidiFile(type=1, ticks_per_beat=midi.ticks_per_beat)
    conductor = conductor_track(midi)
    combined.tracks.append(conductor)
    melodic_channels = list(range(9)) + list(range(10, 16))
    melodic_count = 0
    report = []
    # Build and validate before creating any output files.
    prepared = []
    for index, original in enumerate(tracks, 1):
        note_messages = [msg for msg in original if msg.type == "note_on" and msg.velocity > 0]
        original_channels = {msg.channel for msg in note_messages}
        if len(original_channels) != 1:
            raise ConversionError("Una pista del modelo contiene varios canales; no puede tratarse como un solo instrumento.")
        drums = original_channels == {9}
        name = next((msg.name for msg in original if msg.type == "track_name"), f"Instrumento {index}")
        programs = {msg.program for msg in original if msg.type == "program_change"}
        if len(programs) > 1:
            raise ConversionError(f"La pista {name!r} cambia de instrumento durante la canción.")
        program = next(iter(programs), 0)
        if drums:
            port, channel = 0, 9
        else:
            port, channel_index = divmod(melodic_count, 15)
            channel = melodic_channels[channel_index]
            melodic_count += 1
        if port > 127:
            raise ConversionError("Demasiados instrumentos para exportar como puertos MIDI.")
        combined_track = mido.MidiTrack([mido.MetaMessage("midi_port", port=port, time=0)])
        solo_track = mido.MidiTrack()
        for message in original:
            # Replace existing port events without losing their delta times.
            if message.type == "midi_port":
                combined_track.append(message.copy(port=port))
                solo_track.append(message.copy(port=0))
            elif hasattr(message, "channel"):
                combined_track.append(message.copy(channel=channel))
                solo_track.append(message.copy(channel=9 if drums else 0))
            else:
                combined_track.append(message.copy())
                solo_track.append(message.copy())
        combined.tracks.append(combined_track)
        filename = f"{index:02d}_{safe_name(name)}.mid"
        solo = mido.MidiFile(type=1, ticks_per_beat=midi.ticks_per_beat)
        solo.tracks.extend([mido.MidiTrack(msg.copy() for msg in conductor), solo_track])
        prepared.append((filename, solo))
        report.append({
            "nombre": name, "archivo": f"instrumentos/{filename}",
            "notas": len(note_messages), "programa_gm_0_127": program,
            "bateria": drums, "canal_1_16": channel + 1, "puerto_0_127": port,
        })
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise ConversionError(f"La carpeta de salida debe estar vacía: {destination}")
    (destination / "instrumentos").mkdir()
    combined.save(destination / "cancion.mid")
    for filename, solo in prepared:
        solo.save(destination / "instrumentos" / filename)
    return report


def choose_device(requested: str) -> str:
    import torch

    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise ConversionError("CUDA no está disponible. Ejecuta instalar.ps1 o utiliza --dispositivo cpu.")
    return requested


def diagnose() -> None:
    import importlib.metadata
    import imageio_ffmpeg
    import torch
    from huggingface_hub import get_token

    print(f"Python: {sys.version.split()[0]}")
    for package in ("muscriptor", "torch", "mido", "imageio-ffmpeg"):
        print(f"{package}: {importlib.metadata.version(package)}")
    print(f"FFmpeg: {imageio_ffmpeg.get_ffmpeg_exe()}")
    print(f"CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    # Never show the credential itself.
    print(f"Sesión Hugging Face configurada: {bool(get_token())}")
    print("El acceso al modelo se comprueba al descargarlo; tener sesión no garantiza acceso.")


def transcribe_song(source: Path, destination: Path, *, model_size: str = "medium",
                    device: str = "auto", start: float = 0.0,
                    duration: float | None = None, detect_tempo: bool = False) -> dict:
    """Reusable entry point for a future web worker. Returns the JSON report."""
    if not math.isfinite(start) or start < 0:
        raise ConversionError("El inicio debe ser finito y mayor o igual a cero.")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ConversionError("La duración debe ser positiva y finita.")
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not source.is_file():
        raise ConversionError(f"No existe el archivo de audio: {source}")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ConversionError(f"Usa una carpeta de salida nueva o vacía: {destination}")
    if model_size not in {"small", "medium", "large"}:
        raise ConversionError("Modelo válido: small, medium o large.")
    if device not in {"auto", "cuda", "cpu"}:
        raise ConversionError("Dispositivo válido: auto, cuda o cpu.")

    import torch
    from muscriptor import TranscriptionModel
    from muscriptor.events import NoteStartEvent, ProgressEvent
    from muscriptor.utils.download import ModelDownloadError

    selected_device = choose_device(device)
    cache = ROOT / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="audio_", dir=cache) as temporary:
        wav_path = Path(temporary) / "audio.wav"
        seconds = decode_audio(source, wav_path, start, duration)
        print(f"Audio: {seconds:.1f} s. Modelo: {model_size}. Dispositivo: {selected_device}.", flush=True)
        print("Cargando modelo (la primera vez descarga los pesos)…", flush=True)
        try:
            model = TranscriptionModel.load_model(weights_path=model_size, device=selected_device)
        except ModelDownloadError as error:
            raise ConversionError(
                f"No se pudo obtener MuScriptor {model_size}. Acepta la licencia en "
                f"https://huggingface.co/MuScriptor/muscriptor-{model_size} "
                "y ejecuta .\\autenticar.ps1. No compartas el token en el chat."
            ) from error
        with torch.inference_mode():
            grid = model.detect_beat_grid_for(wav_path, "best-effort" if detect_tempo else False)
            events = []
            for event in model.transcribe(audio=wav_path, batch_size=1, prelude_forcing=True, use_sampling=False):
                if isinstance(event, ProgressEvent):
                    print(f"Progreso: {event.completed}/{event.total} bloques de audio", flush=True)
                else:
                    events.append(event)
            if grid is not None:
                grid = grid.with_onset_delay([
                    event.start_time for event in events if isinstance(event, NoteStartEvent)
                ])
            midi_bytes = model.events_to_midi_bytes(iter(events), beat_grid=grid)
        tracks = export_midi(midi_bytes, destination)
        report = {
            "audio": str(source), "modelo": f"MuScriptor {model_size}",
            "dispositivo": selected_device, "inicio_audio_s": start,
            "duracion_audio_s": round(seconds, 3), "tiempo_procesamiento_s": round(time.perf_counter() - started, 2),
            "tempo_detectado_bpm": grid.bpm if grid is not None else None,
            "tempo_midi_bpm": grid.bpm if grid is not None else 120,
            "cuantizado": False, "midi": "cancion.mid", "pistas": tracks,
        }
        (destination / "informe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nGuardado: {destination / 'cancion.mid'}")
        for track in tracks:
            print(f"  {track['nombre']}: {track['notas']} notas -> {track['archivo']}")
        return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Canción a MIDI con pistas separadas por instrumento (MuScriptor local).")
    parser.add_argument("audio", nargs="?", type=Path, help="Archivo MP3, WAV, FLAC, OGG, M4A, etc.")
    parser.add_argument("--salida", type=Path, help="Carpeta nueva o vacía para los resultados.")
    parser.add_argument("--modelo", choices=["small", "medium", "large"], default="medium")
    parser.add_argument("--dispositivo", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--inicio", type=nonnegative_float, default=0.0, help="Inicio del fragmento, en segundos.")
    parser.add_argument("--duracion", type=positive_float, help="Transcribir solo estos segundos; por defecto, hasta el final.")
    parser.add_argument("--detectar-tempo", action="store_true", help="Detectar BPM/compás (descarga un modelo adicional).")
    parser.add_argument("--diagnostico", action="store_true", help="Comprobar instalación, GPU y sesión sin descargar pesos.")
    args = parser.parse_args(argv)
    if not args.audio and not args.diagnostico:
        parser.error("Indica un archivo de audio o utiliza --diagnostico.")
    try:
        if args.diagnostico:
            diagnose()
        if args.audio:
            destination = args.salida or ROOT / "resultados" / (safe_name(args.audio.stem) + "_" + time.strftime("%Y%m%d_%H%M%S"))
            transcribe_song(args.audio, destination, model_size=args.modelo, device=args.dispositivo,
                            start=args.inicio, duration=args.duracion, detect_tempo=args.detectar_tempo)
        return 0
    except ImportError as error:
        print(f"Falta una dependencia: {error}. Ejecuta instalar.ps1.", file=sys.stderr)
    except ConversionError as error:
        print(f"Error: {error}", file=sys.stderr)
    except KeyboardInterrupt:
        print("Conversión interrumpida.", file=sys.stderr)
        return 130
    except Exception as error:
        if "out of memory" in str(error).lower():
            print("Memoria GPU insuficiente. Prueba --modelo small o --dispositivo cpu.", file=sys.stderr)
        else:
            print(f"Error ({type(error).__name__}): {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
