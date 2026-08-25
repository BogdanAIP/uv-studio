from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from uv_studio.projects.dubbing_alignment import (
    DubbingAlignment,
    DubbingAlignmentError,
    DubbingAlignmentMark,
    DubbingAlignmentState,
    DubbingAlignmentStore,
)
from uv_studio.projects.prepared_speech import PreparedSpeechTake, canonical_revision_sha256
from uv_studio.projects.store import ProjectStore


class _PreparedSpeechState:
    def __init__(self, take: PreparedSpeechTake) -> None:
        self.take = take

    def get(self, take_id: str) -> PreparedSpeechTake:
        if take_id != self.take.take_id:
            raise AssertionError("unexpected take_id")
        return self.take


class _PreparedSpeechFacade:
    def __init__(self, take: PreparedSpeechTake) -> None:
        self.take = take

    def validate_project(self, project_id: str) -> _PreparedSpeechState:
        return _PreparedSpeechState(self.take)


class _DubbingState:
    def __init__(self, transcript, translation=None) -> None:
        self.transcript = transcript
        self.translation = translation

    def get_transcript(self, dubbing_id: str):
        if dubbing_id != self.transcript.dubbing_id:
            raise AssertionError("unexpected dubbing_id")
        return self.transcript

    def get_translation(self, translation_id: str):
        if self.translation is None or translation_id != self.translation.translation_id:
            raise AssertionError("unexpected translation_id")
        return self.translation


class _DubbingFacade:
    def __init__(self, state: _DubbingState) -> None:
        self.state = state

    def validate_project(self, project_id: str) -> _DubbingState:
        return self.state


class DubbingAlignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.project_store = ProjectStore(Path(self.tmp.name) / "projects")
        self.project = self.project_store.create_project(recipe_id="general_video", title="Alignment")
        self.take = PreparedSpeechTake(
            take_id="take_1",
            dubbing_id="dub_1",
            script_kind="transcript",
            script_id="dub_1",
            script_sha256="1" * 64,
            audio_id="aud_1",
            audio_sha256="2" * 64,
            duration_us=1_900_000,
            origin="recorded",
            segment_id="seg_1",
        )
        self.transcript = SimpleNamespace(
            dubbing_id="dub_1",
            language="en",
            start_us=1_000_000,
            end_us=5_000_000,
            segments=(
                SimpleNamespace(
                    segment_id="seg_1",
                    start_us=2_000_000,
                    end_us=4_000_000,
                ),
            ),
        )
        self.store = DubbingAlignmentStore(self.project_store)
        self.store.prepared_speech = _PreparedSpeechFacade(self.take)
        self.store.dubbing = _DubbingFacade(_DubbingState(self.transcript))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _alignment(self, *, alignment_id: str = "align_1", take: PreparedSpeechTake | None = None):
        current_take = take or self.take
        return DubbingAlignment(
            alignment_id=alignment_id,
            take_id=current_take.take_id,
            take_sha256=canonical_revision_sha256(current_take.to_dict()),
            dubbing_id=current_take.dubbing_id,
            script_kind=current_take.script_kind,
            script_id=current_take.script_id,
            script_sha256=current_take.script_sha256,
            audio_id=current_take.audio_id,
            audio_sha256=current_take.audio_sha256,
            language="en",
            segment_id=current_take.segment_id,
            target_start_us=2_000_000,
            target_end_us=4_000_000,
            marks=(
                DubbingAlignmentMark(
                    mark_id="mark_1",
                    unit="word",
                    text="Hello",
                    audio_start_us=100_000,
                    audio_end_us=650_000,
                    confidence=0.95,
                ),
                DubbingAlignmentMark(
                    mark_id="mark_2",
                    unit="word",
                    text="world",
                    audio_start_us=700_000,
                    audio_end_us=1_400_000,
                    confidence=0.91,
                ),
            ),
        )

    def test_roundtrip_persists_provider_neutral_alignment_bound_to_exact_take_revision(self) -> None:
        saved = self.store.upsert(self.project.project_id, self._alignment())
        self.assertEqual(saved.alignments[0].take_id, self.take.take_id)
        raw = saved.to_dict()
        text = str(raw).lower()
        self.assertNotIn("whisperx", text)
        self.assertNotIn("provider", text)
        self.assertNotIn("model", text)

        reopened = DubbingAlignmentStore(self.project_store)
        reopened.prepared_speech = _PreparedSpeechFacade(self.take)
        reopened.dubbing = _DubbingFacade(_DubbingState(self.transcript))
        validated = reopened.validate_project(self.project.project_id)
        self.assertEqual(validated.to_dict(), raw)

    def test_marks_must_be_ordered_non_overlapping_and_within_audio_duration(self) -> None:
        with self.assertRaisesRegex(DubbingAlignmentError, "must not overlap"):
            DubbingAlignmentState(
                alignments=(
                    DubbingAlignment(
                        alignment_id="align_overlap",
                        take_id=self.take.take_id,
                        take_sha256=canonical_revision_sha256(self.take.to_dict()),
                        dubbing_id=self.take.dubbing_id,
                        script_kind=self.take.script_kind,
                        script_id=self.take.script_id,
                        script_sha256=self.take.script_sha256,
                        audio_id=self.take.audio_id,
                        audio_sha256=self.take.audio_sha256,
                        language="en",
                        segment_id=self.take.segment_id,
                        target_start_us=2_000_000,
                        target_end_us=4_000_000,
                        marks=(
                            DubbingAlignmentMark("mark_a", "word", "A", 0, 700_000, 0.8),
                            DubbingAlignmentMark("mark_b", "word", "B", 600_000, 900_000, 0.8),
                        ),
                    ),
                )
            )

        overlong = self._alignment(alignment_id="align_overlong")
        overlong = DubbingAlignment(
            **{
                **{key: value for key, value in overlong.to_dict().items() if key not in {"marks", "schema_version"}},
                "marks": (
                    DubbingAlignmentMark("mark_long", "word", "Long", 1_800_000, 2_000_000, 0.8),
                ),
            }
        )
        with self.assertRaisesRegex(DubbingAlignmentError, "exceeds prepared speech duration"):
            self.store.upsert(self.project.project_id, overlong)

    def test_take_or_script_revision_change_makes_alignment_stale_fail_closed(self) -> None:
        self.store.upsert(self.project.project_id, self._alignment())
        changed_take = PreparedSpeechTake(
            **{
                **self.take.to_dict(),
                "script_sha256": "3" * 64,
            }
        )
        self.store.prepared_speech = _PreparedSpeechFacade(changed_take)
        with self.assertRaisesRegex(DubbingAlignmentError, "prepared speech take changed"):
            self.store.validate_project(self.project.project_id)

    def test_only_one_current_alignment_per_take_is_allowed(self) -> None:
        first = self._alignment(alignment_id="align_first")
        second = self._alignment(alignment_id="align_second")
        state = DubbingAlignmentState(alignments=(first,))
        replaced = state.upsert(second)
        self.assertEqual([item.alignment_id for item in replaced.alignments], ["align_second"])


if __name__ == "__main__":
    unittest.main()
