"""Exportación a JSON, JSONL y CSV."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .exceptions import SofaScoreError

_LIST_KEYS = (
    "matches",
    "last_matches",
    "next_matches",
    "events",
    "results",
    "statistics",
    "incidents",
    "players",
    "rows",
    "seasons",
    "standings",
    "categories",
)


def to_json(data: Any, pretty: bool = True) -> str:
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def to_jsonl(rows: Sequence[Any]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)


def extract_rows(data: Any, table: Optional[str] = None) -> List[Any]:
    """Obtiene la lista de registros que se exportará a CSV/JSONL."""
    if isinstance(data, list):
        return list(data)
    if not isinstance(data, dict):
        return [data]

    if table:
        if table not in data:
            raise SofaScoreError(f'El resultado no contiene la tabla "{table}".')
        value = data[table]
        return list(value) if isinstance(value, list) else [value]

    # Un detalle de partido: la fila "principal" es el resumen del partido.
    if isinstance(data.get("match"), dict):
        return [data["match"]]

    for key in _LIST_KEYS:
        value = data.get(key)
        if isinstance(value, list):
            return list(value)

    return [data]


def flatten_record(obj: Any, prefix: str = "", out: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Aplana diccionarios anidados con notación de puntos."""
    if out is None:
        out = {}

    if isinstance(obj, dict):
        if not obj and prefix:
            out[prefix] = ""
            return out
        for key, value in obj.items():
            if str(key).startswith("_"):
                continue
            name = f"{prefix}.{key}" if prefix else str(key)
            flatten_record(value, name, out)
        return out

    if isinstance(obj, (list, tuple)):
        out[prefix] = json.dumps(obj, ensure_ascii=False)
        return out

    if obj is None:
        out[prefix] = ""
    else:
        out[prefix] = obj
    return out


def write_csv(data: Any, output: Optional[Any] = None, table: Optional[str] = None) -> int:
    """Escribe CSV. Devuelve el número de filas escritas."""
    rows = extract_rows(data, table)
    flat_rows = [flatten_record(row) for row in rows]

    fieldnames: List[str] = []
    for row in flat_rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)

    if output is None:
        if not flat_rows:
            return 0
        writer = csv.DictWriter(
            sys.stdout, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(flat_rows)
        return len(flat_rows)

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore"
        )
        if fieldnames:
            writer.writeheader()
            writer.writerows(flat_rows)
    return len(flat_rows)


def _write_text(text: str, output: Optional[Any]) -> None:
    if output is None:
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_output(
    data: Any,
    fmt: str = "json",
    output: Optional[Any] = None,
    pretty: bool = True,
    table: Optional[str] = None,
) -> int:
    """Escribe ``data`` en el formato pedido. Devuelve el número de registros."""
    fmt = (fmt or "json").lower()
    if fmt == "json":
        text = to_json(data, pretty=pretty)
        _write_text(text, output)
        if isinstance(data, list):
            return len(data)
        return 1

    if fmt in ("jsonl", "ndjson"):
        rows = extract_rows(data, table)
        text = to_jsonl(rows)
        _write_text(text + ("\n" if text else ""), output)
        return len(rows)

    if fmt == "csv":
        return write_csv(data, output, table=table)

    raise SofaScoreError(
        f'Formato no soportado: "{fmt}". Usa json, jsonl o csv.'
    )


def format_from_path(path: Optional[Any], default: str = "json") -> str:
    if not path:
        return default
    suffix = Path(path).suffix.lower()
    return {
        ".json": "json",
        ".jsonl": "jsonl",
        ".ndjson": "jsonl",
        ".csv": "csv",
    }.get(suffix, default)
