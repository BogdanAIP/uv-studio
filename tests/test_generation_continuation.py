from __future__ import annotations

import unittest

from uv_studio.generation.jobs import generation_request_digest
from uv_studio.generation.models import GenerationContract


class GenerationContinuationDigestTests(unittest.TestCase):
    @staticmethod
    def _digest(parent_reference_id: str) -> str:
        digest, _request = generation_request_digest(
            project_id="prj_continuation_digest",
            shot_id="shot_continuation_digest",
            model_id="uv.video.continuation.test",
            capability_id="video.generate",
            offer_id="test_generator.video_generate",
            adapter_id="test_generator",
            inputs={"instruction": "continue and move the camera left"},
            contract=GenerationContract(
                fixed_constraints=("same subject",),
                editable_variables=("camera",),
                continuation_source_reference_id=parent_reference_id,
            ),
        )
        return digest

    def test_parent_reference_is_part_of_idempotency_identity(self) -> None:
        first = self._digest("artifact_parent_a")
        replay = self._digest("artifact_parent_a")
        different_parent = self._digest("artifact_parent_b")

        self.assertEqual(first, replay)
        self.assertNotEqual(first, different_parent)


if __name__ == "__main__":
    unittest.main()
