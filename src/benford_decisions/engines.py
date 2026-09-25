"""Small, auditable adapters for the three registered engines."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import os
import platform
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from .study import INSTRUCTIONS, QUESTION_NAME, STATE, Job

JEV_MODEL = "jev-latest"
JEV_INPUT_USD_PER_MILLION = 0.042
KEV_MODEL = "kev-latest"
KEV_CHECKPOINT = "jaredpalmer/kev-0.8b@54f4f8777356cd5bbbb6c6919c657f26e6f2f6d8"
KEV_SERVER_REVISION = "c9c1f855505336ac32092a5f68305d397f7fcc3e"
KEV_BASE_REVISION = "dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68"
LAYA_PACKAGE_VERSION = "0.3.20"
LAYA_CHECKPOINT_REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"


def request_payload(engine: str, job: Job) -> dict:
    """Return the exact non-secret logical request envelope sent to an engine."""
    model = {"jev": JEV_MODEL, "kev": KEV_MODEL, "laya": "english"}.get(engine)
    if model is None:
        raise ValueError(f"unknown engine: {engine}")
    return {"state": STATE, "model": model,
            "questions": {QUESTION_NAME: job.question()}}


def jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return {key: jsonable(item) for key, item in vars(value).items()
                if not key.startswith("_")}
    return value


def _version(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def common_provenance() -> dict:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


def make_adapter(engine: str):
    if engine == "jev":
        return JevAdapter()
    if engine == "kev":
        return KevAdapter()
    if engine == "laya":
        return LayaAdapter()
    raise ValueError(f"unknown engine: {engine}")


class JevAdapter:
    def __init__(self):
        if not os.environ.get("TYPESAFE_API_KEY"):
            raise RuntimeError("TYPESAFE_API_KEY is required for Jev")
        try:
            from typesafe_sdk import AsyncTypeSafeClient
            from typesafe_sdk import Choice
        except ImportError as error:
            raise RuntimeError("install decision-models-are-not-calculators[jev] before using Jev") from error
        self._client = AsyncTypeSafeClient()
        self._choice_type = Choice

    async def provenance(self) -> dict:
        return {**common_provenance(), "engine": "jev",
                "requested_model": JEV_MODEL,
                "typesafe_sdk": _version("typesafe-sdk"),
                "pricing_source": "https://typesafe.ai/blog/introducing-system-one-models-and-jev",
                "input_price_usd_per_million_tokens": JEV_INPUT_USD_PER_MILLION}

    async def answer(self, job: Job) -> tuple[dict, dict, float]:
        question = job.question()
        typed_question = self._choice_type(
            instructions=INSTRUCTIONS,
            criteria=question["criteria"],
        )
        started = time.perf_counter()
        response = await self._client.system_one(
            state=STATE,
            questions={QUESTION_NAME: typed_question},
            model=JEV_MODEL,
        )
        elapsed = (time.perf_counter() - started) * 1000
        payload = jsonable(response)
        answer = payload.get("answers", {}).get(QUESTION_NAME)
        if not isinstance(answer, dict):
            raise ValueError("Jev response does not contain the requested answer")
        return payload, answer, elapsed


class KevAdapter:
    def __init__(self):
        self.base_url = os.environ.get("KEV_BASE_URL", "").rstrip("/")
        if not self.base_url:
            raise RuntimeError("KEV_BASE_URL must point to the registered Kev server")
        self.api_key = os.environ.get("KEV_API_KEY")
        self.model = os.environ.get("KEV_MODEL", KEV_MODEL)
        if self.model != KEV_MODEL:
            raise RuntimeError(f"registered Kev model is {KEV_MODEL}, not {self.model}")
        self._headers = {"Content-Type": "application/json"}
        if self.api_key:
            self._headers["Authorization"] = f"Bearer {self.api_key}"
        self._identity = None

    def _get(self, path: str) -> dict:
        request = Request(self.base_url + path, headers=self._headers, method="GET")
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    async def provenance(self) -> dict:
        models = await asyncio.to_thread(self._get, "/v1/models")
        candidates = models.get("models", models.get("data", []))
        entry = next((row for row in candidates
                      if row.get("name") == self.model or row.get("id") == self.model), None)
        if not entry:
            raise RuntimeError("Kev /v1/models did not identify kev-latest")
        if entry.get("run") != KEV_CHECKPOINT:
            raise RuntimeError("Kev checkpoint differs from the pre-registered revision")
        if entry.get("backend") not in (None, "mlx") or entry.get("dtype") not in (None, "bfloat16"):
            raise RuntimeError("Kev backend or dtype differs from the registered runtime")
        if entry.get("temperature") is not None and abs(
                float(entry["temperature"]) - 2.406050072164233) > 1e-12:
            raise RuntimeError("Kev calibration differs from the pinned checkpoint")
        self._identity = entry
        return {**common_provenance(), "engine": "kev", "server_model": entry,
                "server_revision": KEV_SERVER_REVISION,
                "base_revision": KEV_BASE_REVISION,
                "api_key_required": bool(self.api_key)}

    async def answer(self, job: Job) -> tuple[dict, dict, float]:
        payload = request_payload("kev", job)
        request = Request(self.base_url + "/v1/systemone",
                          data=json.dumps(payload).encode("utf-8"),
                          headers=self._headers, method="POST")

        def send():
            with urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))

        started = time.perf_counter()
        result = await asyncio.to_thread(send)
        elapsed = (time.perf_counter() - started) * 1000
        answer = result.get("answers", {}).get(QUESTION_NAME)
        if not isinstance(answer, dict):
            raise ValueError("Kev response does not contain the requested answer")
        return result, answer, elapsed


class LayaAdapter:
    def __init__(self):
        checkpoint = os.environ.get("LAYA_CHECKPOINT_PATH", "")
        if not checkpoint:
            raise RuntimeError("LAYA_CHECKPOINT_PATH must point to the pinned English checkpoint")
        self.checkpoint = Path(checkpoint).expanduser().resolve()
        if not self.checkpoint.is_dir():
            raise RuntimeError(f"Laya checkpoint directory does not exist: {self.checkpoint}")
        if self.checkpoint.name != LAYA_CHECKPOINT_REVISION:
            raise RuntimeError("Laya checkpoint directory must end in the registered revision")
        try:
            import torch
            from laya import Router
        except ImportError as error:
            raise RuntimeError("install decision-models-are-not-calculators[laya] and PyTorch before using Laya") from error
        self._torch = torch
        device = os.environ.get("LAYA_DEVICE", "mps" if platform.system() == "Darwin" else "cpu")
        self.device = device
        self._router = Router(models={"english": str(self.checkpoint)},
                              default="english", device=device,
                              max_loaded=1, auto_task_detection=False)

    async def provenance(self) -> dict:
        return {**common_provenance(), "engine": "laya",
                "package_version": _version("laya"),
                "checkpoint": "convaiinnovations/laya",
                "checkpoint_revision": LAYA_CHECKPOINT_REVISION,
                "checkpoint_path": str(self.checkpoint),
                "device": self.device,
                "torch": self._torch.__version__,
                "torchvision": _version("torchvision"),
                "transformers": _version("transformers"),
                "mps_available": bool(self._torch.backends.mps.is_available()),
                "checkpoint_warning": (
                    "The checkpoint emits invalid temperatures for some option cardinalities; "
                    "Laya clamps them to 0.5. Do not interpret its separate confidence score "
                    "as calibrated for those entries. This study records choice probabilities."
                )}

    async def answer(self, job: Job) -> tuple[dict, dict, float]:
        request = request_payload("laya", job)
        started = time.perf_counter()
        response = await asyncio.to_thread(
            self._router.predict, STATE, request["questions"], model="english")
        elapsed = (time.perf_counter() - started) * 1000
        payload = jsonable(response)
        answer = payload.get("answers", {}).get(QUESTION_NAME)
        if not isinstance(answer, dict):
            raise ValueError("Laya response does not contain the requested answer")
        return {"request": request, "response": payload}, answer, elapsed


def validate_answer(job: Job, answer: dict) -> dict[str, float]:
    if answer.get("type") != "choice":
        raise ValueError("answer type is not choice")
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict) or set(probabilities) != set(job.options):
        raise ValueError("answer probabilities do not contain exactly the requested choices")
    normalized: dict[str, float] = {}
    for option in job.options:
        value = probabilities[option]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"probability for {option!r} is not numeric")
        if not 0 <= float(value) <= 1:
            raise ValueError(f"probability for {option!r} is outside [0, 1]")
        normalized[option] = float(value)
    # Hosted Jev reports probabilities to two decimal places. Six independently
    # rounded values may miss 1 by up to 6 * 0.005; retain the raw values.
    tolerance = (len(job.options) * 0.005 + 1e-9 if job.engine == "jev"
                 else max(0.00031, len(job.options) * 0.0000501))
    if abs(sum(normalized.values()) - 1.0) > tolerance:
        raise ValueError("choice probabilities do not sum to one")
    if answer.get("choice") not in job.options:
        raise ValueError("selected choice is absent from the requested options")
    return normalized
