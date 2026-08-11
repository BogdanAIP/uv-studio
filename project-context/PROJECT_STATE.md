# Project State

<!-- uv-active-slice: chore-agent-development-workflow -->

**Updated:** 2026-08-11

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4 — Existing Video / Range Edit

**Main baseline:** `f9d850d6fb2ea5fbd84d071752139e151d494ea4`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio is a local-first, provider-neutral video-production foundation built around a canonical portable Project Store, recipe and production policy, semantic capabilities, explicit execution authorization and bounded adapters.

The implemented existing-video path is:

```text
ProjectMediaRange
  -> exact integer-microsecond source interval
  -> bounded context extraction
  -> prepared replacement clip
  -> deterministic exact reinsertion
```

The product does not yet provide the complete user-facing flow from timeline selection through continuity planning, generation/review, preview and final export.

## Stable capabilities on `main`

- canonical project create/read/update with schema validation and atomic persistence;
- portable `.uvproj.zip` export/import, checksums and traversal protection;
- provider-neutral Recipe Registry and Production Policy;
- Capability Registry with fail-closed selection and explicit locality/cost facts;
- D-017 one-shot authorization for remote or non-free execution;
- exact direct-MCP bindings, project-file contracts and portable provenance;
- exact native VideoClaw Edge TTS compatibility path;
- local FFprobe/FFmpeg media probe and bounded timeline assembly;
- `video.extract_range` under D-021;
- `video.replace_range` under D-022;
- Linux/Windows unit, API, real HTTP smoke and frontend build matrix.

Completed slice history is recorded in `PROJECT_HISTORY.md`. Detailed range reinsertion policy is in `docs/architecture/RANGE_REINSERTION.md` and PR #19.

Prioritized product and engineering debt is tracked in `ENGINEERING_BACKLOG.md`; `NEXT_TASK.md` still promotes exactly one implementation target at a time.

## Current process slice

The repository is adding the agent development contract from D-023:

- automatic `AGENTS.md` entrypoint;
- machine-readable active-slice intent;
- sole coordinator ownership of Git/context/PR state;
- disjoint write scopes for parallel agents and read-only reviewers;
- a mandatory PR template;
- CI validation of context, PR body and draft/ready transitions;
- compact project history instead of an ever-growing current-state file.

This slice changes development guardrails only. It does not add product behavior or a media provider.

## Permanent invariants

1. Recipe and project semantics never name provider/runtime implementation IDs.
2. Discovery and offer metadata never equal execution permission.
3. `local_free_first` never widens to remote or paid-capable offers.
4. Remote/non-free execution passes D-017 before invocation.
5. Secrets, raw remote errors and host-only paths never enter portable project state.
6. Existing-video ranges use project-relative paths and integer microseconds.
7. FFmpeg execution remains argv-based, project-bounded and without caller filtergraph/output-path injection.
8. Partial or invalid outputs never become successful project artifacts.
9. Native Windows remains a required CI target.
10. One development slice maps to one branch and PR.
11. Parallel agents have disjoint write ownership; only the coordinator integrates and publishes.

## Known product and engineering gaps

### End-to-end product flow

The current implementation is still more platform than finished product. Missing Stage 4 steps are continuity brief, replacement preparation/generation, independent review, timeline/range UI, preview and explicit final export.

### Real media verification

CI contract-tests FFmpeg command construction but does not yet encode and inspect a real golden VFR + audio fixture on Windows and Linux. This is an explicit quality follow-up, not evidence that the current media path is production-verified.

### Frontend

The product frontend exposes canonical Projects but lacks timeline/range selection, continuity/review screens, preview integration, frontend unit tests and browser E2E coverage.

### Quality gates

The current matrix lacks measured coverage, Python static type/lint gates, frontend lint, browser E2E and real encoded-media assertions.

### Packaging

Development still requires Python, Node/npm and FFmpeg. A distributable Windows application, installer, updater and recovery UX remain Stage 9 work.

## Next product slice

After the process guardrail slice merges, implement the provider-neutral `RangeContinuityBrief` contract described in `NEXT_TASK.md`. The product-owned model must preserve D-021/D-022 facts and exact range identity before any provider-specific generation is added.

## Development invariant

Before ending a development session, the coordinator updates `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the PR body to the same intent, then verifies the exact final GitHub head and required checks.
