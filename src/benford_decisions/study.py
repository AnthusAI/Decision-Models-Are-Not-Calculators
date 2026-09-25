"""Frozen inputs and exhaustive request plan for the registered study."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Iterator, Literal

ENGINE_NAMES = ("jev", "kev", "laya")
FACES = ("1", "2", "3", "4", "5", "6")
WORDS = ("one", "two", "three", "four", "five", "six")
REPRESENTATIONS = ("digits", "words")
PASSES = (1, 2)
STATE = "A fair six-sided die was rolled once. The result is unknown."
QUESTION_NAME = "die_result"
INSTRUCTIONS = "Which face showed on the roll?"
STUDY_ID = "fair-die-option-order-v1"


@dataclass(frozen=True)
class Job:
    engine: str
    representation: Literal["digits", "words"]
    pass_number: int
    permutation_rank: int
    options: tuple[str, ...]

    @property
    def request_id(self) -> str:
        return (f"{self.engine}:{self.representation}:pass-{self.pass_number}:"
                f"order-{self.permutation_rank:03d}")

    @property
    def labels(self) -> tuple[str, ...]:
        return FACES if self.representation == "digits" else WORDS

    def face_for_label(self, label: str) -> str:
        return str(self.labels.index(label) + 1)

    def question(self) -> dict:
        # The criterion order is intentional: it is the treatment being tested.
        criteria = {label: f"the die face marked {label}"
                    for label in self.options}
        return {
            "type": "choice",
            "instructions": INSTRUCTIONS,
            "criteria": criteria,
        }

    def request(self) -> dict:
        return {
            "state": STATE,
            "questions": {QUESTION_NAME: self.question()},
        }


def orders(representation: str) -> Iterator[tuple[int, tuple[str, ...]]]:
    """Yield each face permutation in numeric-face order, independent of label form."""
    if representation not in REPRESENTATIONS:
        raise ValueError(f"unknown representation: {representation}")
    labels = FACES if representation == "digits" else WORDS
    for rank, face_order in enumerate(permutations(range(6)), start=1):
        yield rank, tuple(labels[face] for face in face_order)


def jobs(engine: str, representation: str | None = None,
         pass_number: int | None = None) -> Iterator[Job]:
    if engine not in ENGINE_NAMES:
        raise ValueError(f"unknown engine {engine!r}; expected one of {ENGINE_NAMES}")
    reps = (representation,) if representation else REPRESENTATIONS
    passes = (pass_number,) if pass_number else PASSES
    if any(rep not in REPRESENTATIONS for rep in reps):
        raise ValueError(f"representation must be one of {REPRESENTATIONS}")
    if any(number not in PASSES for number in passes):
        raise ValueError(f"pass must be one of {PASSES}")
    for number in passes:
        for rep in reps:
            for rank, options in orders(rep):
                yield Job(engine, rep, number, rank, options)


def complete_request_ids(engine: str) -> set[str]:
    return {job.request_id for job in jobs(engine)}
