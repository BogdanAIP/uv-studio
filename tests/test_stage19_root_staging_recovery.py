from __future__ import annotations

import asyncio
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from uv_studio.capabilities.adapters import LocalFFmpegAdapter
from uv_studio.capabilities.models import (
    CapabilityOffer,
    CostClass,
    LocalityClass,
    OfferAvailability,
)
from uv_studio.projects import root_staging as root_staging_module
from uv_studio.projects.identity import STUDIO_COMPAT_RECIPE_ID, studio_project_extensions
from uv_studio.projects.root_staging import (
    acquire_generation_root_staging,
    recover_stale_root_staging,
    release_root_staging,
)
from uv_studio.projects.store import ProjectStore


class Stage19RootStagingRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProjectStore(Path(self.tmp.name) / "projects")
        self.store.create_project(
            title="Root staging recovery",
            recipe_id=STUDIO_COMPAT_RECIPE_ID,
            extensions=studio_project_extensions("micro_drama"),
            project_id="prj_root_staging_recovery",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def _lease_path(path: Path) -> Path:
        return path.with_name(f"{path.name}.lease")

    @staticmethod
    def _timeline_offer() -> CapabilityOffer:
        return CapabilityOffer(
            "local_ffmpeg.timeline_assemble",
            "timeline.assemble",
            "local_ffmpeg",
            "local_ffmpeg.timeline_assemble",
            OfferAvailability.AVAILABLE,
            "test",
            LocalityClass.LOCAL,
            CostClass.FREE,
            False,
        )

    def _make_stale(self, name: str, payload: bytes) -> Path:
        path = self.store.root / name
        path.write_bytes(payload)
        lease = self._lease_path(path)
        lease.write_bytes(b"\0")
        return path

    def test_restart_reclaims_all_exact_stale_names_but_preserves_live_and_unknown_root_state(self) -> None:
        hex_a = "a" * 32
        hex_b = "b" * 32
        hex_c = "c" * 32
        hex_d = "d" * 32
        hex_e = "e" * 32
        token = "f" * 32

        stale = {
            self._make_stale(
                f".uv-generation-attempt_{hex_a}-{token}.png",
                b"generation",
            ),
            self._make_stale(
                f".uv-source-upload-src_{hex_b}.{token}.upload",
                b"source",
            ),
            self._make_stale(
                f".uv-webvtt-sub_{hex_c}-{token}.vtt",
                b"webvtt",
            ),
            self._make_stale(
                f".uv-ffconcat-{token}.txt",
                b"ffconcat",
            ),
            self._make_stale(
                f".uv-timeline-assemble-art_{hex_d}-{token}.mp4",
                b"timeline",
            ),
        }

        sidecar_only = self.store.root / f".uv-ffconcat-{hex_e}.txt.lease"
        sidecar_only.write_bytes(b"\0")

        live = acquire_generation_root_staging(
            self.store.root,
            f"attempt_{hex_e}",
            ".mp4",
        )
        live.write_bytes(b"still-writing")
        live_lease = self._lease_path(live)

        preserved = {
            self.store.root / f".uv-generation-attempt_{hex_a}-{token}.png.unleased": b"near-generation",
            self.store.root / f".uv-source-upload-src_{hex_b}.short.upload": b"near-source",
            self.store.root / f".uv-webvtt-art_{hex_c}-{token}.vtt": b"near-webvtt",
            self.store.root / ".uv-ffconcat.txt": b"near-ffconcat",
            self.store.root / f".uv-timeline-assemble-art_nothex-{token}.mp4": b"near-timeline",
            self.store.root / ".uv-recovered-orphan-prj-anything": b"quarantine",
            self.store.root / "ordinary-root-file.bin": b"ordinary",
        }
        for path, payload in preserved.items():
            path.write_bytes(payload)

        # Exact current-format bytes without a lease are intentionally preserved:
        # an older cooperating runtime may still be writing them and cannot prove
        # liveness through the new lease protocol.
        unleased_exact = self.store.root / f".uv-generation-attempt_{hex_b}-{hex_c}.wav"
        unleased_exact.write_bytes(b"legacy-unleased")

        matching_directory = self.store.root / f".uv-generation-attempt_{hex_c}-{hex_d}.png"
        matching_directory.mkdir()
        nested = matching_directory / "must-survive.bin"
        nested.write_bytes(b"directory-content")
        directory_lease = self._lease_path(matching_directory)
        directory_lease.write_bytes(b"\0")

        try:
            recovered = set(recover_stale_root_staging(self.store.root))

            self.assertEqual(recovered, stale)
            for path in stale:
                self.assertFalse(path.exists(), path.name)
                self.assertFalse(self._lease_path(path).exists(), path.name)
            self.assertFalse(sidecar_only.exists())

            self.assertTrue(live.is_file())
            self.assertEqual(live.read_bytes(), b"still-writing")
            self.assertTrue(live_lease.is_file())

            self.assertTrue(unleased_exact.is_file())
            self.assertEqual(unleased_exact.read_bytes(), b"legacy-unleased")
            for path, payload in preserved.items():
                self.assertTrue(path.is_file(), path.name)
                self.assertEqual(path.read_bytes(), payload)
            self.assertTrue(matching_directory.is_dir())
            self.assertTrue(directory_lease.is_file())
            self.assertEqual(nested.read_bytes(), b"directory-content")
            self.store.load_project("prj_root_staging_recovery")
        finally:
            release_root_staging(live)

        self.assertFalse(live.exists())
        self.assertFalse(live_lease.exists())

    def test_mounted_timeline_assemble_holds_leases_for_manifest_and_output(self) -> None:
        project_dir = self.store.project_directory("prj_root_staging_recovery")
        for name in ("a.mp4", "b.mp4"):
            (project_dir / "sources" / name).write_bytes(name.encode("utf-8"))

        observed: dict[str, Path] = {}

        def runner(command, **kwargs):
            manifest = Path(command[command.index("-i") + 1])
            output = Path(command[-1])
            observed["manifest"] = manifest
            observed["output"] = output

            self.assertTrue(manifest.name.startswith(".uv-ffconcat-"), manifest.name)
            self.assertTrue(manifest.name.endswith(".txt"), manifest.name)
            self.assertTrue(self._lease_path(manifest).is_file(), manifest.name)
            self.assertTrue(output.name.startswith(".uv-timeline-assemble-art_"), output.name)
            self.assertTrue(self._lease_path(output).is_file(), output.name)
            self.assertFalse(output.exists(), "producer output path must start nonexistent")

            output.write_bytes(b"joined")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        result = LocalFFmpegAdapter(
            self.store,
            runner=runner,
            tool_paths={"ffmpeg": "fake-ffmpeg", "ffprobe": "fake-ffprobe"},
        ).execute(
            project_id="prj_root_staging_recovery",
            offer=self._timeline_offer(),
            payload={
                "input_paths": ["sources/a.mp4", "sources/b.mp4"],
                "output_path": "artifacts/joined.mp4",
            },
        )

        self.assertEqual(result.output["path"], "artifacts/joined.mp4")
        self.assertTrue((project_dir / "artifacts" / "joined.mp4").is_file())
        for path in observed.values():
            self.assertFalse(path.exists(), path.name)
            self.assertFalse(self._lease_path(path).exists(), path.name)

    def test_allocator_lock_is_established_before_recovery_can_observe_new_lease(self) -> None:
        entered_per_lease_lock = threading.Event()
        release_allocator = threading.Event()
        recovery_started = threading.Event()
        recovery_finished = threading.Event()
        allocated: list[Path] = []
        errors: list[BaseException] = []
        original_try_lock = root_staging_module._try_acquire_os_lock
        delayed_once = False
        delayed_guard = threading.Lock()

        def delayed_try_lock(handle) -> bool:
            nonlocal delayed_once
            is_per_lease = Path(handle.name).name.endswith(".lease")
            if is_per_lease:
                with delayed_guard:
                    should_delay = not delayed_once
                    if should_delay:
                        delayed_once = True
                if should_delay:
                    entered_per_lease_lock.set()
                    if not release_allocator.wait(timeout=5):
                        raise AssertionError("allocator interleaving was not released")
            return original_try_lock(handle)

        def allocate() -> None:
            try:
                with patch.object(
                    root_staging_module,
                    "_try_acquire_os_lock",
                    side_effect=delayed_try_lock,
                ):
                    allocated.append(
                        acquire_generation_root_staging(
                            self.store.root,
                            f"attempt_{'9' * 32}",
                            ".mp4",
                        )
                    )
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        def recover() -> None:
            recovery_started.set()
            try:
                recover_stale_root_staging(self.store.root)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                recovery_finished.set()

        allocator_thread = threading.Thread(target=allocate, name="root-staging-allocator")
        recovery_thread = threading.Thread(target=recover, name="root-staging-recovery")
        allocator_thread.start()
        self.assertTrue(entered_per_lease_lock.wait(timeout=5))
        recovery_thread.start()
        self.assertTrue(recovery_started.wait(timeout=5))

        # Recovery must be serialized behind allocation until the per-staging lease
        # is already locked. On the broken implementation it finishes here, removes
        # the visible-but-unlocked sidecar and leaves the allocator holding an
        # undiscoverable unlinked inode.
        recovered_too_early = recovery_finished.wait(timeout=1)
        release_allocator.set()
        allocator_thread.join(timeout=5)
        recovery_thread.join(timeout=5)

        self.assertFalse(recovered_too_early)
        self.assertFalse(allocator_thread.is_alive())
        self.assertFalse(recovery_thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(allocated), 1)
        path = allocated[0]
        lease_path = self._lease_path(path)
        self.assertTrue(lease_path.is_file())
        try:
            self.assertEqual(recover_stale_root_staging(self.store.root), ())
            self.assertTrue(lease_path.is_file())
        finally:
            release_root_staging(path)
        self.assertFalse(lease_path.exists())

    def test_application_lifespan_reclaims_root_staging_before_project_recovery(self) -> None:
        from uv_studio import server as server_module

        calls: list[tuple[str, object]] = []

        def root_recovery(root: Path) -> tuple[Path, ...]:
            calls.append(("root", root))
            return ()

        def project_recovery(store: ProjectStore) -> tuple[str, ...]:
            calls.append(("project", store))
            return ()

        async def exercise() -> None:
            with (
                patch.object(server_module, "get_project_store", return_value=self.store),
                patch.object(server_module, "recover_stale_root_staging", side_effect=root_recovery),
                patch.object(
                    server_module,
                    "recover_interrupted_generation_jobs",
                    side_effect=project_recovery,
                ),
            ):
                async with server_module.lifespan(server_module.app):
                    pass

        asyncio.run(exercise())
        self.assertEqual(
            calls,
            [
                ("root", self.store.root),
                ("project", self.store),
            ],
        )


if __name__ == "__main__":
    unittest.main()
