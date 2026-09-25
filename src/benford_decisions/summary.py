"""Descriptive summaries for the exhaustive die-choice study."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from .study import FACES, WORDS, complete_request_ids


def summarize(rows: Iterable[dict]) -> dict:
    records = list(rows)
    if not records:
        raise ValueError("no successful response records")
    by_engine: dict[str, dict] = {}
    for engine in ("jev", "kev", "laya"):
        engine_rows = [row for row in records if row["engine"] == engine]
        ids = {row["request_id"] for row in engine_rows}
        expected = complete_request_ids(engine)
        order_counts = Counter(row["choice_face"] for row in engine_rows)
        subsets = {}
        repeat_by_representation = {}
        for representation in ("digits", "words"):
            first = {row["permutation_rank"]: row for row in engine_rows
                     if row["representation"] == representation and row["pass_number"] == 1}
            second = {row["permutation_rank"]: row for row in engine_rows
                      if row["representation"] == representation and row["pass_number"] == 2}
            paired = sorted(first.keys() & second.keys())
            repeat_by_representation[representation] = {
                "paired_orders": len(paired),
                "changed_selected_face": sum(
                    first[rank]["choice_face"] != second[rank]["choice_face"] for rank in paired),
                "changed_top_face": sum(
                    first[rank]["top_face"] != second[rank]["top_face"] for rank in paired),
                "mean_absolute_probability_change_by_face": {
                    face: (sum(abs(first[rank]["probabilities_by_face"][face] -
                                   second[rank]["probabilities_by_face"][face]) for rank in paired)
                           / len(paired) if paired else None)
                    for face in FACES
                },
            }
        for representation in ("digits", "words"):
            for pass_number in (1, 2):
                part = [row for row in engine_rows
                        if row["representation"] == representation
                        and row["pass_number"] == pass_number]
                pos_chosen = Counter()
                top = Counter()
                for row in part:
                    top[row["top_face"] or "tie"] += 1
                    pos_chosen[row["choice_position"]] += 1
                labels = FACES if representation == "digits" else WORDS
                face_means = {
                    face: sum(row["probabilities_by_face"][face] for row in part) / len(part)
                    if part else None for face in FACES
                }
                subsets[f"{representation}_pass_{pass_number}"] = {
                    "n": len(part),
                    "top_choice_count_by_face": {face: top[face] for face in FACES},
                    "top_probability_tie_count": top["tie"],
                    "choice_count_by_position": {
                        str(position): pos_chosen[position] for position in range(1, 7)
                    },
                    "mean_probability_by_face": face_means,
                    "selection_range_by_position": (
                        max(pos_chosen.values(), default=0) - min(pos_chosen.values(), default=0)
                    ),
                }
        by_engine[engine] = {
            "successful": len(ids), "expected": len(expected),
            "missing_request_ids": sorted(expected - ids),
            "unexpected_request_ids": sorted(ids - expected),
            "complete": ids == expected,
            "choice_count_by_face": {face: order_counts[face] for face in FACES},
            "subsets": subsets,
            "repeat_stability": repeat_by_representation,
            "strict_one_dominance": all(
                row["top_face"] == "1" for row in engine_rows if row["representation"] == "digits"
            ) if engine_rows else False,
        }
    return {"study_id": "fair-die-option-order-v1", "records": len(records),
            "engines": by_engine}
