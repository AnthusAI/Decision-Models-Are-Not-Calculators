"""Validate complete matrices and write clean replay archives and checksums."""

from __future__ import annotations

import gzip
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from .records import read_jsonl
from .engines import request_payload, validate_answer
from .study import ENGINE_NAMES, REPRESENTATIONS, complete_request_ids, jobs
from .summary import summarize


def _canonical(row: dict) -> bytes:
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def build_release(data_dir: Path, results_dir: Path) -> dict:
    rows_by_engine: dict[str, list[dict]] = {}
    release_files: dict[str, dict] = {}
    examples = []
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "machine": platform.machine(), "benford_decisions": "0.1.0"}
    for package in ("torch", "torchvision", "transformers", "laya", "typesafe-sdk",
                    "numpy", "matplotlib", "huggingface-hub"):
        try:
            environment[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            continue

    for engine in ENGINE_NAMES:
        all_rows = read_jsonl(data_dir / f"{engine}.jsonl")
        rows = [row for row in all_rows if row.get("status") == "ok"]
        by_id = {}
        for row in rows:
            request_id = row["request_id"]
            if request_id in by_id and by_id[request_id] != row:
                raise ValueError(f"conflicting successful duplicate: {request_id}")
            by_id[request_id] = row
        planned = {job.request_id: job for job in jobs(engine)}
        expected = complete_request_ids(engine)
        if set(by_id) != expected:
            raise RuntimeError(f"{engine} is incomplete: {len(by_id)}/{len(expected)} valid responses")
        ordered_rows = [by_id[request_id] for request_id in planned]
        for row in ordered_rows:
            matching = planned[row["request_id"]]
            logical_request = request_payload(engine, matching)
            # Earlier collector commits stored state/questions separately from
            # the SDK's model argument. Normalize those records in the clean
            # archive; model identity is independently pinned in provenance.
            if row["request"] not in (logical_request, matching.request()) or row["options"] != list(matching.options):
                raise ValueError(f"request differs from frozen protocol: {row['request_id']}")
            row["request"] = logical_request
            normalized = validate_answer(matching, {
                "type": "choice", "choice": row["choice_label"],
                "probabilities": row["probabilities"],
            })
            if row["choice_face"] != matching.face_for_label(row["choice_label"]):
                raise ValueError(f"semantic choice mapping differs: {row['request_id']}")
            if any(abs(normalized[label] - row["probabilities"][label]) > 1e-12
                   for label in matching.options):
                raise ValueError(f"normalized probabilities differ: {row['request_id']}")
            expected_map = {label: matching.face_for_label(label) for label in matching.options}
            if row["label_to_face"] != expected_map:
                raise ValueError(f"semantic label map differs: {row['request_id']}")
            expected_face_probs = {expected_map[label]: normalized[label]
                                   for label in matching.options}
            if row["probabilities_by_face"] != expected_face_probs:
                raise ValueError(f"semantic probabilities differ: {row['request_id']}")
            expected_positions = {label: index + 1
                                  for index, label in enumerate(matching.options)}
            if (row["option_position"] != expected_positions or
                    row["choice_position"] != expected_positions[row["choice_label"]]):
                raise ValueError(f"option position record differs: {row['request_id']}")
            maximum = max(normalized.values())
            top_labels = [label for label, value in normalized.items()
                          if abs(value - maximum) <= 1e-12]
            expected_top = matching.face_for_label(top_labels[0]) if len(top_labels) == 1 else None
            if row["top_labels"] != top_labels or row["top_face"] != expected_top:
                raise ValueError(f"top-probability record differs: {row['request_id']}")
        provenance = {json.dumps(row["provenance"], sort_keys=True) for row in ordered_rows}
        if len(provenance) != 1:
            raise ValueError(f"{engine} model/environment provenance changed mid-run")
        rows_by_engine[engine] = ordered_rows

        target = data_dir / f"{engine}-responses.jsonl.gz"
        temporary = target.with_suffix(target.suffix + ".tmp")
        digest = hashlib.sha256()
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0,
                               compresslevel=9) as zipped:
                for row in ordered_rows:
                    zipped.write(_canonical(row) + b"\n")
        temporary.replace(target)
        with target.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        release_files[target.name] = {"sha256": digest.hexdigest(),
                                      "compressed_bytes": target.stat().st_size,
                                      "records": len(ordered_rows),
                                      "failed_attempts_excluded": sum(
                                          row.get("status") == "error" for row in all_rows)}

        for representation in REPRESENTATIONS:
            job = next(job for job in jobs(engine, representation, 1)
                       if job.permutation_rank == 1)
            row = by_id[job.request_id]
            raw_response = row["raw_response"]
            response = (raw_response.get("response", raw_response)
                        if isinstance(raw_response, dict) else raw_response)
            examples.append({"engine": engine, "representation": representation,
                             "request_id": row["request_id"], "provenance": row["provenance"],
                             "request": row["request"], "response": response,
                             "normalized_choice_face": row["choice_face"],
                             "normalized_probabilities_by_face": row["probabilities_by_face"]})

    summary = summarize(row for rows in rows_by_engine.values() for row in rows)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (results_dir / "examples.json").write_text(
        json.dumps(examples, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    manifest = {"study_id": "fair-die-option-order-v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expected_total_responses": 8640,
                "successful_total_responses": sum(len(rows) for rows in rows_by_engine.values()),
                "environment": environment, "archives": release_files}
    (results_dir / "release-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return manifest
