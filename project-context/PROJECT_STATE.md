# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-usability-installed-windows-human-acceptance -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Installed Windows human acceptance is in **Draft** on `research/product-usability-installed-windows-human-acceptance`, based on idle `main` `6f656a9a3b3ea885b3280e7dd6a9594daf1dcaf7` after Class C closure.

Class C remains the product-behavior baseline. This slice does not reopen retired product routes or replace Product Orchestrator authority.

## Acceptance boundary under work

- restore only the proven Windows packaging/desktop infrastructure needed to package the current Product Truth;
- do not merge the divergent historical Stage 9 branch wholesale;
- produce a per-user installable Windows build tied to an exact commit;
- run packaged backend/frontend/desktop smoke and current product-owned browser outcomes before human use;
- launch and exercise the installed product through the normal Windows entry point on a real Windows environment;
- distinguish packaging/host failures from optional provider/runtime requirements;
- preserve unsupported Action Transfer, Digital Human and Performance/lip-sync creation as unavailable;
- collect durable evidence that identifies the exact build and Windows environment.

## Human acceptance findings

The first installed Windows candidate exposed inherited Chinese text in Settings and was rejected. A later localized exact build (`f8c7e9a45f7b5d1aa94b62b055712598230b8cfa`, Stage 9 Release #373) was installed and opened successfully enough for the human tester to confirm that Settings were in Russian.

That localized build still failed product acceptance for a more important usability reason:

- a new Story project led directly to visible internal implementation labels such as `Stage 8 · композиционный режим` and `Stage 6`;
- upload controls for images/video/audio looked like required starting inputs even though Story can begin from a text brief and is currently preparation-only;
- the supported end-to-end path from an empty project was not discoverable, so the tester could not determine how to complete a project from scratch;
- Story appeared alongside completed journeys even though its Product Orchestrator state explicitly has no authoritative final Story render/export action;
- Settings exposed provider/model implementation details (provider blocks, LLM/VLM/T2I/I2I/video model selectors, endpoint/proxy controls) instead of the capability-first boundary already present in the backend.

This is a **product-flow acceptance blocker**, not a documentation request. Human acceptance remains pending.

## Draft remediation in progress

The active Draft now changes the routed product UI without inventing unsupported capabilities:

- project creation prefers the supported `general_video` journey, distinguishes finishable journeys from preparation-only/specialized journeys, and opens the new project immediately;
- the project page gives a user-facing route for General Video, Narrated Video, Story and Commercial Product instead of exposing schema/stage/orchestrator terminology first;
- Story is explicitly described as preparation-only and no longer renders Sequence Continuity in its primary route;
- composition upload cards explain whether own media is required or optional and no longer present internal Stage 8 labels;
- Settings reads `/api/uv/capabilities`, explains the safe local/free selection boundary, removes the legacy global model-picker from normal UI, and moves provider credentials/endpoint/proxy controls behind optional/advanced sections;
- browser/static regressions are being updated to assert these user-facing contracts rather than old implementation labels.

A new exact Windows release and a new installed human pass are required after this remediation. Release #373 is evidence for the rejected localized build only and must not be reused as final acceptance evidence for later commits.

## Verification status

Class C Draft head `b280ef8f8698831e3f9a72428933f817da12366d` and Review head `068f5f3687a74af9bc27ea5f75fc0941fdab983b` passed all five permanent CI jobs before PR #58 merged as `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

The current acceptance slice is not yet verified. CI/package evidence cannot by itself close this gate: a real installed Windows human run remains mandatory after the current usability remediation reaches an exact green release head.

Missing `main` branch protection remains an external repository-setting P0 and is intentionally deferred per the current development direction.

## Next authorized slice

After this acceptance gate is complete and lifecycle-closed, start `architecture-hardening-execution-truth` as defined by `project-context/NEXT_TASK.md`.
