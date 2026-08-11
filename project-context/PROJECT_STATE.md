# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 3 — Capability Registry & Adapters  
**Active branch:** `stage-3/local-capability-execution`  
**Main baseline:** `7fb0ca88b8e38a6bc2704e7ead8bfc365fc3fa04`  
**Branch status:** local deterministic capability execution implemented; final branch/PR CI must be green before merge.

## Product definition

UV Studio is a universal video production/editing studio. Task recipes, production policy, semantic capabilities, offer selection and execution are separate layers. Paid AI APIs remain explicit optional capabilities rather than hidden baseline dependencies.

## Current architecture

```text
Canonical Project
  -> RecipeDefinition
      -> ProductionPolicy
      -> RecipeExecutionPlan
          -> semantic capability IDs
              -> CapabilityRegistry
                  -> CapabilityOffer metadata
                      -> SelectionPolicy
                          -> Execution Adapter
```

Permanent rule: **metadata preference is not execution permission**.

## Merged milestones

- `af24ed11...` — reproducible VideoClaw baseline;
- `8d175c25...` — UV Studio launcher + HTTP smoke;
- `2276a854...` — canonical Project Store v1;
- `21016061...` — UV server + Projects API;
- `9570658d...` — UV-owned frontend + Projects UI;
- `3214cec8...` — portable project archives/backups + Qwen-MM-informed architecture;
- `49dcef68...` — provider-neutral Recipe Registry + ProductionPolicy;
- `dff8fc14...` — truthful RecipeExecutionPlan and project readiness UI;
- `7fb0ca88b8e38a6bc2704e7ead8bfc365fc3fa04` — semantic Capability Registry + explicit offer cost/locality/readiness metadata.

## Current Stage 3 slice

### Explicit selection policy

Added:

```text
manual
pinned_offer
local_free_first
```

`local_free_first` selects only:

```text
availability = available
cost_class   = free
locality     = local
```

It never falls through to remote, hybrid, `potentially_paid` or `paid` offers.

`manual` never auto-selects. `pinned_offer` resolves exactly the named available offer, but the current execution API still refuses remote or paid-capable execution because those permission/cost flows do not exist yet.

Decision record: `project-context/decisions/D-014-execution-permission.md`.

### Project-scoped filesystem boundary

`ProjectStore` now exposes safe project-file resolution:

- canonical project-relative paths only;
- no absolute path / `..` traversal;
- Windows backslashes normalize to canonical project paths;
- operation-specific allowed roots;
- no implicit nested directory creation;
- symlink escape is rejected;
- resolved inputs/outputs remain inside the canonical project directory.

### Execution contracts

Added product-owned execution contracts in `uv_studio/capabilities/execution.py`:

- `CapabilityExecutionResult`;
- `CapabilityExecutionEnvelope`;
- normalized input/tool/unsupported errors.

### First executable adapter — local FFmpeg

Added `LocalFFmpegAdapter` with two bounded operations.

#### `media.probe`

- uses local `ffprobe`;
- fixed argv arguments;
- `shell=false`;
- timeout enforced;
- returns structured duration/format/size/audio-video/stream metadata;
- no artifact is created for inspection.

#### `timeline.assemble`

- ordered project-file concat;
- max 200 inputs;
- output only under `artifacts/` or `exports/`;
- existing output is not overwritten;
- temporary concat manifest is stored in project `tasks/` and always removed;
- no arbitrary FFmpeg flags;
- uses stream copy (`-c copy`), so incompatible inputs fail explicitly instead of being silently transcoded;
- output is registered as canonical `ProjectReference` only after FFmpeg succeeds;
- if project metadata registration fails, the newly generated output is removed.

### Project execution API

Added:

```text
POST /api/uv/projects/{project_id}/capabilities/{capability_id}/execute
```

Allowed request fields are exactly:

```text
selection_policy
offer_id
input
```

The current execution boundary permits only `free + local + local_ffmpeg` offers. Known VideoClaw/Qwen/OpenClaw/remote/paid-capable offers are not executable here.

### Tests

Added coverage for:

- `local_free_first` never falling through to paid or remote offers;
- exact pinned offer selection;
- manual selection never auto-running;
- project path traversal rejection;
- Windows path normalization;
- symlink escape rejection;
- no shell execution;
- probe parsing;
- command timeout/failure;
- concat success and artifact registration;
- concat failure leaving no false artifact;
- forbidden output roots;
- pinned paid offer rejected at execution boundary;
- raw command-like API fields rejected.

One unit failure caught an internal `ProjectValidationError` escaping the adapter path-validation boundary. It was corrected so invalid user paths normalize to `InvalidCapabilityInput` / HTTP 422 while the underlying path protection remains strict.

Documentation: `docs/architecture/CAPABILITY_EXECUTION.md`.

## Verification status

Functional code/docs head before context-only commits: `11f1a57b3bdb99dff4e4b43f7cfd7372356995d4`, CI run `31467517961`.

Observed on that head:

- Ubuntu bootstrap/unit: success;
- Ubuntu API integration: success;
- Ubuntu real HTTP smoke: success;
- Ubuntu frontend production build: success;
- Windows bootstrap/unit: success;
- Windows API integration: success;
- Windows real HTTP smoke: success;
- Windows frontend install/build was still completing when this state file was updated.

Context updates create a newer final head. Merge requires the actual final branch/PR head to pass the complete Linux/Windows matrix.

## What works now

- durable project/recovery/UI foundation;
- provider-neutral recipes and production policies;
- truthful execution planning;
- semantic Capability Registry;
- explicit offer readiness/locality/cost metadata;
- strict execution permission policies;
- project-scoped local deterministic execution;
- real FFprobe inspection and bounded FFmpeg concat when tools are installed;
- no paid API required by the execution layer.

## Not implemented yet

- direct MCP client/process adapter;
- optional Qwen-MM runtime adapter;
- OpenClaw runtime adapter;
- remote/provider execution permission and cost confirmation;
- live model/provider selection;
- generic general-video executor;
- range edit/dubbing/music workflows;
- explicit normalization/transcoding capability for incompatible timeline inputs.

## Current invariants

1. Recipe semantics never name provider/runtime.
2. Capability metadata and execution permission remain separate.
3. `local_free_first` is fail-closed and cannot widen to paid/remote.
4. Local capability paths remain inside the canonical project.
5. No arbitrary shell/FFmpeg command surface is exposed.
6. A failed execution does not create a successful artifact record.
7. Remote/paid-capable offers require a future explicit permission flow.
8. Native Windows cannot depend on WSL-only optional adapters.
9. Vendor source remains an immutable compatibility boundary.
10. Qwen-MM/OpenClaw remain optional peer adapters.

## Next slice

Add **direct MCP adapter infrastructure** behind the same semantic capability/execution contracts. Qwen-MM-Plugins should then be connectable as an optional MCP package without becoming a mandatory runtime or changing recipe/project schemas. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
