"""Command-line entry points for planning, collecting, and summarizing."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .collect import DEFAULT_CAP, DEFAULT_DATA, _estimate_jev_cost, run_engine
from .engines import make_adapter
from .records import read_jsonl
from .study import ENGINE_NAMES, jobs
from .summary import summarize


def _rows(engine: str) -> list[dict]:
    rows = read_jsonl(DEFAULT_DATA / f"{engine}.jsonl")
    return [row for row in rows if row.get("status") == "ok"]


async def _preflight(engine: str) -> dict:
    adapter = make_adapter(engine)
    provenance = await adapter.provenance()
    return {"engine": engine, "planned_requests": len(list(jobs(engine))),
            "provenance": provenance,
            "jev_conservative_cost_usd": _estimate_jev_cost(list(jobs(engine)))
            if engine == "jev" else None}


def _run(args) -> int:
    engines = ENGINE_NAMES if args.engine == "all" else (args.engine,)
    code = 0
    for engine in engines:
        path = DEFAULT_DATA / f"{engine}.jsonl"
        result = asyncio.run(run_engine(engine, path, args.jev_cap))
        print(f"{engine}: {result['successful']}/{result['expected']} complete")
        code = max(code, 0 if result["complete"] else 2)
    return code


def _summary(args) -> int:
    engines = ENGINE_NAMES if args.engine == "all" else (args.engine,)
    records = [row for engine in engines for row in _rows(engine)]
    if not records:
        raise SystemExit("no successful records found")
    result = summarize(records)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all(result["engines"][name]["complete"] for name in engines) else 2


def _charts(_args) -> int:
    from .charts import generate
    generate(DEFAULT_DATA, Path(__file__).resolve().parents[2] / "images")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="benford-decisions")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="show the frozen matrix and cost estimate")
    preflight = commands.add_parser("preflight", help="verify one engine before inference")
    preflight.add_argument("--engine", choices=ENGINE_NAMES, required=True)
    run = commands.add_parser("run", help="execute or resume a registered matrix")
    run.add_argument("--engine", choices=(*ENGINE_NAMES, "all"), required=True)
    run.add_argument("--jev-cap", type=float, default=DEFAULT_CAP)
    summary = commands.add_parser("summarize", help="summarize successful recorded responses")
    summary.add_argument("--engine", choices=(*ENGINE_NAMES, "all"), default="all")
    summary.add_argument("--output", type=Path)
    commands.add_parser("charts", help="generate the social image and result plots")
    args = parser.parse_args()
    if args.command == "plan":
        output = {engine: {"requests": len(list(jobs(engine))),
                           "jev_cost_estimate_usd": _estimate_jev_cost(list(jobs(engine)))
                           if engine == "jev" else None}
                  for engine in ENGINE_NAMES}
        output["total_requests"] = sum(item["requests"] for item in output.values()
                                       if isinstance(item, dict))
        print(json.dumps(output, indent=2))
    elif args.command == "preflight":
        print(json.dumps(asyncio.run(_preflight(args.engine)), indent=2, sort_keys=True))
    elif args.command == "run":
        raise SystemExit(_run(args))
    elif args.command == "summarize":
        raise SystemExit(_summary(args))
    elif args.command == "charts":
        raise SystemExit(_charts(args))
