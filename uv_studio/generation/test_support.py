"""Strictly opt-in test generation transport for browser Product Truth proof.

This module is not a product model/provider. It is activated only by the
explicit ``UV_STUDIO_E2E_TEST_GENERATION=1`` process environment variable so
CI can prove the complete UI -> backend -> project -> Take path without
pretending a configured external generation provider exists on user machines.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from uv_studio.capabilities.models import (
    AdapterDefinition,
    AdapterKind,
    CapabilityOffer,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
)
from uv_studio.capabilities.registry import CapabilityRegistry

from .models import ModelDefinition, ModelRegistry

TEST_GENERATION_ENV = "UV_STUDIO_E2E_TEST_GENERATION"
TEST_ADAPTER_ID = "stage14_e2e_generator"
TEST_OFFER_ID = "stage14_e2e_generator.image_generate"
TEST_MODEL_ID = "uv.image.e2e_test"

# Valid deterministic 1x1 PNG. The browser proof cares about product ownership,
# provenance and Take/Timeline semantics rather than visual model quality.
_TEST_PNG = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8cfc000000401010089990d1d"
    "0000000049454e44ae426082"
)


def enabled() -> bool:
    return os.environ.get(TEST_GENERATION_ENV) == "1"


def model_registry_with_test_model(base: CapabilityRegistry) -> ModelRegistry:
    offers = tuple(
        offer
        for capability in base.list_capabilities()
        for offer in base.offers_for(capability.capability_id)
    )
    capabilities = CapabilityRegistry(
        base.list_capabilities(),
        base.list_adapters(),
        offers,
    )
    capabilities.register_adapter(
        AdapterDefinition(
            adapter_id=TEST_ADAPTER_ID,
            title="Stage 14 E2E generator",
            description="Test-only local deterministic media materializer.",
            kind=AdapterKind.LOCAL,
        )
    )
    capabilities.register_offer(
        CapabilityOffer(
            offer_id=TEST_OFFER_ID,
            capability_id="image.generate",
            adapter_id=TEST_ADAPTER_ID,
            title="Stage 14 E2E image generation",
            availability=OfferAvailability.AVAILABLE,
            reason="Enabled only for browser Product Truth verification.",
            locality=LocalityClass.LOCAL,
            cost_class=CostClass.FREE,
            asynchronous=True,
            features=("e2e_test_only",),
        )
    )

    from .builtin import build_builtin_model_registry

    registry = build_builtin_model_registry(capabilities)
    registry.register(
        ModelDefinition(
            model_id=TEST_MODEL_ID,
            title="UV Image · E2E test only",
            description=(
                "Deterministic local test model visible only when the explicit "
                "Stage 14 E2E environment gate is enabled."
            ),
            capability_id="image.generate",
            offer_id=TEST_OFFER_ID,
            output_kind=MediaKind.IMAGE,
        )
    )
    return registry


class Stage14E2ETestExecutor:
    def execute(self, *, output_path: Path, **_: Any) -> Mapping[str, Any]:
        if not enabled():
            raise RuntimeError("Stage 14 E2E generation executor is not enabled")
        output_path.write_bytes(_TEST_PNG)
        return {
            "test_only": True,
            "transport": TEST_ADAPTER_ID,
            "deterministic": True,
        }
