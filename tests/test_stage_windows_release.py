from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.stage_windows_release import WindowsReleaseStageError, stage_windows_release


class StageWindowsReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        self.backend = self.root / "backend-source"
        self.backend.mkdir()
        (self.backend / "uv-studio-backend.exe").write_bytes(b"backend")
        backend_runtime = self.backend / "_internal"
        backend_runtime.mkdir()
        (backend_runtime / "python313.dll").write_bytes(b"python")

        self.frontend = self.root / "frontend-source"
        self.frontend.mkdir()
        (self.frontend / "server.js").write_text("server\n", encoding="utf-8")
        traced = self.frontend / "node_modules" / "next"
        traced.mkdir(parents=True)
        (traced / "package.json").write_text("{}\n", encoding="utf-8")

        self.node = self.root / "node.exe"
        self.node.write_bytes(b"node")
        self.node_license = self.root / "node-LICENSE.txt"
        self.node_license.write_text("Node license\n", encoding="utf-8")

        self.uv_license = self.root / "UV-LICENSE.txt"
        self.uv_license.write_text("UV Studio license\n", encoding="utf-8")
        self.third_party_notices = self.root / "THIRD_PARTY_NOTICES.md"
        self.third_party_notices.write_text("# Notices\n", encoding="utf-8")
        self.release_profile = self.root / "runtime-profile.json"
        self.release_profile.write_text('{"schema_version": 4}\n', encoding="utf-8")

        self.media = self.root / "media-source"
        ffmpeg_dir = self.media / "bin"
        ffmpeg_dir.mkdir(parents=True)
        self.ffmpeg = ffmpeg_dir / "ffmpeg.exe"
        self.ffprobe = ffmpeg_dir / "ffprobe.exe"
        self.ffmpeg.write_bytes(b"ffmpeg")
        self.ffprobe.write_bytes(b"ffprobe")
        mlt_dir = self.media / "mlt" / "bin"
        mlt_dir.mkdir(parents=True)
        self.melt = mlt_dir / "melt.exe"
        self.melt.write_bytes(b"melt")
        plugin_dir = self.media / "mlt" / "lib" / "mlt"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "filter.dll").write_bytes(b"plugin")

        qt_runtime = (
            self.media
            / "distribution"
            / "bin"
            / "Qt"
            / "plugins"
            / "platforms"
        )
        qt_runtime.mkdir(parents=True)
        (qt_runtime / "qwindows.dll").write_bytes(b"qt-runtime")
        qt_test = (
            self.media
            / "distribution"
            / "bin"
            / "Qt"
            / "test"
            / "controls"
            / "objects-RelWithDebInfo"
            / "QuickControlsTestUtilsPrivate_resources_1"
            / ".qt"
            / "rcc"
        )
        qt_test.mkdir(parents=True)
        (qt_test / "qrc_qmake_Qt_test_controls_init.cpp.obj").write_bytes(
            b"qt-test-object"
        )
        (qt_test / "fixture.txt").write_bytes(b"qt-test-fixture")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _stage(self, output: Path | None = None) -> tuple[Path, dict[str, object]]:
        target = output or (self.root / "release")
        result = stage_windows_release(
            backend_root=self.backend,
            frontend_root=self.frontend,
            node_executable=self.node,
            node_license_file=self.node_license,
            media_root=self.media,
            ffmpeg_executable=self.ffmpeg,
            ffprobe_executable=self.ffprobe,
            mlt_executable=self.melt,
            uv_license_file=self.uv_license,
            third_party_notices_file=self.third_party_notices,
            release_profile_file=self.release_profile,
            output_root=target,
        )
        return target, result

    def test_stage_preserves_runtime_components_notices_and_provenance(self) -> None:
        output, result = self._stage()
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["entrypoints"],
            {
                "backend": "backend/uv-studio-backend.exe",
                "frontend": "frontend/server.js",
                "node": "runtime/node/node.exe",
                "ffmpeg": "runtime/media/bin/ffmpeg.exe",
                "ffprobe": "runtime/media/bin/ffprobe.exe",
                "mlt": "runtime/media/mlt/bin/melt.exe",
            },
        )
        self.assertTrue(
            (output / "backend" / "_internal" / "python313.dll").is_file()
        )
        self.assertTrue(
            (
                output
                / "frontend"
                / "node_modules"
                / "next"
                / "package.json"
            ).is_file()
        )
        self.assertTrue((output / "runtime" / "node" / "node.exe").is_file())
        self.assertTrue(
            (output / "runtime" / "media" / "mlt" / "lib" / "mlt" / "filter.dll").is_file()
        )
        self.assertTrue(
            (
                output
                / "runtime"
                / "media"
                / "distribution"
                / "bin"
                / "Qt"
                / "plugins"
                / "platforms"
                / "qwindows.dll"
            ).is_file()
        )
        self.assertFalse(
            (
                output
                / "runtime"
                / "media"
                / "distribution"
                / "bin"
                / "Qt"
                / "test"
            ).exists()
        )
        self.assertEqual(result["excluded_media_file_count"], 2)
        self.assertEqual(
            result["media_exclusion_rules"],
            [
                "**/bin/Qt/test/**",
                "share/shotcut/**",
                "ffplay.exe",
                "glaxnimate.exe",
                "shotcut.exe",
                "whisper-cli.exe",
            ],
        )
        self.assertGreaterEqual(result["media_file_count"], 5)
        self.assertEqual(
            result["legal_files"],
            [
                "legal/UV-STUDIO-LICENSE.txt",
                "legal/THIRD-PARTY-NOTICES.md",
                "legal/release-inputs.windows-x86_64.json",
                "legal/node/LICENSE.txt",
            ],
        )
        self.assertEqual(
            (output / "legal" / "UV-STUDIO-LICENSE.txt").read_text(
                encoding="utf-8"
            ),
            "UV Studio license\n",
        )
        self.assertEqual(
            (output / "legal" / "THIRD-PARTY-NOTICES.md").read_text(
                encoding="utf-8"
            ),
            "# Notices\n",
        )
        self.assertEqual(
            (output / "legal" / "node" / "LICENSE.txt").read_text(
                encoding="utf-8"
            ),
            "Node license\n",
        )
        self.assertEqual(
            (output / "legal" / "release-inputs.windows-x86_64.json").read_text(
                encoding="utf-8"
            ),
            '{"schema_version": 4}\n',
        )

    def test_media_exclusion_is_case_insensitive_like_windows_paths(self) -> None:
        alternate = self.media / "other" / "BIN" / "qt" / "TEST" / "nested"
        alternate.mkdir(parents=True)
        (alternate / "artifact.obj").write_bytes(b"object")
        output, result = self._stage()
        self.assertFalse(
            (output / "runtime" / "media" / "other" / "BIN" / "qt" / "TEST").exists()
        )
        self.assertEqual(result["excluded_media_file_count"], 3)

    def test_shotcut_application_surface_is_pruned_without_pruning_runtime(self) -> None:
        for filename in ("shotcut.exe", "ffplay.exe", "glaxnimate.exe", "whisper-cli.exe"):
            (self.media / filename).write_bytes(filename.encode("ascii"))
        shotcut_ui = self.media / "share" / "shotcut" / "qml"
        shotcut_ui.mkdir(parents=True)
        (shotcut_ui / "Main.qml").write_text("ui\n", encoding="utf-8")
        runtime_share = self.media / "share" / "mlt-7"
        runtime_share.mkdir(parents=True)
        (runtime_share / "profiles.yml").write_text("runtime\n", encoding="utf-8")
        nested_helper = self.media / "tools"
        nested_helper.mkdir()
        (nested_helper / "shotcut.exe").write_bytes(b"not-top-level")

        output, result = self._stage()
        media_output = output / "runtime" / "media"
        for filename in ("shotcut.exe", "ffplay.exe", "glaxnimate.exe", "whisper-cli.exe"):
            self.assertFalse((media_output / filename).exists())
        self.assertFalse((media_output / "share" / "shotcut").exists())
        self.assertTrue((media_output / "share" / "mlt-7" / "profiles.yml").is_file())
        self.assertTrue((media_output / "tools" / "shotcut.exe").is_file())
        self.assertTrue((media_output / "mlt" / "lib" / "mlt" / "filter.dll").is_file())
        self.assertEqual(result["excluded_media_file_count"], 7)

    def test_required_media_entrypoint_inside_exclusion_fails_closed(self) -> None:
        test_dir = self.media / "bundle" / "bin" / "Qt" / "test"
        test_dir.mkdir(parents=True)
        excluded_melt = test_dir / "melt.exe"
        excluded_melt.write_bytes(b"melt")
        output = self.root / "release"
        with self.assertRaisesRegex(
            WindowsReleaseStageError, "non-runtime media exclusion"
        ):
            stage_windows_release(
                backend_root=self.backend,
                frontend_root=self.frontend,
                node_executable=self.node,
                node_license_file=self.node_license,
                media_root=self.media,
                ffmpeg_executable=self.ffmpeg,
                ffprobe_executable=self.ffprobe,
                mlt_executable=excluded_melt,
                uv_license_file=self.uv_license,
                third_party_notices_file=self.third_party_notices,
                release_profile_file=self.release_profile,
                output_root=output,
            )
        self.assertFalse(output.exists())

    def test_existing_destination_is_rejected_without_merging(self) -> None:
        output = self.root / "release"
        output.mkdir()
        stale = output / "stale.txt"
        stale.write_text("keep", encoding="utf-8")
        with self.assertRaises(WindowsReleaseStageError):
            self._stage(output)
        self.assertEqual(stale.read_text(encoding="utf-8"), "keep")

    def test_media_entrypoint_outside_media_root_is_rejected(self) -> None:
        foreign = self.root / "foreign-ffmpeg.exe"
        foreign.write_bytes(b"foreign")
        output = self.root / "release"
        with self.assertRaises(WindowsReleaseStageError):
            stage_windows_release(
                backend_root=self.backend,
                frontend_root=self.frontend,
                node_executable=self.node,
                node_license_file=self.node_license,
                media_root=self.media,
                ffmpeg_executable=foreign,
                ffprobe_executable=self.ffprobe,
                mlt_executable=self.melt,
                uv_license_file=self.uv_license,
                third_party_notices_file=self.third_party_notices,
                release_profile_file=self.release_profile,
                output_root=output,
            )
        self.assertFalse(output.exists())

    def test_missing_required_component_entrypoint_fails_closed(self) -> None:
        (self.backend / "uv-studio-backend.exe").unlink()
        output = self.root / "release"
        with self.assertRaises(WindowsReleaseStageError):
            self._stage(output)
        self.assertFalse(output.exists())

    def test_missing_legal_input_fails_closed_before_output_creation(self) -> None:
        self.node_license.unlink()
        output = self.root / "release"
        with self.assertRaisesRegex(WindowsReleaseStageError, "Node license is missing"):
            self._stage(output)
        self.assertFalse(output.exists())

    def test_symlink_in_source_tree_is_rejected_even_under_excluded_subtree_when_supported(self) -> None:
        test_dir = self.media / "distribution" / "bin" / "Qt" / "test"
        link = test_dir / "shadow.obj"
        target = (
            test_dir
            / "controls"
            / "objects-RelWithDebInfo"
            / "QuickControlsTestUtilsPrivate_resources_1"
            / ".qt"
            / "rcc"
            / "fixture.txt"
        )
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable on this platform")
        output = self.root / "release"
        with self.assertRaises(WindowsReleaseStageError):
            self._stage(output)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
