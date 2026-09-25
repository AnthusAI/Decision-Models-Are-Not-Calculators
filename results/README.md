# Results

This is the **complete three-model release**: Jev, Kev, and Laya each have
2,880 valid responses, covering every registered order, label form, and pass.

`decision-models release` validates all successful request IDs, then writes the combined
summary, exact digit/word example requests and replies, a model/environment
manifest, and deterministic gzip JSONL archives in `data/answers/`. The
manifest contains SHA-256 checksums. Historical setup failures are retained in
the local run log but excluded from the clean replay archives; they are not
model responses. No partial run should be described as a three-model result.

`decision-models charts` generates the 1200x630 social preview and two
article figures. Without the `--allow-incomplete` flag, both release and charts
refuse to run until all three engines have all expected responses. The Laya
archive excludes 2,880 initial setup failures
from an incompatible TorchVision environment; a corrected environment then
produced its 2,880 valid replies. The Jev archive excludes one initial HTTP
402 and two two-decimal probability-validation failures; credits and a
documented precision correction allowed the full run. See
[`docs/measurement-notes.md`](../docs/measurement-notes.md).
