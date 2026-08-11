from __future__ import annotations

import unittest

from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CapabilityValidationError,
    CostClass,
    DuplicateCapability,
    LocalityClass,
    MediaKind,
    OfferAvailability,
    OperationKind,
    UnknownAdapter,
    UnknownCapability,
    build_builtin_capability_registry,
)


class CapabilityRegistryTests(unittest.TestCase):
    def test_builtin_registry_starts_without_credentials(self) -> None:
        registry = build_builtin_capability_registry()
        ids = [item.capability_id for item in registry.list_capabilities()]
        self.assertIn("video.generate", ids)
        self.assertIn("timeline.assemble", ids)
        self.assertIn("speech.synthesize", ids)

    def test_local_ffmpeg_offer_is_free_and_local(self) -> None:
        offer = next(
            item
            for item in build_builtin_capability_registry().offers_for("timeline.assemble")
            if item.offer_id == "local_ffmpeg.timeline_assemble"
        )
        self.assertEqual(offer.cost_class, CostClass.FREE)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertIn(offer.availability, {OfferAvailability.AVAILABLE, OfferAvailability.UNAVAILABLE})

    def test_native_model_offer_requires_configuration_and_is_not_declared_free(self) -> None:
        offers = build_builtin_capability_registry().offers_for("video.generate")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].availability, OfferAvailability.CONFIGURATION_REQUIRED)
        self.assertEqual(offers[0].cost_class, CostClass.POTENTIALLY_PAID)

    def test_digital_human_has_no_false_native_offer(self) -> None:
        self.assertEqual(
            build_builtin_capability_registry().offers_for("video.digital_human"),
            (),
        )

    def test_offer_preference_is_available_then_free_then_local(self) -> None:
        cap = CapabilityDefinition(
            "test.capability",
            "Test",
            "Test capability",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.TEXT,),
        )
        adapters = (
            AdapterDefinition("remote_adapter", "Remote", "Remote adapter", AdapterKind.MCP),
            AdapterDefinition("local_adapter", "Local", "Local adapter", AdapterKind.LOCAL),
        )
        registry = CapabilityRegistry([cap], adapters)
        registry.register_offer(
            CapabilityOffer(
                "remote_adapter.paid",
                cap.capability_id,
                "remote_adapter",
                "Remote paid",
                OfferAvailability.AVAILABLE,
                "Configured",
                LocalityClass.REMOTE,
                CostClass.PAID,
                False,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "local_adapter.free",
                cap.capability_id,
                "local_adapter",
                "Local free",
                OfferAvailability.AVAILABLE,
                "Installed",
                LocalityClass.LOCAL,
                CostClass.FREE,
                False,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "remote_adapter.unconfigured",
                cap.capability_id,
                "remote_adapter",
                "Remote unconfigured",
                OfferAvailability.CONFIGURATION_REQUIRED,
                "Needs configuration",
                LocalityClass.REMOTE,
                CostClass.FREE,
                False,
            )
        )
        self.assertEqual(
            [item.offer_id for item in registry.offers_for(cap.capability_id)],
            ["local_adapter.free", "remote_adapter.paid", "remote_adapter.unconfigured"],
        )

    def test_offer_must_reference_registered_capability_and_adapter(self) -> None:
        cap = CapabilityDefinition(
            "known.capability",
            "Known",
            "Known capability",
            OperationKind.UNDERSTANDING,
            (MediaKind.TEXT,),
            (MediaKind.METADATA,),
        )
        registry = CapabilityRegistry([cap])
        offer = CapabilityOffer(
            "missing_adapter.offer",
            cap.capability_id,
            "missing_adapter",
            "Broken",
            OfferAvailability.UNAVAILABLE,
            "Missing adapter",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )
        with self.assertRaises(UnknownAdapter):
            registry.register_offer(offer)

    def test_duplicate_capability_is_rejected(self) -> None:
        cap = CapabilityDefinition(
            "duplicate.capability",
            "Duplicate",
            "Duplicate capability",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.TEXT,),
        )
        registry = CapabilityRegistry([cap])
        with self.assertRaises(DuplicateCapability):
            registry.register_capability(cap)

    def test_invalid_capability_id_is_rejected(self) -> None:
        with self.assertRaises(CapabilityValidationError):
            CapabilityDefinition(
                "../bad",
                "Bad",
                "Bad capability",
                OperationKind.GENERATION,
                (MediaKind.TEXT,),
                (MediaKind.TEXT,),
            )

    def test_unknown_capability_is_explicit(self) -> None:
        with self.assertRaises(UnknownCapability):
            build_builtin_capability_registry().get_capability("missing.capability")

    def test_public_metadata_contains_no_secret_values(self) -> None:
        registry = build_builtin_capability_registry()
        payload = {
            "capabilities": [item.to_dict() for item in registry.list_capabilities()],
            "adapters": [item.to_dict() for item in registry.list_adapters()],
            "offers": [
                offer.to_dict()
                for capability in registry.list_capabilities()
                for offer in registry.offers_for(capability.capability_id)
            ],
        }
        encoded = str(payload).lower()
        for forbidden in ("api_key", "secret", "token=", "bearer "):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
