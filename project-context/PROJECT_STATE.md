# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-usability-class-c-cold-start -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Class C cold-start usability evidence is active in **Draft** on `test/product-usability-class-c-cold-start`, based on idle `main` `c0cc0dea46205ac471dd5e7695d069df25216ad7` after recipe/workspace reconciliation PR #56.

This slice tests the product from a user-equivalent clean state. It must not rely on repository knowledge, direct Project Store fixtures, hidden API readiness seeding, retired pipeline routes or developer-only shortcuts.

## Product boundary under test

- discovery begins from the normal UV Studio application entry path;
- only recipes currently advertised by the product creation catalog may be selected;
- project creation, prerequisite guidance and workspace routing must be understandable through visible controls alone;
- representative supported journeys must reach real outcomes through visible UI interactions;
- optional local runtimes/providers may be absent, but the product must distinguish configuration/runtime requirements from product defects;
- unsupported/preserved-only recipes remain fail-closed and must not reappear as new-project choices;
- compatibility recovery may be observed only through normal user-facing import/recovery behavior, never by direct store writes;
- evidence must be durable and comparable with the later packaged Windows human-acceptance gate.

## Verification status

Implementation and browser evidence are pending. The slice requires exact Draft and Review heads to pass all five permanent CI jobs, including full browser user-outcome coverage on Ubuntu and Windows.

Stage 9 remains blocked until this Class C cold-start slice and installed Windows human acceptance are complete. Missing `main` branch protection remains an external repository-setting P0.

## Handoff after this slice

After Class C is reviewed, merged and lifecycle-closed, the next gate is `product-usability-installed-windows-human-acceptance` on the packaged application. That gate is intentionally separate from CI-oriented cold-start evidence and must not be claimed by this slice.
