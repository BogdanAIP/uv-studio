# D-049 — One frozen executable owns desktop launch and backend-child supervision

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The Stage 9 Windows payload already contains one proven PyInstaller one-folder backend component, the standalone Next frontend, a pinned Node executable and manifest-owned FFmpeg/FFprobe/MLT. A desktop product still needs a user-facing launcher that can validate the installed payload, start the local services, wait for readiness, open the UI and stop the peer process when either side fails.

Building a second frozen Python launcher would duplicate the Python runtime and create a second packaging/provenance surface. Depending on PowerShell, a batch file or a system Python launcher would violate the no-manual-toolchain product contract.

## Decision

The existing manifest-owned frozen backend executable has two roles selected before application startup:

- normal invocation is the UV Studio desktop launcher/supervisor;
- the private `--backend-child` invocation starts only the FastAPI backend child.

The launcher starts the backend child by invoking that exact same manifest-owned executable and starts the frontend with the exact manifest-owned Node executable plus the manifest-owned standalone `server.js`. It never resolves Python, Node or media tools through system `PATH`, and child processes are always started with argument arrays and `shell=False`.

The packaged desktop transport is product-internal and fixed for the current standalone frontend contract:

- backend: `127.0.0.1:8000`;
- frontend: `127.0.0.1:3000`.

The backend-child mode passes these loopback transport overrides directly to the server startup function without rewriting the persisted machine runtime configuration. Direct/development server invocation continues to use the normal runtime configuration. This keeps the packaged Next rewrite and backend endpoint coherent even if direct-server configuration has a different port.

Before child startup the launcher:

1. infers the release root from its own frozen executable location rather than trusting an inherited release-root environment variable;
2. requires that its own executable exactly equals the manifest `backend` entrypoint;
3. performs the D-044 quick structural/inventory/size verification;
4. resolves backend/frontend/Node only from manifest component entrypoints;
5. derives packaged mutable state under `%LOCALAPPDATA%/UV Studio` unless an existing D-045 override is supplied, and rejects overlap with the immutable payload;
6. fails closed when required loopback ports are already occupied.

The launcher then starts both children, waits for backend health and frontend HTTP readiness, and opens the default browser only after both are ready. If one child exits unexpectedly, startup times out, or the launcher is interrupted, it shuts down the peer process; Windows process groups are used so a graceful CTRL_BREAK can be attempted before forced termination.

A hidden `--desktop-smoke` mode exercises the real packaged supervisor without opening a browser, requests secret-safe diagnostics through the packaged frontend, requires frozen packaged mode and deep release verification, then shuts both children down cleanly. It exists for release/clean-machine automation, not as a second user workflow.

## Integrity policy

D-044 remains authoritative: normal launcher startup uses the quick check for responsiveness. Installer verification, support diagnostics, update/recovery and release CI use deep SHA-256 verification. The launcher does not redefine the release manifest or introduce another payload identity.

## Consequences

- Stage 9 keeps a single frozen Python runtime instead of duplicating it for a separate launcher.
- The installer can create the UV Studio shortcut directly to the manifest-owned backend executable; no system scripting runtime is required.
- A second launch fails with an actionable local-port collision instead of terminating or attaching to an unknown process.
- Browser-based Next remains the current desktop UI surface; installer/window/tray polish may evolve without changing the canonical Project Store or release-manifest boundary.
- Packaged launcher regressions must prove exact manifest resolution, no-shell child execution, port collision failure, mutable-data separation, packaged diagnostics and child cleanup.
