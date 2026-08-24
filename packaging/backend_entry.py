"""Frozen Windows entrypoint for the Stage 9 desktop product and private release modes."""

from __future__ import annotations

import ctypes
import multiprocessing
import os
import sys
from typing import Sequence


def _hide_desktop_supervisor_console(arguments: Sequence[str]) -> None:
    """Hide only the user-facing frozen supervisor console on Windows.

    Private machine-facing modes intentionally keep their console/stdout behavior
    for installer and CI diagnostics. Normal desktop startup has no arguments and
    immediately hands visible UI ownership to the Rust/WebView2 host.
    """

    if arguments or os.name != "nt" or not getattr(sys, "frozen", False):
        return
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_console_window = kernel32.GetConsoleWindow
        get_console_window.restype = ctypes.c_void_p
        hwnd = get_console_window()
        if hwnd:
            user32.ShowWindow(ctypes.c_void_p(hwnd), 0)  # SW_HIDE
    except (AttributeError, OSError):
        # The installed shortcuts also request SW_HIDE. Failing to hide an
        # already-created console must never block UV Studio startup.
        return


def main(argv: Sequence[str] | None = None) -> int:
    multiprocessing.freeze_support()
    arguments = list(sys.argv[1:] if argv is None else argv)
    _hide_desktop_supervisor_console(arguments)

    if arguments == ["--backend-child"]:
        from uv_studio.server import main as server_main

        server_main(host_override="127.0.0.1", port_override=8000)
        return 0

    if arguments == ["--verify-release"]:
        from uv_studio.installed_release import (
            InstalledReleaseVerificationError,
            verify_installed_release,
        )

        try:
            result = verify_installed_release()
        except InstalledReleaseVerificationError as exc:
            # This is a private machine-facing mode used by the installer. Keep the
            # message deliberately sanitized in InstalledReleaseVerificationError
            # and emit it on stdout so NSIS can capture it without invoking a shell.
            print(f"UV Studio release verification failed: {exc}")
            return 2
        print(
            "UV Studio release verification passed: "
            f"files={result.get('verified_files', 0)}"
        )
        return 0

    from uv_studio.desktop_launcher import main as desktop_main

    return desktop_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
