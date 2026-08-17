"""Frozen Windows entrypoint for the Stage 9 desktop product and backend child."""

from __future__ import annotations

import multiprocessing
import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    multiprocessing.freeze_support()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--backend-child"]:
        from uv_studio.server import main as server_main

        server_main(host_override="127.0.0.1", port_override=8000)
        return 0

    from uv_studio.desktop_launcher import main as desktop_main

    return desktop_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
