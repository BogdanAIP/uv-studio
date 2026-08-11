from __future__ import annotations

import unittest

from uv_studio.capabilities import (
    AdapterDefinition,
    AdapterKind,
    CapabilityDefinition,
    CapabilityOffer,
    CapabilityRegistry,
    CostClass,
    LocalityClass,
    MediaKind,
    NoEligibleOffer,
    OfferAvailability,
    OfferSelectionRequired,
    OperationKind,
    PinnedOfferRejected,
    SelectionPolicy,
    select_offer,
)


class CapabilitySelectionTests(unittest.TestCase):
    def _registry(self) -> CapabilityRegistry:
        capability = CapabilityDefinition(
            "video.generate",
            "Video generation",
            "test capability",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.VIDEO,),
            asynchronous=True,
        )
        adapters = (
            AdapterDefinition("local_adapter", "Local", "local", AdapterKind.LOCAL),
            AdapterDefinition("remote_adapter", "Remote", "remote", AdapterKind.RUNTIME),
        )
        registry = CapabilityRegistry((capability,), adapters)
        registry.register_offer(
            CapabilityOffer(
                "local_adapter.free",
                "video.generate",
                "local_adapter",
                "Local free",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.LOCAL,
                CostClass.FREE,
                True,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "local_adapter.paid",
                "video.generate",
                "local_adapter",
                "Local paid",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.LOCAL,
                CostClass.PAID,
                True,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "remote_adapter.free",
                "video.generate",
                "remote_adapter",
                "Remote free",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.REMOTE,
                CostClass.FREE,
                True,
            )
        )
        return registry

    def test_local_free_first_selects_only_local_free(self) -> None:
        decision = select_offer(
            self._registry(),
            "video.generate",
            policy=SelectionPolicy.LOCAL_FREE_FIRST,
        )
        self.assertEqual(decision.offer.offer_id, "local_adapter.free")

    def test_local_free_first_never_falls_through_to_paid_or_remote(self) -> None:
        capability = CapabilityDefinition(
            "video.generate",
            "Video generation",
            "test capability",
            OperationKind.GENERATION,
            (MediaKind.TEXT,),
            (MediaKind.VIDEO,),
            asynchronous=True,
        )
        adapters = (
            AdapterDefinition("local_adapter", "Local", "local", AdapterKind.LOCAL),
            AdapterDefinition("remote_adapter", "Remote", "remote", AdapterKind.RUNTIME),
        )
        registry = CapabilityRegistry((capability,), adapters)
        registry.register_offer(
            CapabilityOffer(
                "local_adapter.paid",
                "video.generate",
                "local_adapter",
                "Local paid",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.LOCAL,
                CostClass.PAID,
                True,
            )
        )
        registry.register_offer(
            CapabilityOffer(
                "remote_adapter.free",
                "video.generate",
                "remote_adapter",
                "Remote free",
                OfferAvailability.AVAILABLE,
                "ready",
                LocalityClass.REMOTE,
                CostClass.FREE,
                True,
            )
        )
        with self.assertRaises(NoEligibleOffer):
            select_offer(registry, "video.generate", policy="local_free_first")

    def test_manual_never_auto_selects(self) -> None:
        with self.assertRaises(OfferSelectionRequired):
            select_offer(self._registry(), "video.generate", policy="manual")

    def test_pinned_offer_selects_exact_available_offer(self) -> None:
        decision = select_offer(
            self._registry(),
            "video.generate",
            policy="pinned_offer",
            pinned_offer_id="remote_adapter.free",
        )
        self.assertEqual(decision.offer.offer_id, "remote_adapter.free")

    def test_pinned_offer_requires_exact_known_offer(self) -> None:
        with self.assertRaises(PinnedOfferRejected):
            select_offer(
                self._registry(),
                "video.generate",
                policy="pinned_offer",
                pinned_offer_id="remote_adapter.missing",
            )


if __name__ == "__main__":
    unittest.main()
