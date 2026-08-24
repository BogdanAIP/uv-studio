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

## Verification status

Class C Draft head `b280ef8f8698831e3f9a72428933f817da12366d` and Review head `068f5f3687a74af9bc27ea5f75fc0941fdab983b` passed all five permanent CI jobs before PR #58 merged as `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

The current acceptance slice is not yet verified. CI/package evidence cannot by itself close this gate: a real installed Windows human run remains mandatory.

Missing `main` branch protection remains an external repository-setting P0 and is intentionally deferred per the current development direction.

## Next authorized slice

After this acceptance gate is complete and lifecycle-closed, start `architecture-hardening-execution-truth` as defined by `project-context/NEXT_TASK.md`.
