# D-025 — UV Studio owns the application security boundary

Status: proposed  
Date: 2026-08-12

## Decision

The default UV Studio server is a UV Studio-owned FastAPI application. The complete vendored VideoClaw FastAPI application is no longer used as the product root and is not mounted as a sub-application by default.

Legacy VideoClaw configuration, sandbox, workflow and provider-backed pipeline routes remain disabled unless a later slice explicitly proves a safe compatibility contract. Remote/non-free execution must enter through the UV Studio product-owned capability preparation/authorization boundary rather than through an independent legacy provider path.

Machine runtime configuration and provider secrets are also UV Studio-owned. Public settings and credentials are stored separately under the machine configuration root; credentials are write-only through the HTTP API and never returned to the browser.

## Context

The repository-wide audit after PR #20 found a mismatch between the strong UV Studio-owned capability boundary and the running application:

- `uv_studio.server` reused `api.app.app` from VideoClaw and appended UV routers afterward;
- the upstream app enabled wildcard CORS while exposing mutating configuration, sandbox, workflow, file and pipeline APIs;
- upstream `/api/config` returned `Config.as_dict()`, including provider credential fields;
- the Settings UI round-tripped that complete configuration;
- VideoClaw saved configuration inside `vendor/videoclaw-app/backend/config.yaml`;
- sandbox/workflow/pipeline routes could create provider clients outside D-017.

Keeping those routes mounted would make product-wide statements such as "remote execution requires explicit authorization" false even though `/api/uv` itself was correct.

## Runtime boundary

The accepted ownership direction is:

```text
UV Studio FastAPI app
  -> UV Studio project/recipe/capability/MCP/configuration routers
  -> narrowly re-exposed read-only/local compatibility endpoints when justified
  -> no provider-backed legacy execution route by default
```

and not:

```text
complete VideoClaw FastAPI app
  + UV Studio routers appended afterward
```

The pinned VideoClaw source remains available to exact product-owned compatibility adapters. This decision does not discard VideoClaw as a donor/compatibility source.

## Configuration and secrets

- public runtime settings live in `data/config/runtime.json` by default;
- provider secrets live separately in `data/config/secrets.json` by default;
- both locations are machine-only and outside portable projects;
- the server host remains loopback-only in this stage;
- CORS uses explicit configured frontend origins and rejects wildcard configuration;
- GET configuration returns public settings + boolean secret-presence state only;
- secret replacement is write-only and does not require the old value;
- explicit `null` clears a secret; an empty string is rejected;
- the transitional vendor `config.yaml` path is defensively ignored by Git;
- no real provider credential is committed or used by regression tests.

## Consequences

1. Existing VideoClaw production UI actions whose backend route is provider-backed may fail closed until migrated behind semantic capabilities/D-017.
2. Read-only compatibility metadata may be re-exposed from UV Studio-owned code when it does not initialize or execute provider workflows.
3. Future provider adapters must read exact machine secrets from the UV Studio configuration boundary rather than revive raw browser-readable config.
4. A future authenticated remote-access feature would require a separate threat model; changing the default server host away from loopback is rejected for now.
5. Dependency ownership remains a separate Stage 3.5 slice; the current app may still import packages installed by the vendored compatibility requirement set until that work is complete.

## Acceptance

Change this decision to `accepted` only after the exact final PR head proves on Ubuntu and Windows that:

- raw secrets do not appear in configuration responses;
- project archives exclude machine secrets;
- untrusted browser origins receive no permissive CORS origin;
- representative legacy provider execution routes are absent from the default route table;
- UV Studio local/free capability execution remains available;
- API, real HTTP smoke and frontend production build remain green.
