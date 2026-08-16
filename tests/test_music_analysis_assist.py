from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from uv_studio.projects.models import ProjectReference
from uv_studio.projects.music_analysis_assist import (
    MusicAnalysisAssistError,
    build_music_analysis_assist,
    normalize_music_analysis_suggestion,
)
from uv_studio.projects.music_map import MusicMapStore
from uv_studio.projects.store import ProjectStore


class MusicAnalysisAssistTests(unittest.TestCase):
    def _setup(self, tmp: str):
        store = ProjectStore(Path(tmp) / "projects")
        project = store.create_project(title="Analysis assist", recipe_id="music_video")
        payload = b"analysis-assist-song"
        relative = "sources/song.wav"
        (store.project_directory(project.project_id) / relative).write_bytes(payload)
        reference = ProjectReference(
            id="song",
            kind="audio",
            path=relative,
            metadata={
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
                "duration_us": 30_000_000,
            },
        )
        store.update_project(project.project_id, sources=(reference,))
        return store, project.project_id

    def test_package_and_normalization_never_mutate_canonical_music_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._setup(tmp)
            package = build_music_analysis_assist(store, project_id, song_reference_id="song")
            self.assertEqual(package.to_dict()["capability_id"], "audio.analyze_music")
            self.assertFalse(package.to_dict()["canonical_state_mutated"])
            self.assertIsNone(MusicMapStore(store).load(project_id))
            normalized = normalize_music_analysis_suggestion(
                store,
                project_id,
                song_reference_id="song",
                payload={
                    "binding": package.binding.to_dict(),
                    "excerpt": {"start_us": 2_000_000, "end_us": 22_000_000},
                    "sections": [
                        {"section_id": "verse", "kind": "verse", "label": "Verse", "start_us": 2_000_000, "end_us": 12_000_000},
                        {"section_id": "chorus", "kind": "chorus", "label": "Chorus", "start_us": 12_000_000, "end_us": 22_000_000},
                    ],
                    "markers": [
                        {"marker_id": "drop", "kind": "climax", "time_us": 12_000_000}
                    ],
                    "lyric_phrases": [
                        {"phrase_id": "line", "start_us": 3_000_000, "end_us": 5_000_000, "text": "Suggested lyric"}
                    ],
                    "note": "advisory only",
                },
            )
            self.assertFalse(normalized["canonical_state_mutated"])
            self.assertEqual(normalized["sections"][1]["kind"], "chorus")
            self.assertIsNone(MusicMapStore(store).load(project_id))

    def test_stale_song_bytes_reject_prepared_suggestion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._setup(tmp)
            package = build_music_analysis_assist(store, project_id, song_reference_id="song")
            (store.project_directory(project_id) / "sources/song.wav").write_bytes(b"substituted")
            with self.assertRaises(MusicAnalysisAssistError):
                normalize_music_analysis_suggestion(
                    store,
                    project_id,
                    song_reference_id="song",
                    payload={
                        "binding": package.binding.to_dict(),
                        "excerpt": {"start_us": 0, "end_us": 10_000_000},
                        "sections": [], "markers": [], "lyric_phrases": [], "note": None,
                    },
                )

    def test_suggested_times_must_stay_inside_excerpt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store, project_id = self._setup(tmp)
            package = build_music_analysis_assist(store, project_id, song_reference_id="song")
            with self.assertRaisesRegex(MusicAnalysisAssistError, "outside"):
                normalize_music_analysis_suggestion(
                    store,
                    project_id,
                    song_reference_id="song",
                    payload={
                        "binding": package.binding.to_dict(),
                        "excerpt": {"start_us": 5_000_000, "end_us": 15_000_000},
                        "sections": [],
                        "markers": [{"marker_id": "bad", "kind": "beat", "time_us": 2_000_000}],
                        "lyric_phrases": [],
                        "note": None,
                    },
                )


if __name__ == "__main__":
    unittest.main()
