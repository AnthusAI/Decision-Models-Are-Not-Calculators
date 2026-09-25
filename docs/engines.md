# Engine builds and provenance

This study uses the three systems documented in the neighboring
[`Biased-Decisions`](https://github.com/AnthusAI/Biased-Decisions) project.
The engines are not interchangeable: Jev is a hosted TypeSafe service, Kev is
an open-weight Qwen3.5-derived checkpoint served through a compatible local
API, and Laya is a local ModernBERT classifier. See the source survey in
Biased-Decisions for references and licensing details.

## Jev

- API: TypeSafe System One endpoint via `typesafe-sdk==0.7.1`.
- Requested model: `jev-latest` (a mutable hosted alias; record response model
  identity/version with every run when returned).
- Input price used for the $1 guard: $0.042 per million input tokens; output
  uncharged. Price source: [TypeSafe's System One announcement](https://typesafe.ai/blog/introducing-system-one-models-and-jev).
- Provide `TYPESAFE_API_KEY` through the environment. The runner never writes
  this value to results.

## Kev

- Model API name: `kev-latest`.
- Checkpoint: `jaredpalmer/kev-0.8b@54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8`.
- Service source revision: `c9c1f855505336ac32092a5f68305d397f7fcc3e`.
- Base source revision: `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`.
- Apple Silicon build: MLX, bfloat16, registered temperature 2.406050072164233,
  prefix cache disabled, date facts disabled. The repository's reproducible
  service setup is available in its `var/start_kev.py` wrapper and pinned local
  checkout; do not substitute another checkpoint or alias silently.
- Set `KEV_BASE_URL` to the service address (normally
  `http://127.0.0.1:8009`). The runner checks `/v1/models` before collecting.

## Laya

- Package: `laya==0.3.20`.
- Model: `convaiinnovations/laya`, English classifier snapshot revision
  `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`.
- Set `LAYA_CHECKPOINT_PATH` to a local directory for that exact revision.
- Default device is MPS on macOS and CPU elsewhere; record the actual device.
  Do not use the separate `laya-mlx` fork for this upstream Laya arm.

Model weights/service code have their own terms; this study harness is MIT.
