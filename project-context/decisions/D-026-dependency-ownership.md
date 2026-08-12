# D-026 — UV Studio owns its baseline dependency graph

Status: proposed  
Date: 2026-08-12

## Decision

UV Studio declares and verifies the packages required by its own runtime and tests instead of installing `vendor/videoclaw-app/backend/requirements.txt` as an implicit application baseline.

The dependency boundary is split by responsibility:

```text
requirements-uv.txt
  -> product-owned core runtime

requirements-uv-dev.txt
  -> core + development/test-only transport

requirements-edge-tts.txt
  -> optional exact Edge TTS compatibility runtime

future provider/runtime requirements
  -> explicit optional groups only when an exact adapter needs them
```

The complete vendored VideoClaw dependency list is not renamed into a compatibility requirement group merely to preserve the previous coupling. A compatibility group may be introduced later only for a concrete UV Studio-owned compatibility path whose imports actually require it.

## Context

After D-025 the default server no longer imports or mounts the complete VideoClaw FastAPI application. The remaining UV Studio runtime imports are product-owned FastAPI/Pydantic/MCP/AnyIO/Uvicorn code; exact optional adapters such as Edge TTS load their provider package lazily at execution time.

Before this slice:

- `requirements-uv.txt` declared only MCP;
- `scripts/setup-dev.ps1` installed the complete vendored backend requirements first;
- app-baseline CI did the same, so FastAPI/Uvicorn/Pydantic and provider SDKs were available incidentally;
- the frontend used Next 16.2.3 with `eslint-config-next` 15.2.4;
- frontend lint was not a CI gate;
- the repository backlog recorded high-severity npm advisories without a blocking audit gate.

That state made product independence impossible to prove even after the runtime route boundary had been separated.

## Core Python dependency policy

The baseline declares direct runtime dependencies used by UV Studio-owned code with bounded major versions:

- AnyIO;
- FastAPI;
- MCP v2;
- Pydantic v2;
- Starlette;
- Uvicorn.

`httpx` is development/test-only because it is required by FastAPI/Starlette `TestClient`, not by normal product execution.

Provider/heavy optional packages such as OpenAI SDK, DashScope, Edge TTS, Playwright, Pillow, document processors and provider-specific clients do not belong in the core requirements merely because the pinned VideoClaw snapshot contains them.

## CI proof

The baseline matrix must prove dependency ownership rather than only install the files:

1. bootstrap installs only `requirements-uv.txt`;
2. `pip check` succeeds;
3. `uv_studio.server` imports from that environment;
4. unit tests run without installing the full vendored backend requirements;
5. app-baseline installs only `requirements-uv-dev.txt` before UV API/HTTP tests;
6. the VideoClaw snapshot may still be syntax-compiled/provenance-checked, but it is not imported as the product application runtime.

A regression test guards against reintroducing provider/heavy optional packages or the vendor requirements file into baseline setup/CI.

## Frontend dependency policy

The derived UV Studio frontend owns its own dependency health:

- Next and `eslint-config-next` stay on a mutually compatible line;
- security-fixed package versions are preferred when the current line has a published security patch;
- `npm ci` must use a regenerated committed lockfile rather than a manually edited approximation;
- `npm run lint` is a required application gate;
- `npm audit --audit-level=high` is a required application gate;
- production build remains required.

The package-lock regeneration for this slice may use an isolated subordinate worker branch because the execution environment with npm registry access is GitHub Actions. The coordinator integrates the exact generated blob into the single integration branch; the temporary generator is removed before review.

## Consequences

1. A clean UV Studio development setup no longer installs the complete VideoClaw backend dependency graph.
2. Optional provider capabilities may report unavailable/configuration-required until their explicit extra is installed instead of making server startup depend on those packages.
3. The pinned vendor source remains available for provenance and exact compatibility adapters without controlling the product dependency graph.
4. New providers must introduce an explicit optional requirement group or isolated runtime contract rather than append SDKs to core by default.
5. Frontend security/lint failures become merge-blocking instead of backlog-only observations.

## Acceptance

Change this decision to `accepted` only after the exact final PR head proves on Ubuntu and Windows that:

- UV Studio server imports and unit tests run from core requirements without vendor dependency installation;
- API/HTTP tests run from the product-owned dev requirements;
- `pip check` passes;
- regenerated npm lockfile matches the updated package manifest;
- `npm ci`, frontend lint, high-severity audit and production build all pass;
- existing Project/MCP/capability/range contracts remain green.
