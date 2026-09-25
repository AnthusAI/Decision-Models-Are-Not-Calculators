# Measurement notes

## 2026-09-25: Jev probability precision

Jev's hosted response reports six probabilities to two decimal places. At
`jev:digits:pass-1:order-311`, one response contained
`0.93 + 0.02 + 0.01 + 0.01 + 0.00 + 0.02 = 0.99`. The initial harness check
allowed only a 0.00031 sum deviation, appropriate for four-decimal responses
but not for this Jev output. The failed attempts were retained in the local
collection log; no successful response was discarded.

The validator was corrected to allow the maximum error from rounding six
two-decimal numbers independently: `6 × 0.005 = 0.03`, with floating-point
slack. Values are **not renormalized**: released probabilities are exactly the
numbers the model returned. The request, permutation sequence, model alias,
and planned outcomes did not change. Kev and Laya retain their stricter
four-decimal tolerance. A regression test covers both checks.

The response archives contain one successful answer per planned request ID;
the manifest reports excluded failed attempts. This amendment concerns
validation of Jev's serialization precision, not a different experimental
condition.
