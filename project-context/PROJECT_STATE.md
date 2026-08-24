# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: product-usability-class-c-cold-start -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Class C cold-start usability evidence is in **Review** on `research/product-usability-class-c-cold-start` as PR #58, based on idle `main` `c0cc0dea46205ac471dd5e7695d069df25216ad7` after recipe/workspace reconciliation PR #56.

This slice tests the product from a user-equivalent clean state. It does not rely on repository knowledge, direct Project Store fixtures, hidden API readiness seeding, retired pipeline routes or developer-only shortcuts.

## Product boundary under test

- discovery begins from the normal UV Studio application entry path `/` and proceeds to `/projects`;
- only recipes currently advertised by the product creation catalog may be selected;
- preserved-only Action Transfer, Digital Human and Performance/lip-sync remain absent from clean-state discovery;
- project creation, prerequisite guidance and workspace routing are exercised through visible controls alone;
- the Class C browser outcome creates Photo-to-Video and Visualizer projects through visible recipe cards and the standard project form;
- both representative paths use visible media controls and deterministic local FFmpeg-backed actions to reach rendered outcomes;
- optional provider/runtime-specific journeys are intentionally not claimed by this evidence;
- compatibility recovery may be observed only through normal user-facing import/recovery behavior, never by direct store writes;
- evidence is written as durable JSON plus a final screenshot for comparison with the later packaged Windows human-acceptance gate.

## Verification status

Draft head `b280ef8f8698831e3f9a72428933f817da12366d` passed all five permanent CI jobs in workflow run `32697091699`, including browser user-outcomes on Ubuntu and Windows. The Windows run also confirms the browser evidence runner now emits Russian unittest diagnostics through explicit UTF-8 rather than the legacy console encoding.

The exact Review head must pass the same five permanent jobs before merge. Review evidence is authoritative only when the PR is non-draft and `ACTIVE_SLICE.json` plus this file both declare `review` on that exact head.

Stage 9 remains blocked until this Class C cold-start slice and installed Windows human acceptance are complete. Missing `main` branch protection remains an external repository-setting P0 and is intentionally deferred from this slice.

## Handoff after this slice

After Class C is merged and lifecycle-closed, the next product-usability gate is `product-usability-installed-windows-human-acceptance` on the packaged application. That gate is intentionally separate from CI-oriented cold-start evidence and must not be claimed by this slice.
