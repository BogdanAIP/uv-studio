#!/usr/bin/env python3
"""Create or verify deterministic SHA256SUMS for final release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReleaseChecksumError(RuntimeError):
    pass


def _require_regular_file(path: Path | str, label: str) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_symlink():
        raise ReleaseChecksumError(f"{label} must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise ReleaseChecksumError(f"{label} is missing: {candidate}") from exc
    if not resolved.is_file():
        raise ReleaseChecksumError(f"{label} must be a regular file: {candidate}")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_basename(name: str) -> None:
    if not name or name in {".", ".."}:
        raise ReleaseChecksumError("artifact basename is invalid")
    if Path(name).name != name or "/" in name or "\\" in name:
        raise ReleaseChecksumError(f"artifact entry must be a basename: {name!r}")
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ReleaseChecksumError(f"artifact basename contains control characters: {name!r}")


def write_checksums(artifacts: Sequence[Path | str], output: Path | str) -> Path:
    if not artifacts:
        raise ReleaseChecksumError("at least one release artifact is required")

    output_path = Path(output).expanduser()
    if output_path.is_symlink():
        raise ReleaseChecksumError("checksum output must not be a symlink")
    if output_path.exists() and not output_path.is_file():
        raise ReleaseChecksumError("checksum output must be a regular file path")

    resolved_output = output_path.resolve(strict=False)
    records: dict[str, Path] = {}
    for raw in artifacts:
        artifact = _require_regular_file(raw, "release artifact")
        if artifact == resolved_output:
            raise ReleaseChecksumError("checksum output cannot also be an input artifact")
        name = artifact.name
        _validate_basename(name)
        folded = name.casefold()
        if folded in records:
            raise ReleaseChecksumError(f"duplicate artifact basename: {name}")
        records[folded] = artifact

    lines = [
        f"{_sha256(records[key])}  {records[key].name}"
        for key in sorted(records, key=lambda item: records[item].name.casefold())
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return output_path.resolve()


def verify_checksums(checksum_file: Path | str) -> list[str]:
    manifest = _require_regular_file(checksum_file, "checksum manifest")
    text = manifest.read_text(encoding="utf-8")
    if not text.endswith("\n"):
        raise ReleaseChecksumError("checksum manifest must end with a newline")

    seen: set[str] = set()
    verified: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise ReleaseChecksumError(f"checksum manifest has blank line {line_number}")
        if len(line) < 67 or line[64:66] != "  ":
            raise ReleaseChecksumError(f"invalid checksum line {line_number}")
        digest = line[:64]
        name = line[66:]
        if not _SHA256_RE.fullmatch(digest):
            raise ReleaseChecksumError(f"invalid SHA-256 on line {line_number}")
        _validate_basename(name)
        folded = name.casefold()
        if folded in seen:
            raise ReleaseChecksumError(f"duplicate checksum entry: {name}")
        seen.add(folded)
        artifact = _require_regular_file(manifest.parent / name, "release artifact")
        actual = _sha256(artifact)
        if actual != digest:
            raise ReleaseChecksumError(
                f"SHA-256 mismatch for {name}: expected {digest}, got {actual}"
            )
        verified.append(name)

    if not verified:
        raise ReleaseChecksumError("checksum manifest is empty")
    return verified


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    write = subparsers.add_parser("write", help="write deterministic SHA256SUMS")
    write.add_argument("--output", type=Path, required=True)
    write.add_argument("artifacts", type=Path, nargs="+")

    verify = subparsers.add_parser("verify", help="verify a SHA256SUMS file")
    verify.add_argument("checksum_file", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "write":
            output = write_checksums(args.artifacts, args.output)
            print(output)
        else:
            for name in verify_checksums(args.checksum_file):
                print(name)
    except (OSError, UnicodeError, ReleaseChecksumError) as exc:
        print(f"release checksum error: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
