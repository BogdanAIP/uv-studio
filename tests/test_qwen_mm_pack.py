from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from uv_studio.capabilities import CostClass, LocalityClass, build_builtin_capability_registry
from uv_studio.integrations.qwen_mm import (
    API_PACK,
    CORE_PACK,
    QWEN_MM_UPSTREAM_SHA,
    VIDEO_EDIT_PACK,
    QwenMMPlatformUnsupported,
    configure_qwen_mm_pack,
)
from uv_studio.mcp.store import MCPConfigStore


class QwenMMPackTests(unittest.TestCase):
    def test_profiles_pin_exact_upstream_commit_not_main(self) -> None:
        for pack in (CORE_PACK, API_PACK, VIDEO_EDIT_PACK):
            requirement = pack.profile.args[1]
            self.assertIn(QWEN_MM_UPSTREAM_SHA, requirement)
            self.assertNotIn(".git@main", requirement)
            self.assertEqual(pack.profile.command, "uvx")

    def test_core_binds_only_clean_local_free_media_probe(self) -> None:
        self.assertEqual(len(CORE_PACK.bindings), 1)
        binding = CORE_PACK.bindings[0]
        self.assertEqual(binding.tool_name, "media_info")
        self.assertEqual(binding.capability_id, "media.probe")
        self.assertEqual(binding.locality, LocalityClass.LOCAL)
        self.assertEqual(binding.cost_class, CostClass.FREE)
        self.assertIn("read_video", CORE_PACK.intentionally_unbound_tools)
        self.assertIn("visualize", CORE_PACK.intentionally_unbound_tools)

    def test_cloud_api_bindings_are_never_declared_free(self) -> None:
        self.assertTrue(API_PACK.cloud_backed)
        self.assertGreater(len(API_PACK.bindings), 0)
        for binding in API_PACK.bindings:
            self.assertEqual(binding.locality, LocalityClass.REMOTE)
            self.assertEqual(binding.cost_class, CostClass.POTENTIALLY_PAID)
        self.assertEqual(
            dict(API_PACK.profile.env_refs),
            {"DASHSCOPE_API_KEY": "DASHSCOPE_API_KEY"},
        )
        self.assertIn("segmentation", API_PACK.intentionally_unbound_tools)

    def test_video_edit_generation_is_cloud_paid_capable_and_happyhorse_unbound(self) -> None:
        by_tool = {binding.tool_name: binding for binding in VIDEO_EDIT_PACK.bindings}
        self.assertEqual(by_tool["qwen_image"].capability_id, "image.generate")
        self.assertEqual(by_tool["qwen_tts"].capability_id, "speech.synthesize")
        self.assertEqual(by_tool["wan_t2v"].capability_id, "video.generate")
        self.assertEqual(by_tool["wan_s2v"].capability_id, "video.digital_human")
        for binding in by_tool.values():
            self.assertEqual(binding.locality, LocalityClass.REMOTE)
            self.assertEqual(binding.cost_class, CostClass.POTENTIALLY_PAID)
        self.assertEqual(VIDEO_EDIT_PACK.intentionally_unbound_tools, ("happyhorse",))

    def test_speech_transcribe_is_provider_neutral_builtin_capability(self) -> None:
        capability = build_builtin_capability_registry().get_capability("speech.transcribe")
        self.assertEqual(capability.operation_kind.value, "speech")
        self.assertEqual({kind.value for kind in capability.input_kinds}, {"audio", "video"})

    def test_configure_pack_persists_env_reference_not_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MCPConfigStore(Path(tmp))
            os.environ["DASHSCOPE_API_KEY"] = "super-secret-dashscope-value"
            try:
                config = configure_qwen_mm_pack(store, "video-edit", platform="linux")
                raw = store.path.read_text(encoding="utf-8")
                self.assertNotIn("super-secret-dashscope-value", raw)
                self.assertIn("DASHSCOPE_API_KEY", raw)
                self.assertEqual(config.get_profile("qwen-mm-video-edit"), VIDEO_EDIT_PACK.profile)
            finally:
                os.environ.pop("DASHSCOPE_API_KEY", None)

    def test_configuring_one_pack_preserves_unrelated_profiles_and_replaces_same_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MCPConfigStore(Path(tmp))
            first = configure_qwen_mm_pack(store, "core", platform="linux")
            self.assertEqual(len(first.profiles), 1)
            second = configure_qwen_mm_pack(store, "api", platform="linux")
            self.assertEqual({p.profile_id for p in second.profiles}, {"qwen-mm-core", "qwen-mm-api"})
            third = configure_qwen_mm_pack(store, "core", platform="linux")
            self.assertEqual(len([p for p in third.profiles if p.profile_id == "qwen-mm-core"]), 1)

    def test_native_windows_configuration_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(QwenMMPlatformUnsupported):
                configure_qwen_mm_pack(MCPConfigStore(Path(tmp)), "core", platform="win32")


if __name__ == "__main__":
    unittest.main()
