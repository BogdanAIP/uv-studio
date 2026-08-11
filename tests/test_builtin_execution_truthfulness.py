from __future__ import annotations

import unittest

from uv_studio.capabilities import build_builtin_capability_registry
from uv_studio.capabilities.adapters.native_videoclaw import EDGE_TTS_OFFER_ID
from uv_studio.capabilities.models import CostClass, LocalityClass, OfferAvailability


class BuiltinExecutionTruthfulnessTests(unittest.TestCase):
    def test_only_exact_edge_tts_native_offer_may_be_available(self) -> None:
        registry = build_builtin_capability_registry()
        native_offers = tuple(
            offer
            for offer in registry.list_offers()
            if offer.adapter_id == "native_videoclaw"
        )
        self.assertTrue(native_offers)

        edge = next(offer for offer in native_offers if offer.offer_id == EDGE_TTS_OFFER_ID)
        self.assertEqual(edge.locality, LocalityClass.REMOTE)
        self.assertEqual(edge.cost_class, CostClass.FREE)
        self.assertIn(
            edge.availability,
            (OfferAvailability.AVAILABLE, OfferAvailability.UNAVAILABLE),
        )

        for offer in native_offers:
            if offer.offer_id == EDGE_TTS_OFFER_ID:
                continue
            self.assertEqual(
                offer.availability,
                OfferAvailability.CONFIGURATION_REQUIRED,
                f"native offer {offer.offer_id!r} must not advertise availability without an exact executor/config contract",
            )

    def test_every_current_builtin_available_offer_has_a_known_execution_family(self) -> None:
        registry = build_builtin_capability_registry()
        executable_adapter_ids = {"local_ffmpeg", "native_videoclaw"}
        for offer in registry.list_offers():
            if offer.availability is not OfferAvailability.AVAILABLE:
                continue
            self.assertIn(
                offer.adapter_id,
                executable_adapter_ids,
                f"built-in AVAILABLE offer {offer.offer_id!r} has no current execution family",
            )
            if offer.adapter_id == "native_videoclaw":
                self.assertEqual(offer.offer_id, EDGE_TTS_OFFER_ID)


if __name__ == "__main__":
    unittest.main()
