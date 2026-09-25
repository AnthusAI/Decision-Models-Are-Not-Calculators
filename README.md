# Decision Models Are Not Calculators

An exhaustive, replayable test of how Jev, Kev, and Laya assign probabilities to
a fair six-sided die when the six choice labels are reordered.

The study tests all 720 orders with digit labels and all 720 with word labels,
then repeats the full set once. Each model receives 2,880 requests. The test
measures what these pinned models return for this prompt. It does not identify
what data or training process caused the answers.

## Results (25 September 2026)

All **8,640 planned requests** returned valid responses: 720 choice orders ×
two label forms × two passes × three models. The literal “always one” claim
held for **Jev**, which selected face 1 in all 2,880 replies. It failed for
**Kev**, which selected face 1 in 1,410/2,880 replies (49.0%), and for
**Laya**, which selected face 6 in 2,610/2,880 replies (90.6%).

| Model | Selected face 1 | Selected face 6 | Digit-pass-1 mean probability for face 1 | Digit-pass-1 mean probability for face 6 |
| --- | ---: | ---: | ---: | ---: |
| Jev | 2,880 / 2,880 | 0 | 89.7% | 4.4% |
| Kev | 1,410 / 2,880 | 294 / 2,880 | 18.6% | 18.4% |
| Laya | 40 / 2,880 | 2,610 / 2,880 | 6.5% | 66.2% |

Changing choice order mattered for Kev and Laya, although every face occupied
every position exactly 120 times in each representation/pass. In the first
digit pass, Kev selected the **first-listed option** 426/720 times (59.2%);
Laya selected the **last-listed option** 0/720 times. Jev always selected
face 1, so its selected position was perfectly balanced: 120/720 at each
position. Changing digits to words changed the selected face for 324 of 720
paired orders in Kev, 129 in Laya, and none in Jev. Exact repeats selected
the same face in every case for all three models; Jev's returned probabilities
varied slightly, while Kev's and Laya's were identical.

![Measured probabilities by die face for Jev, Kev, and Laya](images/decision-models-are-not-calculators-cover.png)

See the [full summary](results/summary.json),
[exact example requests and replies](results/examples.json),
[checksummed release manifest](results/release-manifest.json),
[Jev response archive](data/answers/jev-responses.jsonl.gz),
[Kev response archive](data/answers/kev-responses.jsonl.gz), and
[Laya response archive](data/answers/laya-responses.jsonl.gz). The
[face-probability plot](images/decision-models-face-probabilities.png) and
[choice-position plot](images/decision-models-option-position.png) show the
representation and ordering effects.

One concrete request used this state: `A fair six-sided die was rolled once.
The result is unknown.` It asked `Which face showed on the roll?` with the
six digit labels `1` through `6` as alternatives. For that order, Jev replied
`1` (probability for one `0.88`); Kev replied `6` (probability for six
`0.1975`); Laya replied `1` (probability for one `0.3988`). Those are
individual replies, not representative averages. The
linked examples preserve the full request envelopes and unedited model replies.

Benford’s Law describes the first digits of certain *observed numerical
datasets*. This experiment does not inspect training data and cannot establish
Benford’s Law as the cause of any model behavior. A die with an unobserved fair
roll has a one-in-six probability for each face; these model replies are not
measurements of that roll.

## Study protocol

The frozen protocol is in [`docs/PREREGISTERED.md`](docs/PREREGISTERED.md).
Release status and limitations are in [`results/README.md`](results/README.md).
The [measurement note](docs/measurement-notes.md) records Jev's two-decimal
probability rounding and the transparent validator correction.

## Run the harness

Python 3.12 or newer is required. The core harness and replay need only the
standard library; engines and plots have separate optional dependencies.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
decision-models plan
```

Set up one engine at a time using its pinned build notes. Credentials must be
provided through the process environment and must never be committed.

```sh
python -m pip install -e '.[jev]'
TYPESAFE_API_KEY=... decision-models run --engine jev
decision-models summarize --engine jev
```

Run the registered Kev service on loopback as documented in
[`docs/engines.md`](docs/engines.md), then:

```sh
KEV_BASE_URL=http://127.0.0.1:8009 decision-models run --engine kev
```

Laya runs locally. Install the pinned package and use the exact checkpoint
revision documented in [`docs/engines.md`](docs/engines.md):

```sh
python -m pip install -e '.[laya]'
export LAYA_CHECKPOINT_PATH=/path/to/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851
decision-models run --engine laya
```

The runner checkpoints each response. Re-running skips completed request IDs
and retries the first failed or unattempted request. It stops at the first
error to avoid repeating a systemic failure across thousands of calls. Results
are accepted only when the expected model identity and response shape are
present. Raw local records are written to `data/answers/<engine>.jsonl`; clean,
complete, checksummed replay archives are exported by the `release` command.

```sh
decision-models summarize --engine all
python -m pip install -e '.[charts]'
decision-models charts
```

## Reproduce the published results

The complete release was created with `decision-models release` and
`decision-models charts`. Both commands require all three complete engines
unless an explicitly labelled interim release is requested with
`--allow-incomplete`. See
[`results/README.md`](results/README.md).
The summary code makes no model calls. It verifies complete permutation
coverage and regenerates the article data from the raw answer record.

## License

The harness is MIT-licensed. Model code, weights, and services retain their
authors' terms; see the build notes before running an engine.
