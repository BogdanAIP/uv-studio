# D-057 — Stage 9 constrained-host and long-project evidence

- **Status:** Proposed
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Stage 9 requires representative weak-hardware and long-project evidence. A fixed RAM/CPU minimum invented from hosted-runner specifications would be misleading: UV Studio's baseline local workflows vary with codec, resolution and duration, while optional AI runtimes have separate capability requirements.

The useful release contract is therefore to expose coarse host capacity without collecting machine identity, and to prove bounded behavior on representative metadata and long-timeline cases rather than declaring arbitrary hardware unsupported.

## Proposed decision

1. Extend secret-safe diagnostics with coarse system resources only:
   - logical CPU count;
   - total physical memory when the OS exposes it;
   - currently available physical memory when the OS exposes it;
   - existing full-check storage free space remains authoritative for writable user data.
2. Do not return hostnames, usernames, process lists, environment dumps, device serials or absolute paths.
3. Do not make low CPU/RAM values a release-integrity error. Resource capacity is support context, not release authenticity.
4. Preserve the dependency-minimal baseline: use Windows `GlobalMemoryStatusEx` and POSIX `sysconf`; do not add `psutil` solely for diagnostics.
5. Add representative bounded evidence:
   - Project Store can load and serialize 4,000 canonical references with a bounded metadata-memory envelope;
   - the real-media suite generates a compact ten-minute CPU-only source and uses the product LocalFFmpegAdapter to seek/extract a range near the end of the timeline;
   - cancellation/timeout evidence from D-056 remains the escape path for work that is too expensive on a constrained host.

## Non-goals

- no universal claim that a particular RAM amount can render every codec/resolution;
- no artificial GPU requirement for baseline FFmpeg/MLT workflows;
- no performance benchmark tied to noisy hosted-runner wall-clock timing;
- no loading media payload bytes into the Project Store merely to prove project scale.

## Acceptance criteria

1. resource snapshot fails soft when an OS probe is unavailable;
2. resource JSON contains no machine identity, paths, environment or process inventory;
3. diagnostics UI can display CPU/RAM alongside existing storage free-space information;
4. 2,000 source + 2,000 artifact references round-trip through Project Store and JSON serialization with peak traced Python allocation below 128 MiB;
5. real-media evidence addresses a range at 598–600 seconds of a generated ten-minute source through the product adapter and registers only expected artifacts;
6. Linux, Windows, shipping Python, frontend/browser and packaged Windows release checks remain green.
