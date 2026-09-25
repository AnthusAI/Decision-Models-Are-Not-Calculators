from collections import Counter
import asyncio
from itertools import permutations

import pytest

from benford_decisions import collect
from benford_decisions.engines import request_payload, validate_answer
from benford_decisions.records import read_jsonl
from benford_decisions.release import build_release
from benford_decisions.study import FACES, WORDS, Job, jobs, orders
from benford_decisions.summary import summarize


def test_all_six_choice_orders_and_balance():
    generated = list(orders("digits"))
    assert len(generated) == 720
    assert {order for _, order in generated} == set(permutations(FACES))
    for position in range(6):
        counts = Counter(order[position] for _, order in generated)
        assert counts == {face: 120 for face in FACES}


def test_word_orders_map_to_same_semantic_face_order():
    digits = list(orders("digits"))
    words = list(orders("words"))
    assert len(words) == 720
    assert all(tuple(str(WORDS.index(label) + 1) for label in word_order) == digit_order
               for (_, digit_order), (_, word_order) in zip(digits, words))


def test_complete_matrix_size_and_exact_repeat():
    assert len(list(jobs("jev"))) == 2880
    assert len({job.request_id for job in jobs("jev")}) == 2880


def test_prompt_does_not_cue_a_face_and_preserves_order():
    job = Job("jev", "digits", 1, 1, ("6", "4", "2", "5", "3", "1"))
    question = job.question()
    assert list(question["criteria"]) == list(job.options)
    assert "Benford" not in str(job.request())
    assert "probability" not in str(job.request()).lower()


def test_engine_request_envelope_includes_model_and_exact_order():
    job = Job("kev", "digits", 1, 1, ("6", "4", "2", "5", "3", "1"))
    payload = request_payload("kev", job)
    assert payload["model"] == "kev-latest"
    assert list(payload["questions"]["die_result"]["criteria"]) == list(job.options)


def test_validate_rejects_missing_or_invalid_probability():
    job = next(jobs("jev"))
    with pytest.raises(ValueError):
        validate_answer(job, {"type": "choice", "choice": "1", "probabilities": {"1": 1}})


def test_jev_two_decimal_rounding_is_retained_without_renormalizing():
    jev_job = next(jobs("jev"))
    probabilities = {"1": .93, "2": .02, "3": .01, "4": .01, "5": .0, "6": .02}
    result = validate_answer(jev_job, {"type": "choice", "choice": "1",
                                       "probabilities": probabilities})
    assert sum(result.values()) == pytest.approx(.99)
    kev_job = next(jobs("kev"))
    with pytest.raises(ValueError, match="sum to one"):
        validate_answer(kev_job, {"type": "choice", "choice": "1",
                                  "probabilities": probabilities})


def test_summary_detects_incomplete_engine():
    job = next(jobs("jev"))
    row = {"request_id": job.request_id, "engine": "jev", "representation": "digits",
           "pass_number": 1, "permutation_rank": 1,
           "options": list(job.options),
           "choice_face": "1", "top_face": None, "choice_position": 1,
           "probabilities": {label: 1 / 6 for label in job.options},
           "probabilities_by_face": {face: 1 / 6 for face in FACES},
           "label_to_face": {label: str(index + 1) for index, label in enumerate(job.options)},
           "option_position": {label: index for index, label in enumerate(job.options, start=1)}}
    result = summarize([row])["engines"]["jev"]
    assert result["successful"] == 1
    assert result["complete"] is False
    assert result["strict_one_dominance"] is False


def test_collector_stops_after_first_adapter_failure(tmp_path, monkeypatch):
    class BrokenAdapter:
        async def provenance(self):
            return {"engine": "kev", "revision": "test"}

        async def answer(self, _job):
            raise OSError("test endpoint unavailable")

    monkeypatch.setattr(collect, "make_adapter", lambda _engine: BrokenAdapter())
    result = asyncio.run(collect.run_engine("kev", tmp_path / "kev.jsonl"))
    rows = read_jsonl(tmp_path / "kev.jsonl")
    assert len(rows) == 1
    assert rows[0]["status"] == "error"
    assert result["successful"] == 0
    assert result["complete"] is False


def test_release_refuses_incomplete_results(tmp_path):
    (tmp_path / "data").mkdir()
    with pytest.raises(RuntimeError, match="jev is incomplete"):
        build_release(tmp_path / "data", tmp_path / "results")
