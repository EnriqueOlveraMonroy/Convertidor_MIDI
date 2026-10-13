"""Offline tests: real MIDI I/O, tempo, channels and FFmpeg decoding.

No model weights or Hugging Face account are needed for these checks.
"""

import io
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave

import mido

from audio_a_midi import ConversionError, decode_audio, export_midi, transcribe_song


def midi_bytes(track_count=2):
    midi = mido.MidiFile(type=1, ticks_per_beat=480)
    midi.tracks.append(mido.MidiTrack([
        mido.MetaMessage("set_tempo", tempo=500000, time=0),
        mido.MetaMessage("time_signature", numerator=3, denominator=4, time=0),
        mido.MetaMessage("set_tempo", tempo=750000, time=480),
    ]))
    for index in range(track_count):
        drums = index == 1
        channel = 9 if drums else 0
        midi.tracks.append(mido.MidiTrack([
            mido.MetaMessage("track_name", name="drums" if drums else f"piano {index}", time=0),
            mido.Message("program_change", program=0 if drums else index % 128, channel=channel, time=0),
            mido.Message("control_change", control=64, value=127, channel=channel, time=120),
            mido.Message("note_on", note=36 if drums else 60, velocity=90, channel=channel, time=120),
            mido.Message("note_off", note=36 if drums else 60, velocity=0, channel=channel, time=480),
            mido.Message("control_change", control=64, value=0, channel=channel, time=0),
        ]))
    buffer = io.BytesIO()
    midi.save(file=buffer)
    return buffer.getvalue()


def note_times(midi):
    seconds = 0.0
    result = []
    for message in midi:
        seconds += message.time
        if message.type in {"note_on", "note_off"}:
            result.append((message.type, message.note, round(seconds, 6)))
    return result


class MidiExportTests(unittest.TestCase):
    def test_published_muscriptor_events_export_as_named_tracks(self):
        # Exercise the real model package's serializer, without loading weights
        # or claiming to test neural transcription quality.
        import torch
        from muscriptor import TranscriptionModel
        from muscriptor.events import NoteEndEvent, NoteStartEvent, ProgressEvent
        from muscriptor.tokenizer.mt3 import MT3Tokenizer

        model = TranscriptionModel(
            model=None,
            tokenizer=MT3Tokenizer(instrument_vocabulary="MT3_FULL_PLUS", max_shift_steps=1001),
            device=torch.device("cpu"),
        )
        piano = NoteStartEvent(pitch=60, start_time=0.25, index=0, instrument="acoustic_piano")
        bass = NoteStartEvent(pitch=40, start_time=0.5, index=1, instrument="electric_bass")
        drums = NoteStartEvent(pitch=36, start_time=0.75, index=2, instrument="drums")
        events = [ProgressEvent(completed=0, total=1), piano, bass, drums,
                  NoteEndEvent(end_time=0.85, start_event=drums),
                  NoteEndEvent(end_time=1.0, start_event=piano),
                  NoteEndEvent(end_time=1.5, start_event=bass),
                  ProgressEvent(completed=1, total=1)]
        payload = model.events_to_midi_bytes(iter(events), beat_grid=None)
        with tempfile.TemporaryDirectory() as temporary:
            tracks = export_midi(payload, Path(temporary))
            self.assertEqual({track["nombre"] for track in tracks}, {"acoustic piano", "electric bass", "drums"})
            self.assertEqual([track["notas"] for track in tracks], [1, 1, 1])

    def test_tracks_drums_sustain_and_tempo_survive_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            tracks = export_midi(midi_bytes(), output)
            combined = mido.MidiFile(output / "cancion.mid")
            self.assertEqual(combined.type, 1)
            self.assertEqual(len(combined.tracks), 3)
            self.assertEqual([track["notas"] for track in tracks], [1, 1])
            self.assertEqual(tracks[1]["canal_1_16"], 10)
            self.assertTrue(tracks[1]["bateria"])
            for info in tracks:
                solo = mido.MidiFile(output / info["archivo"])
                expected_pitch = 36 if info["bateria"] else 60
                expected = [item for item in note_times(combined) if item[1] == expected_pitch]
                self.assertEqual(note_times(solo), expected)
                self.assertEqual(expected[0][2], 0.25)
                self.assertEqual(expected[1][2], 0.875)
                controls = [msg for msg in solo.tracks[1] if msg.type == "control_change"]
                self.assertEqual([(msg.control, msg.value) for msg in controls], [(64, 127), (64, 0)])
                tempos = [msg.tempo for msg in solo.tracks[0] if msg.type == "set_tempo"]
                self.assertEqual(tempos, [500000, 750000])

    def test_more_than_fifteen_melodic_tracks_get_unique_ports(self):
        with tempfile.TemporaryDirectory() as temporary:
            tracks = export_midi(midi_bytes(18), Path(temporary))
            addresses = [(track["puerto_0_127"], track["canal_1_16"]) for track in tracks]
            self.assertEqual(len(set(addresses)), 18)
            self.assertEqual(tracks[-1]["puerto_0_127"], 1)

    def test_nonempty_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            existing = output / "cancion.mid"
            existing.write_bytes(b"keep me")
            with self.assertRaises(ConversionError):
                export_midi(midi_bytes(), output)
            self.assertEqual(existing.read_bytes(), b"keep me")

    def test_empty_prediction_fails_without_creating_output(self):
        midi = mido.MidiFile(type=1)
        midi.tracks.append(mido.MidiTrack())
        buffer = io.BytesIO()
        midi.save(file=buffer)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            with self.assertRaises(ConversionError):
                export_midi(buffer.getvalue(), output)
            self.assertFalse(output.exists())


class AudioInputTests(unittest.TestCase):
    def test_ffmpeg_decodes_crops_and_resamples_stereo_mp3(self):
        import imageio_ffmpeg
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            wav_path = root / "input.wav"
            with wave.open(str(wav_path), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(44100)
                wav.writeframes(struct.pack("<hh", 1000, -500) * 88200)
            mp3 = root / "canción de prueba.mp3"
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-loglevel", "error", "-i", str(wav_path), str(mp3)], check=True)
            decoded = root / "decoded.wav"
            seconds = decode_audio(mp3, decoded, 0.5, 1.0)
            self.assertAlmostEqual(seconds, 1.0, places=2)
            with wave.open(str(decoded), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertEqual(wav.getframerate(), 16000)

    def test_invalid_audio_reports_decoder_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            invalid = root / "invalid.mp3"
            invalid.write_bytes(b"not an audio file")
            with self.assertRaisesRegex(ConversionError, "FFmpeg"):
                decode_audio(invalid, root / "output.wav", 0, None)

    def test_cli_rejects_missing_input_without_downloading_model(self):
        result = subprocess.run([sys.executable, "audio_a_midi.py", "no-such-file.mp3"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("No existe el archivo", result.stderr)

    def test_api_rejects_invalid_range_without_loading_model(self):
        for start, duration in [(float("nan"), 1), (-1, 1), (0, float("inf")), (0, 0)]:
            with self.subTest(start=start, duration=duration):
                with self.assertRaises(ConversionError):
                    transcribe_song(Path("any.mp3"), Path("output"), start=start, duration=duration)


if __name__ == "__main__":
    unittest.main()
