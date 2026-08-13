from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uv_studio.capabilities import CostClass, LocalityClass, OfferAvailability
from uv_studio.capabilities.builtin import build_builtin_capability_registry


def _which_with_asr_runtime(tool: str) -> str | None:
    if tool == "whisper-cli":
        return "/tools/whisper-cli"
    if tool == "ffmpeg":
        return "/tools/ffmpeg"
    return None


class WhisperCppRegistryTests(unittest.TestCase):
    def _offer(self):
        return next(
            item
            for item in build_builtin_capability_registry().offers_for("speech.transcribe")
            if item.offer_id == "local_whisper_cpp.speech_transcribe"
        )

    def test_offer_is_unavailable_without_runtime(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch(
            "uv_studio.capabilities.builtin.shutil.which", return_value=None
        ):
            offer = self._offer()
        self.assertEqual(offer.availability, OfferAvailability.UNAVAILABLE)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertEqual(offer.cost_class, CostClass.FREE)

    def test_offer_is_unavailable_without_ffmpeg_even_when_runtime_and_model_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "whisper-cli"
            model = root / "ggml-model.bin"
            runtime.write_bytes(b"runtime")
            model.write_bytes(b"model")
            env = {
                "UV_WHISPER_CPP_BIN": str(runtime),
                "UV_WHISPER_CPP_MODEL": str(model),
            }
            with mock.patch.dict("os.environ", env, clear=True), mock.patch(
                "uv_studio.capabilities.builtin.shutil.which", return_value=None
            ):
                offer = self._offer()
        self.assertEqual(offer.availability, OfferAvailability.UNAVAILABLE)
        self.assertIn("FFmpeg", offer.reason)
        self.assertNotIn(str(runtime), offer.reason)
        self.assertNotIn(str(model), offer.reason)

    def test_offer_requires_model_after_runtime_and_ffmpeg_are_found(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True), mock.patch(
            "uv_studio.capabilities.builtin.shutil.which", side_effect=_which_with_asr_runtime
        ):
            offer = self._offer()
        self.assertEqual(offer.availability, OfferAvailability.CONFIGURATION_REQUIRED)
        self.assertNotIn("/tools/whisper-cli", offer.reason)
        self.assertNotIn("/tools/ffmpeg", offer.reason)

    def test_offer_is_available_with_runtime_ffmpeg_and_model_without_leaking_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / "whisper-cli"
            model = root / "ggml-model.bin"
            runtime.write_bytes(b"runtime")
            model.write_bytes(b"model")
            env = {
                "UV_WHISPER_CPP_BIN": str(runtime),
                "UV_WHISPER_CPP_MODEL": str(model),
            }
            with mock.patch.dict("os.environ", env, clear=True), mock.patch(
                "uv_studio.capabilities.builtin.shutil.which", side_effect=_which_with_asr_runtime
            ):
                offer = self._offer()

        self.assertEqual(offer.availability, OfferAvailability.AVAILABLE)
        self.assertEqual(offer.locality, LocalityClass.LOCAL)
        self.assertEqual(offer.cost_class, CostClass.FREE)
        self.assertFalse(offer.asynchronous)
        self.assertIn("speech.timestamps", offer.features)
        self.assertNotIn(str(runtime), offer.reason)
        self.assertNotIn(str(model), offer.reason)
        self.assertNotIn("/tools/ffmpeg", offer.reason)

    def test_semantic_translation_and_alignment_capabilities_exist_without_fake_offers(self) -> None:
        registry = build_builtin_capability_registry()
        self.assertEqual(registry.offers_for("text.translate"), ())
        self.assertEqual(registry.offers_for("audio.align"), ())


if __name__ == "__main__":
    unittest.main()
