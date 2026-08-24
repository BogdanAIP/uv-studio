from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from uv_studio.desktop_launcher import (
    BACKEND_HOST,
    BACKEND_PORT,
    FRONTEND_HOST,
    FRONTEND_PORT,
    DesktopLauncherError,
    _start_children,
    _start_desktop_host,
    build_child_environment,
    build_launch_plan,
    prepare_packaged_project_store,
    require_desktop_ports_available,
    run_desktop,
)
from uv_studio.projects.maintenance import ProjectMaintenanceError
from uv_studio.release_manifest import (
    ReleaseComponent,
    build_release_manifest,
    write_release_manifest,
)


class DesktopLauncherTests(unittest.TestCase):
    def _release(self, root: Path) -> Path:
        files = {
            "backend/uv-studio-backend.exe": b"backend-exe",
            "frontend/server.js": b"frontend-server",
            "runtime/node/node.exe": b"node-exe",
            "desktop/uv-studio-desktop.exe": b"rust-desktop-exe",
            "runtime/media/bin/ffmpeg.exe": b"ffmpeg-exe",
            "runtime/media/bin/ffprobe.exe": b"ffprobe-exe",
            "runtime/media/bin/melt.exe": b"melt-exe",
        }
        for relative, content in files.items():
            target = root.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        components = (
            ReleaseComponent("backend", "0.1.0-dev", "backend/uv-studio-backend.exe"),
            ReleaseComponent("frontend", "0.1.0-dev", "frontend/server.js"),
            ReleaseComponent("node", "24.19.0", "runtime/node/node.exe"),
            ReleaseComponent("desktop", "0.1.0-dev", "desktop/uv-studio-desktop.exe"),
            ReleaseComponent("ffmpeg", "kdenlive-26.04.3", "runtime/media/bin/ffmpeg.exe"),
            ReleaseComponent("ffprobe", "kdenlive-26.04.3", "runtime/media/bin/ffprobe.exe"),
            ReleaseComponent("mlt", "kdenlive-26.04.3", "runtime/media/bin/melt.exe"),
        )
        manifest = build_release_manifest(
            root,
            product_version="0.1.0-dev",
            build_id="desktop-launcher-test",
            target_arch="x86_64",
            components=components,
        )
        write_release_manifest(manifest, root)
        return root / "backend" / "uv-studio-backend.exe"

    def test_plan_uses_only_manifest_owned_runtime_entrypoints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            self.assertEqual(plan.backend_executable, executable.resolve())
            self.assertEqual(plan.frontend_entrypoint, (root / "frontend" / "server.js").resolve())
            self.assertEqual(plan.node_executable, (root / "runtime" / "node" / "node.exe").resolve())
            self.assertEqual(plan.desktop_executable, (root / "desktop" / "uv-studio-desktop.exe").resolve())
            self.assertEqual(plan.backend_url, f"http://{BACKEND_HOST}:{BACKEND_PORT}")
            self.assertEqual(plan.frontend_url, f"http://{FRONTEND_HOST}:{FRONTEND_PORT}")

    def test_quick_startup_preflight_rejects_size_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            (root / "frontend" / "server.js").write_bytes(b"different-size-payload")
            with self.assertRaisesRegex(DesktopLauncherError, "release preflight"):
                build_launch_plan(root, current_executable=executable)

    def test_launcher_cannot_be_substituted_for_manifest_backend_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            self._release(root)
            other = Path(temporary) / "other.exe"
            other.write_bytes(b"other")
            with self.assertRaisesRegex(DesktopLauncherError, "manifest-owned backend entrypoint"):
                build_launch_plan(root, current_executable=other)

    def test_child_environment_forces_packaged_transport_and_mutable_webview_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            local_app_data = Path(temporary) / "local-app-data"
            environment = build_child_environment(
                plan,
                base_environment={
                    "LOCALAPPDATA": str(local_app_data),
                    "PATH": "attacker-path-must-not-be-used",
                    "WEBVIEW2_USER_DATA_FOLDER": "attacker-value-must-not-win",
                },
            )
            user_data = (local_app_data / "UV Studio").resolve()
            self.assertEqual(environment["UV_STUDIO_RELEASE_ROOT"], str(root.resolve()))
            self.assertEqual(environment["UV_STUDIO_USER_DATA_DIR"], str(user_data))
            self.assertEqual(environment["WEBVIEW2_USER_DATA_FOLDER"], str((user_data / "webview2").resolve()))
            self.assertEqual(environment["HOSTNAME"], FRONTEND_HOST)
            self.assertEqual(environment["PORT"], str(FRONTEND_PORT))
            self.assertEqual(environment["NODE_ENV"], "production")
            self.assertEqual(environment["PATH"], "attacker-path-must-not-be-used")

    def test_child_environment_rejects_mutable_state_inside_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            with self.assertRaisesRegex(DesktopLauncherError, "user data must not overlap"):
                build_child_environment(
                    plan,
                    base_environment={
                        "LOCALAPPDATA": str(Path(temporary) / "local"),
                        "UV_STUDIO_USER_DATA_DIR": str(root / "mutable"),
                    },
                )

    def test_project_store_preflight_uses_packaged_default_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            user_data = (Path(temporary) / "local" / "UV Studio").resolve()
            environment = {"UV_STUDIO_USER_DATA_DIR": str(user_data)}
            with (
                patch("uv_studio.desktop_launcher.ProjectStore") as store_class,
                patch("uv_studio.desktop_launcher.prepare_project_store_for_current_schema") as prepare,
            ):
                prepare_packaged_project_store(plan, environment)
            store_class.assert_called_once_with((user_data / "projects").resolve())
            prepare.assert_called_once_with(
                store_class.return_value,
                (user_data / "recovery" / "migrations").resolve(),
            )

    def test_project_store_preflight_honors_explicit_project_store_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            user_data = (Path(temporary) / "local" / "UV Studio").resolve()
            projects = (Path(temporary) / "external-projects").resolve()
            environment = {
                "UV_STUDIO_USER_DATA_DIR": str(user_data),
                "UV_STUDIO_PROJECTS_DIR": str(projects),
            }
            with (
                patch("uv_studio.desktop_launcher.ProjectStore") as store_class,
                patch("uv_studio.desktop_launcher.prepare_project_store_for_current_schema") as prepare,
            ):
                prepare_packaged_project_store(plan, environment)
            store_class.assert_called_once_with(projects)
            prepare.assert_called_once_with(
                store_class.return_value,
                (user_data / "recovery" / "migrations").resolve(),
            )

    def test_project_store_preflight_failure_aborts_as_launcher_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            environment = {"UV_STUDIO_USER_DATA_DIR": str(Path(temporary) / "data")}
            with patch(
                "uv_studio.desktop_launcher.prepare_project_store_for_current_schema",
                side_effect=ProjectMaintenanceError("synthetic migration failure"),
            ):
                with self.assertRaisesRegex(DesktopLauncherError, "no UV Studio service was started"):
                    prepare_packaged_project_store(plan, environment)

    def test_desktop_prepares_project_store_before_ports_and_children(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            order: list[str] = []
            backend = Mock()
            frontend = Mock()
            desktop = Mock()
            with (
                patch(
                    "uv_studio.desktop_launcher.prepare_packaged_project_store",
                    side_effect=lambda *_args, **_kwargs: order.append("prepare"),
                ),
                patch(
                    "uv_studio.desktop_launcher.require_desktop_ports_available",
                    side_effect=lambda: order.append("ports"),
                ),
                patch(
                    "uv_studio.desktop_launcher._start_children",
                    side_effect=lambda *_args, **_kwargs: (
                        order.append("children") or backend,
                        frontend,
                    ),
                ),
                patch("uv_studio.desktop_launcher._wait_until_ready"),
                patch("uv_studio.desktop_launcher._smoke_diagnostics"),
                patch("uv_studio.desktop_launcher._start_desktop_host", return_value=desktop),
                patch("uv_studio.desktop_launcher._wait_for_desktop_smoke"),
                patch("uv_studio.desktop_launcher._stop_process"),
            ):
                result = run_desktop(
                    release_root=root,
                    current_executable=executable,
                    open_desktop=False,
                    smoke=True,
                    base_environment={"LOCALAPPDATA": str(Path(temporary) / "local")},
                )
            self.assertEqual(result, 0)
            self.assertEqual(order[:3], ["prepare", "ports", "children"])

    def test_required_port_collision_fails_closed(self) -> None:
        with patch("uv_studio.desktop_launcher.port_is_available", side_effect=[False, True]):
            with self.assertRaisesRegex(DesktopLauncherError, str(BACKEND_PORT)):
                require_desktop_ports_available()

    def test_children_are_started_with_exact_argv_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            environment = {
                "UV_STUDIO_RELEASE_ROOT": str(root),
                "UV_STUDIO_USER_DATA_DIR": str(root.parent / "data"),
                "HOSTNAME": FRONTEND_HOST,
                "PORT": str(FRONTEND_PORT),
            }
            backend_process = Mock()
            frontend_process = Mock()
            with patch(
                "uv_studio.desktop_launcher.subprocess.Popen",
                side_effect=[backend_process, frontend_process],
            ) as popen:
                actual_backend, actual_frontend = _start_children(plan, environment)
            self.assertIs(actual_backend, backend_process)
            self.assertIs(actual_frontend, frontend_process)
            backend_call = popen.call_args_list[0]
            frontend_call = popen.call_args_list[1]
            self.assertEqual(backend_call.args[0], [str(plan.backend_executable), "--backend-child"])
            self.assertFalse(backend_call.kwargs["shell"])
            self.assertEqual(
                frontend_call.args[0],
                [str(plan.node_executable), str(plan.frontend_entrypoint)],
            )
            self.assertFalse(frontend_call.kwargs["shell"])

    def test_desktop_host_is_started_from_manifest_with_exact_local_url(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            executable = self._release(root)
            plan = build_launch_plan(root, current_executable=executable)
            environment = {
                "UV_STUDIO_USER_DATA_DIR": str(root.parent / "data"),
                "WEBVIEW2_USER_DATA_FOLDER": str(root.parent / "data" / "webview2"),
            }
            process = Mock()
            with patch("uv_studio.desktop_launcher.subprocess.Popen", return_value=process) as popen:
                actual = _start_desktop_host(plan, environment, smoke=True)
            self.assertIs(actual, process)
            call = popen.call_args
            self.assertEqual(
                call.args[0],
                [str(plan.desktop_executable), "--url", plan.frontend_url, "--smoke"],
            )
            self.assertEqual(call.kwargs["cwd"], str(plan.desktop_executable.parent))
            self.assertEqual(
                call.kwargs["env"]["WEBVIEW2_USER_DATA_FOLDER"],
                environment["WEBVIEW2_USER_DATA_FOLDER"],
            )
            self.assertFalse(call.kwargs["shell"])

    def test_normal_desktop_exit_zero_shuts_down_local_services(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "release"
            root.mkdir()
            executable = self._release(root)
            backend = Mock()
            frontend = Mock()
            desktop = Mock()
            backend.poll.return_value = None
            frontend.poll.return_value = None
            desktop.poll.return_value = 0
            with (
                patch("uv_studio.desktop_launcher.prepare_packaged_project_store"),
                patch("uv_studio.desktop_launcher.require_desktop_ports_available"),
                patch("uv_studio.desktop_launcher._start_children", return_value=(backend, frontend)),
                patch("uv_studio.desktop_launcher._wait_until_ready"),
                patch("uv_studio.desktop_launcher._start_desktop_host", return_value=desktop),
                patch("uv_studio.desktop_launcher._stop_process") as stop,
            ):
                result = run_desktop(
                    release_root=root,
                    current_executable=executable,
                    base_environment={"LOCALAPPDATA": str(Path(temporary) / "local")},
                )
            self.assertEqual(result, 0)
            stop.assert_any_call(desktop)
            stop.assert_any_call(frontend)
            stop.assert_any_call(backend)


class DesktopServerTransportTests(unittest.TestCase):
    def test_server_transport_override_does_not_rewrite_machine_configuration(self) -> None:
        from uv_studio import server

        with patch.object(server, "uvicorn") as uvicorn:
            server.main(host_override=BACKEND_HOST, port_override=BACKEND_PORT)
        self.assertEqual(uvicorn.run.call_args.kwargs["host"], BACKEND_HOST)
        self.assertEqual(uvicorn.run.call_args.kwargs["port"], BACKEND_PORT)


if __name__ == "__main__":
    unittest.main()
