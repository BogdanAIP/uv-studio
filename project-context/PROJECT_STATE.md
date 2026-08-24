# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: product-usability-class-c-cold-start -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository context is **idle** after Class C cold-start usability PR #58 merged as `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

Class C now proves the supported product from a user-equivalent clean state without repository knowledge, direct Project Store fixtures, hidden API readiness seeding, retired pipeline routes or developer-only shortcuts.

## Completed Class C boundary

- discovery begins from the normal UV Studio application entry path `/` and proceeds to `/projects`;
- only recipes advertised by the product creation catalog are selected;
- preserved-only Action Transfer, Digital Human and Performance/lip-sync remain absent from clean-state discovery;
- project creation, prerequisite guidance and workspace routing are exercised through visible controls alone;
- Photo-to-Video and Visualizer projects are created through visible recipe cards and the standard project form;
- both representative paths use visible media controls and deterministic local FFmpeg-backed actions to reach rendered outcomes;
- optional provider/runtime-specific journeys are not falsely claimed by this evidence;
- the browser evidence runner emits UTF-8 diagnostics portably on Ubuntu and Windows.

## Verification status

Draft head `b280ef8f8698831e3f9a72428933f817da12366d` passed all five permanent CI jobs in workflow run `32697091699`.

Review head `068f5f3687a74af9bc27ea5f75fc0941fdab983b` passed all five permanent CI jobs in workflow run `32697793227`, including browser user-outcome coverage on Ubuntu and Windows, and PR #58 merged without review threads as `9d3f9f04800e7cc3a1e280038a15b0efc53f3ca4`.

Stage 9 remains blocked until installed Windows human acceptance is complete. Missing `main` branch protection remains an external repository-setting P0 and is intentionally deferred per the current development direction.

## Next authorized slice

`product-usability-installed-windows-human-acceptance`, defined by `project-context/NEXT_TASK.md`.

That gate must test the packaged application on Windows and must not be substituted with CI browser evidence. Architecture hardening can be prepared in parallel only after preserving this P0 gate as explicit durable context.
