from __future__ import annotations

import unittest
from unittest import mock

from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
)
from uv_studio.capabilities.adapters.argos_translate import (
    ArgosTranslateAdapter,
    register_argos_translate_adapter,
)
from uv_studio.capabilities.execution import InvalidCapabilityInput


class _Translation:
    def translate(self, text: str) -> str:
        return {"Hello": "Привет", "World": "Мир"}.get(text, f"RU:{text}")


class _Language:
    def __init__(self, code: str) -> None:
        self.code = code

    def get_translation(self, target):
        if self.code == "en" and target.code == "ru":
            return _Translation()
        return None


class _Store:
    def __init__(self) -> None:
        self.loaded: list[str] = []

    def load_project(self, project_id: str):
        self.loaded.append(project_id)
        return object()


class ArgosTranslateAdapterTests(unittest.TestCase):
    @staticmethod
    def _offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_argos_translate.text_translate",
            "text.translate",
            "local_argos_translate",
            "Argos local translation",
            OfferAvailability.AVAILABLE,
            "configured",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    @staticmethod
    def _registry() -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "text.translate",
            "Translate",
            "Translate text segments",
            OperationKind.TRANSFORMATION,
            (MediaKind.TEXT,),
            (MediaKind.TEXT,),
        )
        registry = CapabilityRegistry(
            (capability,),
            (
                AdapterDefinition(
                    "placeholder",
                    "Placeholder",
                    "Keeps registry constructor non-empty for this test",
                    AdapterKind.LOCAL,
                ),
            ),
        )
        return registry

    def test_registration_is_configuration_required_when_optional_runtime_is_absent(self) -> None:
        registry = self._registry()
        with mock.patch(
            "uv_studio.capabilities.adapters.argos_translate._runtime_installed",
            return_value=False,
        ):
            register_argos_translate_adapter(registry)
        offer = registry.offers_for("text.translate")[0]
        self.assertEqual(offer.availability, OfferAvailability.CONFIGURATION_REQUIRED)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertEqual(offer.cost_class, CostClass.FREE)
        self.assertIn("runtime.optional", offer.features)

    def test_available_adapter_preserves_segment_identity_and_normalizes_language_tags(self) -> None:
        store = _Store()
        adapter = ArgosTranslateAdapter(
            store, language_loader=lambda: [_Language("en"), _Language("ru")]
        )
        result = adapter.execute(
            project_id="proj_argos",
            offer=self._offer(),
            payload={
                "source_language": "en-US",
                "target_language": "ru-RU",
                "segments": [
                    {"segment_id": "seg_1", "text": "Hello"},
                    {"segment_id": "seg_2", "text": "World"},
                ],
            },
        )
        self.assertEqual(store.loaded, ["proj_argos"])
        self.assertEqual(result.output["source_language"], "en")
        self.assertEqual(result.output["target_language"], "ru")
        self.assertEqual(
            result.output["segments"],
            [
                {"segment_id": "seg_1", "text": "Привет"},
                {"segment_id": "seg_2", "text": "Мир"},
            ],
        )

    def test_missing_language_pair_and_unknown_segment_fields_fail_closed(self) -> None:
        adapter = ArgosTranslateAdapter(
            _Store(), language_loader=lambda: [_Language("en"), _Language("ru")]
        )
        with self.assertRaisesRegex(InvalidCapabilityInput, "translation package"):
            adapter.execute(
                project_id="proj_argos",
                offer=self._offer(),
                payload={
                    "source_language": "ru",
                    "target_language": "en",
                    "segments": [{"segment_id": "seg_1", "text": "Привет"}],
                },
            )
        with self.assertRaisesRegex(InvalidCapabilityInput, "unsupported segments"):
            adapter.execute(
                project_id="proj_argos",
                offer=self._offer(),
                payload={
                    "source_language": "en",
                    "target_language": "ru",
                    "segments": [
                        {"segment_id": "seg_1", "text": "Hello", "provider": "remote"}
                    ],
                },
            )


if __name__ == "__main__":
    unittest.main()
