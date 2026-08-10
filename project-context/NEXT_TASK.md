# Next Task

**Primary target:** finish Stage 0 by creating the first UV Studio-owned startup/smoke layer above the vendored VideoClaw baseline.

## Do first

1. Add a top-level development setup/run path so contributors do not work from inside `vendor/videoclaw-app` manually.
2. Start the imported FastAPI server in CI and probe its `/api/health` endpoint over HTTP.
3. Add a minimal UV Studio wrapper/config boundary that locates the vendored backend/frontend without modifying upstream business logic.
4. Document Windows developer startup from repository root.
5. Keep the vendored subtree behavior unchanged in this slice.

## Expected files

Likely:

- `scripts/setup-dev.ps1`
- `scripts/run-backend.ps1`
- `scripts/run-frontend.ps1`
- Linux equivalents or cross-platform Python launch helpers where useful;
- `docs/DEVELOPMENT.md`
- CI smoke-test updates;
- small UV Studio-owned bootstrap/config module outside `vendor/` if needed.

## Acceptance criteria

- a developer can start backend/frontend from repository root without knowing upstream internal paths;
- backend health endpoint is exercised over real HTTP in CI;
- Linux and Windows CI remain green;
- no provider/API credentials are needed for startup smoke tests;
- no feature logic is added to the vendored film orchestrator;
- vendored upstream provenance remains untouched;
- `PROJECT_STATE.md` is updated to the verified state.

## Explicitly out of scope for this slice

- Stage 1 Project Store;
- Recipe Registry;
- OpenClaw integration;
- music-video functionality;
- dubbing;
- range editing;
- UI redesign/rebranding beyond what is needed for startup boundaries;
- provider refactoring.

Complete the baseline/startup boundary first. Stage 1 begins only after the application can be launched and smoke-tested as UV Studio from repository root.