from __future__ import annotations

import unittest

from uv_studio.capabilities import build_builtin_capability_registry
from uv_studio.capabilities.models import MediaKind, OperationKind


class MusicAnalysisCapabilityTests(unittest.TestCase):
    def test_semantic_music_analysis_exists_without_mandatory_provider(self) -> None:
        registry = build_builtin_capability_registry()
        capability = registry.get_capability("audio.analyze_music")
        self.assertEqual(capability.operation_kind, OperationKind.UNDERSTANDING)
        self.assertEqual(capability.input_kinds, (MediaKind.AUDIO,))
        self.assertEqual(capability.output_kinds, (MediaKind.METADATA,))
        self.assertEqual(registry.offers_for("audio.analyze_music"), ())


if __name__ == "__main__":
    unittest.main()
