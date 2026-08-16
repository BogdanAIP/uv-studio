"""Frozen Windows backend entrypoint for the Stage 9 one-folder release component."""

from __future__ import annotations

import multiprocessing


def main() -> None:
    multiprocessing.freeze_support()
    from uv_studio.server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
