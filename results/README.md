# Results

Run `benford-decisions release` only after all three matrices are complete. It
validates the 2,880 successful request IDs per engine, then writes the combined
summary, exact digit/word example requests and replies, a model/environment
manifest, and deterministic gzip JSONL archives in `data/answers/`. The
manifest contains SHA-256 checksums. Historical setup failures are retained in
the local run log but excluded from the clean replay archives; they are not
model responses. No partial run should be described as a three-model result.

`benford-decisions charts` generates the 1200x630 social preview and two
article figures from successful archived records. Plots refuse to run until
each engine has all expected responses.
