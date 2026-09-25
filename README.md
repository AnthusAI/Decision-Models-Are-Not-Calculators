# Benford Decisions

An exhaustive, replayable test of how Jev, Kev, and Laya assign probabilities to
a fair six-sided die when the six choice labels are reordered.

The study tests all 720 orders with digit labels and all 720 with word labels,
then repeats the full set once. Each model receives 2,880 requests. The test
measures what these pinned models return for this prompt. It does not identify
what data or training process caused the answers.

## Study status

Pre-registration and results: see [`docs/PREREGISTERED.md`](docs/PREREGISTERED.md)
and [`results/README.md`](results/README.md). Raw answers are retained as JSONL
and compressed in the release record when collection is complete.

## Run the harness

Python 3.12 or newer is required. The core harness and replay need only the
standard library; engines and plots have separate optional dependencies.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
benford-decisions plan
```

Set up one engine at a time using its pinned build notes. Credentials must be
provided through the process environment and must never be committed.

```sh
python -m pip install -e '.[jev]'
TYPESAFE_API_KEY=... benford-decisions run --engine jev
benford-decisions summarize --engine jev
```

Run the registered Kev service on loopback as documented in
[`docs/engines.md`](docs/engines.md), then:

```sh
KEV_BASE_URL=http://127.0.0.1:8009 benford-decisions run --engine kev
```

Laya runs locally. Install the pinned package and use the exact checkpoint
revision documented in [`docs/engines.md`](docs/engines.md):

```sh
python -m pip install -e '.[laya]'
export LAYA_CHECKPOINT_PATH=/path/to/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851
benford-decisions run --engine laya
```

The runner checkpoints each response. Re-running skips completed request IDs
and retries the first failed or unattempted request. It stops at the first
error to avoid repeating a systemic failure across thousands of calls. Results
are accepted only when the expected model identity and response shape are
present. Raw local records are written to `data/answers/<engine>.jsonl`; clean,
complete, checksummed replay archives are exported by the `release` command.

```sh
benford-decisions summarize --engine all
python -m pip install -e '.[charts]'
benford-decisions charts
```

## Reproduce the published results

After all three engines are complete, create the committed response archives,
SHA-256 manifest, run provenance, summaries, and exact example request/reply
records with `benford-decisions release`. See [`results/README.md`](results/README.md).
The summary code makes no model calls. It verifies complete permutation
coverage and regenerates the article data from the raw answer record.

## License

The harness is MIT-licensed. Model code, weights, and services retain their
authors' terms; see the build notes before running an engine.
