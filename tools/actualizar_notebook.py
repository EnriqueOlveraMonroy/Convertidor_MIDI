"""Embed repository code in the Kaggle notebook and remove saved outputs."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "Cancion_a_MIDI_Kaggle.ipynb"


def prepare_notebook() -> str:
    converter = (ROOT / "audio_a_midi.py").read_text(encoding="utf-8")
    runtime = (ROOT / "kaggle_runtime.py").read_text(encoding="utf-8")
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    values = {"CONVERSOR_PY": converter, "RUNTIME_PY": runtime, "CONVERTIR_COMPLETA": False}
    replacements = dict.fromkeys(values, 0)
    for cell in notebook["cells"]:
        if cell["cell_type"] != "code":
            continue
        source = cell["source"]
        code = source if isinstance(source, str) else "".join(source)
        lines = code.splitlines(keepends=True)
        edits = []
        for node in ast.parse(code).body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in values:
                replacements[target.id] += 1
                edits.append((node.lineno - 1, node.end_lineno, f"{target.id} = {values[target.id]!r}\n"))
        for start, end, replacement in sorted(edits, reverse=True):
            lines[start:end] = [replacement]
        cell["source"] = "".join(lines).splitlines(keepends=True)
        cell["outputs"] = []
        cell["execution_count"] = None
    if any(count != 1 for count in replacements.values()):
        raise ValueError("No se encontraron las tres asignaciones esperadas una sola vez. Revisa la estructura del notebook.")
    notebook["metadata"]["converter_sha256"] = hashlib.sha256(converter.encode()).hexdigest()
    return json.dumps(notebook, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Actualizar el código incluido en el notebook de Kaggle.")
    parser.add_argument("--check", action="store_true", help="Solo comprobar, sin modificar archivos.")
    args = parser.parse_args()
    prepared = prepare_notebook()
    if args.check:
        if NOTEBOOK.read_text(encoding="utf-8") != prepared:
            print("El notebook necesita actualizarse. Ejecuta python tools/actualizar_notebook.py")
            return 1
        print("Notebook actualizado, sin salidas y con conversión completa desactivada.")
        return 0
    temporary = NOTEBOOK.with_suffix(".ipynb.tmp")
    temporary.write_text(prepared, encoding="utf-8")
    temporary.replace(NOTEBOOK)
    print("Notebook actualizado. Sube también este .ipynb a GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
