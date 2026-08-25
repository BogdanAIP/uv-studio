from __future__ import annotations

import unittest

from uv_studio.capabilities.builtin import build_builtin_capability_registry
from uv_studio.capabilities.models import MediaKind
from uv_studio.generation.builtin import build_builtin_model_registry
from uv_studio.generation.models import (
    GenerationContract,
    GenerationValidationError,
    ModelDefinition,
    ModelRegistry,
    ModelRegistryError,
)


class GenerationModelContractTests(unittest.TestCase):
    def test_generation_contract_round_trips_provider_neutral_constraints(self) -> None:
        contract = GenerationContract(
            fixed_constraints=("Анна остаётся в красном шарфе",),
            editable_variables=("выражение лица", "положение камеры"),
            forbidden_changes=("не менять персонажа",),
            approved_reference_id="asset_anna_keyframe",
        )

        restored = GenerationContract.from_dict(contract.to_dict())

        self.assertEqual(restored, contract)
        self.assertNotIn("prompt", contract.to_dict())
        self.assertNotIn("provider", contract.to_dict())

    def test_generation_contract_rejects_duplicate_constraints(self) -> None:
        with self.assertRaises(GenerationValidationError):
            GenerationContract(
                fixed_constraints=("same", "same"),
            )

    def test_builtin_named_model_identity_is_separate_from_execution_mapping(self) -> None:
        registry = build_builtin_model_registry()

        model = registry.get("uv.image.standard")
        described = registry.describe(model.model_id)

        self.assertEqual(model.model_id, "uv.image.standard")
        self.assertEqual(model.capability_id, "image.generate")
        self.assertEqual(model.offer_id, "native_videoclaw.image_generate")
        self.assertEqual(described["output_kind"], "image")
        self.assertEqual(described["execution"]["adapter_id"], "native_videoclaw")
        self.assertEqual(described["execution"]["availability"], "configuration_required")

    def test_model_registry_rejects_offer_for_different_capability(self) -> None:
        capabilities = build_builtin_capability_registry()
        registry = ModelRegistry(capabilities)

        with self.assertRaises(ModelRegistryError):
            registry.register(
                ModelDefinition(
                    model_id="uv.image.invalid",
                    title="Invalid mapping",
                    description="Must not cross capability boundaries.",
                    capability_id="image.generate",
                    offer_id="native_videoclaw.text_generate",
                    output_kind=MediaKind.IMAGE,
                )
            )


if __name__ == "__main__":
    unittest.main()
