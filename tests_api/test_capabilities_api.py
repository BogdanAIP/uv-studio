from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from uv_studio.server import app


class CapabilitiesApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_catalog_starts_without_credentials_and_exposes_cost_metadata(self) -> None:
        response = self.client.get("/api/uv/capabilities")
        self.assertEqual(response.status_code, 200, response.text)
        capabilities = response.json()
        ids = [item["capability_id"] for item in capabilities]
        self.assertIn("video.generate", ids)
        self.assertIn("timeline.assemble", ids)
        self.assertIn("speech.synthesize", ids)
        self.assertIn("video.compose_photos", ids)
        self.assertIn("audio.visualize", ids)
        self.assertIn("video.digital_human", ids)

        encoded = str(capabilities).lower()
        for forbidden in ("api_key", "secret", "bearer "):
            self.assertNotIn(forbidden, encoded)

    def test_local_timeline_offer_is_declared_free_and_local(self) -> None:
        response = self.client.get("/api/uv/capabilities/timeline.assemble/offers")
        self.assertEqual(response.status_code, 200, response.text)
        offers = response.json()
        local = next(item for item in offers if item["offer_id"] == "local_ffmpeg.timeline_assemble")
        self.assertEqual(local["cost_class"], "free")
        self.assertEqual(local["locality"], "local")
        self.assertEqual(local["adapter"]["kind"], "local")
        self.assertIn(local["availability"], {"available", "unavailable"})

    def test_native_generation_offer_is_configuration_required(self) -> None:
        response = self.client.get("/api/uv/capabilities/video.generate/offers")
        self.assertEqual(response.status_code, 200, response.text)
        offers = response.json()
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer["availability"], "configuration_required")
        self.assertEqual(offer["cost_class"], "potentially_paid")
        self.assertEqual(offer["adapter"]["adapter_id"], "native_videoclaw")

    def test_digital_human_exposes_only_optional_local_musetalk_offer(self) -> None:
        response = self.client.get("/api/uv/capabilities/video.digital_human/offers")
        self.assertEqual(response.status_code, 200, response.text)
        offers = response.json()
        self.assertEqual(len(offers), 1)
        offer = offers[0]
        self.assertEqual(offer["offer_id"], "local_musetalk.video_digital_human")
        self.assertEqual(offer["adapter"]["adapter_id"], "local_musetalk")
        self.assertEqual(offer["adapter"]["kind"], "local")
        self.assertEqual(offer["locality"], "local")
        self.assertEqual(offer["cost_class"], "free")
        self.assertEqual(offer["availability"], "configuration_required")
        self.assertNotIn("native_videoclaw", offer["offer_id"])

    def test_capability_detail_contains_offer_summary(self) -> None:
        response = self.client.get("/api/uv/capabilities/video.generate")
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()
        self.assertEqual(detail["offer_summary"]["total"], 1)
        self.assertEqual(detail["offer_summary"]["configuration_required"], 1)

        digital_human = self.client.get("/api/uv/capabilities/video.digital_human").json()
        self.assertEqual(digital_human["offer_summary"]["total"], 1)
        self.assertEqual(digital_human["offer_summary"]["configuration_required"], 1)

    def test_unknown_capability_is_404(self) -> None:
        self.assertEqual(self.client.get("/api/uv/capabilities/missing.capability").status_code, 404)
        self.assertEqual(self.client.get("/api/uv/capabilities/missing.capability/offers").status_code, 404)


if __name__ == "__main__":
    unittest.main()
