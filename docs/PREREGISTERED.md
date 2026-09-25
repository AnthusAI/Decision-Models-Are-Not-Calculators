# Pre-registration: fair die, option order, and decision-model probabilities

**Study ID:** `fair-die-option-order-v1`
**Frozen:** 2026-09-25, before inference
**Engines:** Jev (`jev-latest`), Kev (`kev-latest`, registered 0.8B checkpoint), and Laya (English checkpoint at the recorded immutable revision)

## Question

When asked to identify the outcome of a fair six-sided die roll whose result is
unknown, do these decision models assign unequal probabilities to the faces,
and do their answers change when the same six choices are presented in a
different order or written as digits rather than words?

This experiment evaluates returned probabilities and selected choices. It does
not reveal a model's internal reasoning, training distribution, or the cause of
any observed preference. Benford's Law is a motivation for asking about the
digit `1`, not a causal explanation tested by this experiment.

## Exact prompt

State: `A fair six-sided die was rolled once. The result is unknown.`

Question: `Which face showed on the roll?`

Type: `choice`, with six ordered criteria. For digit treatment the criterion
keys are `1` through `6`; for word treatment they are `one` through `six`.
Each value is `the die face marked {key}`. Criteria insertion order is the
assigned order. No prompt mentions Benford, bias, or a preferred answer.

## Design

For each engine, run every one of the 720 permutations of the six semantic faces
in digit form and every one of the 720 permutations in word form. Repeat the
entire matrix once, in the same deterministic permutation sequence. This yields
2,880 requests per engine and 8,640 total. Request order is pass, representation
(`digits`, then `words`), then lexicographic permutation of semantic faces.
Each face appears exactly 120 times at each position within a representation
and pass. Runs are serial within an engine; a failed request is recorded and
can be retried by its stable request ID.

The repeats are a stability check, not independent model samples. There is no
sampling uncertainty from the known complete set of option orders; no
confidence intervals or significance tests will be used.

## Outcomes

For every response retain raw response, normalized selected face, returned
probability for each semantic face, choice position, exact request, model/build
identity, latency, and timestamp. Report exact counts and mean probabilities
for each face by engine, representation, and pass; selected-face counts by
choice position; and the pass-1/pass-2 difference.

**Primary confirmatory claim:** in the digit treatment, face `1` is the
highest-probability choice in every response, in both complete passes. Any
non-`1` top response falsifies the literal “always predict one” claim for that
engine. A strict top-probability tie counts as not uniquely top. Report each
engine independently and do not pool them.

**Order sensitivity:** report exact variation in selected face and mean
probability by position across the balanced permutation set, alongside
face-level distributions. Avoid causal claims beyond the manipulated ordering
and label representation. No threshold will be used to convert the descriptive
order results into a general model property.

## Stopping, budget, and exclusions

Run the full matrix for each engine. Do not silently exclude malformed or failed
responses: retain them as errors, publish coverage, and retry only the exact
failed request. Mark an engine incomplete if any of its 2,880 successful
responses is missing. Jev input-token spend is capped at $1; the runner must
perform a conservative preflight estimate before issuing requests and record
returned usage/cost when available. No secret or API key is retained.

## Frozen reporting

Publish raw responses, a checksum, environment/build provenance, executable
summary/plot code, and this pre-registration. Clearly separate the observed
model outputs from the hypothesis that Benford-like frequency in training
material caused them. Mention version aliases and immutable revisions wherever
available; a hosted alias can change independently of this repository.
