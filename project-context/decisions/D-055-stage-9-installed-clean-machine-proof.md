# D-055 — Installed clean-machine runtime independence proof

- **Status:** Proposed
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

D-046, D-047, D-048 and D-049 define the Windows shipping runtime: frozen Python backend, bundled Node standalone frontend and manifest-owned FFmpeg/FFprobe/MLT. D-050/D-053 prove installation, update and rollback, but a hosted Windows runner also contains development Python, Node and media tools. A green desktop smoke on such a host is insufficient evidence that an installed UV Studio does not accidentally fall back to machine tooling.

## Proposed decision

The existing installed A -> B -> A release proof also becomes the clean-machine runtime-independence proof.

After a release is installed and selected, CI temporarily replaces `PATH` with only Windows system directories and clears host runtime search variables (`PYTHONHOME`, `PYTHONPATH`, `NODE_PATH`). Before launching UV Studio the proof asserts that `python.exe`, `node.exe`, `ffmpeg.exe`, `ffprobe.exe` and `melt.exe` are not discoverable through that sanitized `PATH`.

The selected installed frozen launcher must then complete the normal `--desktop-smoke` using its exact release manifest. The environment is restored after the proof even on failure.

This is deliberately performed against the installed immutable sibling rather than the source checkout or staging directory. It therefore covers the same layout and launcher that a clean user machine receives.

## Acceptance criteria

1. the ordinary installed desktop smoke remains green;
2. the sanitized environment cannot resolve host Python/Node/FFmpeg/FFprobe/MLT;
3. installed release A completes desktop smoke under the sanitized environment;
4. update release B completes the same clean-machine smoke after A -> B;
5. rollback-selected A completes the same clean-machine smoke after B -> A;
6. D-044 deep verification, installer activation and D-045 user-data preservation remain unchanged;
7. the exact-head Stage 9 Windows Release workflow is green.

## Boundary

This proof establishes runtime independence from preinstalled language/media tooling. It does not claim that Windows system DLLs, networking, graphics drivers or optional external integrations are absent; those remain operating-system or optional-capability dependencies and are diagnosed separately.
