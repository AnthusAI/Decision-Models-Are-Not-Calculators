"""Execute and resume the preregistered request matrix."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .engines import JEV_INPUT_USD_PER_MILLION, make_adapter, request_payload, validate_answer
from .records import append_jsonl, read_jsonl
from .study import ENGINE_NAMES, FACES, jobs
from .summary import summarize

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "answers"
DEFAULT_CAP = 1.0


def _estimate_jev_cost(engine_jobs) -> float:
    # Deliberately conservative: two input tokens per UTF-8 byte, no response-price credit.
    byte_count = sum(len(json.dumps(job.request(), ensure_ascii=False).encode("utf-8"))
                     for job in engine_jobs)
    return byte_count * 2 * JEV_INPUT_USD_PER_MILLION / 1_000_000


async def run_engine(engine: str, output: Path, cap: float = DEFAULT_CAP) -> dict:
    planned = list(jobs(engine))
    existing = read_jsonl(output)
    successful = {row["request_id"] for row in existing if row.get("status") == "ok"}
    pending = [job for job in planned if job.request_id not in successful]
    if engine == "jev":
        estimate = _estimate_jev_cost(pending)
        spent = sum(float(row.get("cost_usd", 0)) for row in existing)
        if spent + estimate > cap:
            raise RuntimeError(f"Jev input cost budget check failed: recorded ${spent:.6f} + "
                               f"conservative pending estimate ${estimate:.6f} > cap ${cap:.2f}")
    adapter = make_adapter(engine)
    provenance = await adapter.provenance()
    print(f"{engine}: {len(successful)}/{len(planned)} already complete; "
          f"{len(pending)} remaining", flush=True)
    for index, job in enumerate(pending, start=1):
        record = {"study_id": "fair-die-option-order-v1", "request_id": job.request_id,
                  "engine": engine, "representation": job.representation,
                  "pass_number": job.pass_number, "permutation_rank": job.permutation_rank,
                  "options": list(job.options), "request": request_payload(engine, job),
                  "provenance": provenance, "started_at": datetime.now(timezone.utc).isoformat()}
        started = time.perf_counter()
        try:
            raw, answer, latency_ms = await adapter.answer(job)
            # Retain a malformed model reply in the error record for audit.
            record["raw_response"] = raw
            probs = validate_answer(job, answer)
            label_to_face = {label: job.face_for_label(label) for label in job.options}
            max_probability = max(probs.values())
            top_labels = [label for label, value in probs.items()
                          if abs(value - max_probability) <= 1e-12]
            probability_by_face = {label_to_face[label]: value for label, value in probs.items()}
            record.update({"status": "ok", "choice_label": answer["choice"],
                           "choice_face": label_to_face[answer["choice"]],
                           "top_labels": top_labels,
                           "top_face": label_to_face[top_labels[0]] if len(top_labels) == 1 else None,
                           "probabilities": probs, "probabilities_by_face": probability_by_face,
                           "label_to_face": label_to_face,
                           "option_position": {label: i + 1 for i, label in enumerate(job.options)},
                           "choice_position": job.options.index(answer["choice"]) + 1,
                           "latency_ms": round(latency_ms, 3),
                           "completed_at": datetime.now(timezone.utc).isoformat()})
            usage = raw.get("usage", {}) if isinstance(raw, dict) else {}
            input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
            record["input_tokens"] = input_tokens
            record["cost_usd"] = (input_tokens * JEV_INPUT_USD_PER_MILLION / 1_000_000
                                   if engine == "jev" and isinstance(input_tokens, (int, float))
                                   else 0.0)
        except Exception as error:  # retain the exact failed job and resume without losing progress
            record.update({"status": "error", "error_type": type(error).__name__,
                           "error": str(error), "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                           "completed_at": datetime.now(timezone.utc).isoformat()})
        append_jsonl(output, record)
        if record["status"] != "ok":
            print(f"{engine} {job.request_id}: {record['error_type']}: {record['error']}",
                  file=sys.stderr, flush=True)
            # One adapter/protocol failure may be systemic; stop before repeating it
            # across thousands of requests. The failed ID remains retryable.
            break
        if index % 60 == 0 or index == len(pending):
            print(f"{engine}: processed {index}/{len(pending)} remaining requests", flush=True)
    final_rows = read_jsonl(output)
    final_ok = [row for row in final_rows if row.get("status") == "ok"]
    if final_ok:
        result = summarize(final_ok)["engines"][engine]
    else:
        final_ids = {row["request_id"] for row in final_rows if row.get("status") == "ok"}
        result = {"successful": len(final_ids), "expected": len(planned),
                  "complete": False,
                  "missing_request_ids": sorted({job.request_id for job in planned} - final_ids)}
    return result


async def _main(args) -> int:
    if args.engine not in ENGINE_NAMES:
        raise SystemExit(f"engine must be one of {ENGINE_NAMES}")
    path = args.output or DEFAULT_DATA / f"{args.engine}.jsonl"
    result = await run_engine(args.engine, path, args.jev_cap)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["complete"] else 2


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=ENGINE_NAMES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--jev-cap", type=float, default=DEFAULT_CAP,
                        help="maximum Jev input spend in USD (default: $1)")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(_main(args)))
    except (RuntimeError, OSError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error


if __name__ == "__main__":
    main()
