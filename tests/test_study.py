from collections import Counter
from itertools import permutations

import pytest

from benford_decisions.engines import validate_answer
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


def test_validate_rejects_missing_or_invalid_probability():
    job = next(jobs("jev"))
    with pytest.raises(ValueError):
        validate_answer(job, {"type": "choice", "choice": "1", "probabilities": {"1": 1}})


def test_summary_detects_incomplete_engine():
    job = next(jobs("jev"))
    row = {"request_id": job.request_id, "engine": "jev", "representation": "digits",
           "pass_number": 1, "choice_face": "1", "top_face": "1", "choice_position": 1,
           "probabilities": {label: 1 / 6 for label in job.options},
           "probabilities_by_face": {face: 1 / 6 for face in FACES},
           "label_to_face": {label: str(index + 1) for index, label in enumerate(job.options)},
           "option_position": {label: index for index, label in enumerate(job.options, start=1)}}
    result = summarize([row])["engines"]["jev"]
    assert result["successful"] == 1
    assert result["complete"] is False
    assert result["strict_one_dominance"] is True
