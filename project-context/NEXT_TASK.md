# Next Task

Updated: 2026-08-11

## Primary target

Implement **real native VideoClaw compatibility execution behind the existing Capability Registry**, starting with the already-advertised `native_videoclaw.edge_tts` offer.

Stage 3 now has safe local FFmpeg and exact MCP execution, but the built-in registry still publishes `native_videoclaw.edge_tts` as `AVAILABLE` when `edge_tts` is installed while the execution API has no `native_videoclaw` transport. An `AVAILABLE` offer must not be a dead end.

This slice should close that inconsistency without making the vendored VideoClaw application the product architecture.

## Required implementation

### 1. Product-owned native compatibility adapter

Add a UV Studio-owned adapter outside `vendor/videoclaw-app`.

It must:

- accept only exact known native offer IDs;
- expose no arbitrary Python import/function/command execution surface;
- normalize product-owned semantic input/output;
- use the pinned vendor/runtime only through a narrow compatibility boundary when genuinely required;
- preserve native Windows support;
- fail closed when an optional native dependency is absent.

### 2. Make `native_videoclaw.edge_tts` truthfully executable

The first exact target is:

```text
native_videoclaw.edge_tts -> speech.synthesize
locality = remote
cost     = free
```

Because it contacts a remote service even though it needs no API key, execution must continue to require D-017 `remote_execution` one-shot authorization. It must not require `external_cost`.

Define a small semantic request contract (for example text + explicitly supported voice/output options) rather than forwarding arbitrary Edge TTS arguments.

Write output only into the canonical project (normally `artifacts/`), using deterministic bounded filenames/paths owned by UV Studio.

### 3. Generalize external execution provenance where needed

Current external provenance was introduced for MCP and records MCP profile/tool identity. Native external execution needs the same durable audit guarantees without pretending to be MCP.

Refactor the provenance model carefully so common fields stay common while transport-specific identity is explicit and versioned.

Minimum invariant for native Edge TTS:

- project/capability/offer/adapter;
- portable input digest;
- authorization fact/scopes;
- locality/cost snapshot;
- timestamps/status;
- safe output reference/summary;
- controlled error class/code;
- no token, secret, raw remote error or machine-only path leakage.

Existing MCP provenance/archive tests must remain compatible or have an explicit backward-compatible schema migration.

### 4. Audit other native offers but do not fake readiness

Current model-backed offers (`text_generate`, `image_generate`, `video_generate`, `action_transfer`) are `CONFIGURATION_REQUIRED` because UV Studio has not yet selected exact provider/model/credential contracts.

Do not mark them executable merely because VideoClaw contains provider code.

Instead, document for each native offer what exact configuration/execution contract is still missing. If a small generic native-provider configuration model is clearly justified by the audit, design it in this slice only if it can be tested without real paid credentials; otherwise leave a precise follow-up.

### 5. Execution API routing

Extend the existing project capability `/execute` route so:

- `local_ffmpeg` stays in its threadpool path;
- `mcp.*` stays exact/authorized/provenance-recorded;
- `native_videoclaw` routes only to the new exact native adapter;
- unknown adapters still fail closed;
- selection and D-017 authorization remain transport-independent.

### 6. Tests first, no paid provider calls

Use mocks/fakes around Edge TTS network behavior in unit/API tests. CI must never depend on live Microsoft/Edge endpoints.

Add at least one optional/manual real smoke recipe or developer instruction only if useful, but it must not be part of the required CI gate.

## Acceptance criteria

The slice is complete only when tests prove:

1. `native_videoclaw.edge_tts` cannot execute without `remote_execution` authorization.
2. Correct one-shot authorization permits the exact known native offer.
3. The token cannot be replayed or reused with mutated input.
4. Arbitrary native function/module/command names are not accepted.
5. Semantic Edge TTS input is bounded and validated.
6. Output stays inside the canonical project and cannot escape by path manipulation.
7. Missing optional `edge_tts` fails truthfully before network execution.
8. Mocked success writes a canonical audio artifact and durable non-secret provenance.
9. Mocked remote failure writes controlled failed provenance without raw provider content.
10. Existing MCP provenance and archive history remain valid.
11. Local FFmpeg behavior remains off the async event loop.
12. `local_free_first` still cannot widen to this remote/free offer.
13. Model-backed native offers remain `CONFIGURATION_REQUIRED` until exact provider/model contracts exist.
14. Linux and Windows CI remain green.

## Expected files

Likely changes:

- new `uv_studio/capabilities/adapters/native_videoclaw.py`;
- `uv_studio/api/capability_execution.py`;
- `uv_studio/capabilities/provenance.py` (only for a clean transport-neutral provenance model);
- possibly a small native semantic request/result module;
- native adapter unit tests;
- capability execution API tests;
- archive/provenance regression tests;
- `project-context/PROJECT_STATE.md`;
- this file;
- architecture decision record if provenance/native adapter semantics become durable.

## Explicit non-goals

- No arbitrary vendored function execution bridge.
- No direct user-controlled Python module/class/function names.
- No paid provider call in CI.
- No automatic selection of a paid VideoClaw model.
- No claim that all native VideoClaw model offers are executable.
- No OpenClaw work in the same slice.
- No Stage 4 range-edit workflow work until this Stage 3 advertised-offer inconsistency is closed.
