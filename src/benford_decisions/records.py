"""Append-only JSONL records with deterministic identity and safe resumption."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on {path}:{line_number}") from error
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(encoded + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def unique_by(rows: Iterable[dict], key: str) -> dict[str, dict]:
    unique: dict[str, dict] = {}
    for row in rows:
        identity = row.get(key)
        if identity in unique and unique[identity] != row:
            raise ValueError(f"conflicting duplicate {key}: {identity}")
        unique[identity] = row
    return unique
