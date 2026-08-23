# Project State

<!-- uv-context-state: idle -->

**Updated:** 2026-08-23

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Repository context is **idle** after recipe/workspace reconciliation PR #56 merged as `44c853f00766795399de9addf74ba79cef2c35c4`.

Product Truth recovery now has one explicit boundary between durable recipe compatibility metadata and recipes that UV Studio can truthfully advertise for new project creation.

## Completed Product Truth reconciliation

- the provider-neutral Recipe Registry remains the durable vocabulary for current and preserved/imported projects;
- the creation catalog advertises only recipes with a current authoritative Product Orchestrator journey;
- Action Transfer, Digital Human and Performance/lip-sync remain readable compatibility recipes but are not offered for new creation or recipe switching;
- archive import/recovery remains permissive so preserved unsupported projects can still be opened and exported;
- visible project workspaces are mounted only from `workflow.relevant_workspaces`;
- the historical generic ProjectEditor + Sequence Continuity + Dubbing fallback is removed;
- the direct `performance_lip_sync` page bypass is removed until that workflow is separately recovered;
- `free_project` remains owned by Targeted Edit rather than becoming a second generic editor authority;
- preserved unsupported projects fail closed with partial readiness, no next actions and no foreign workspaces.

## Verification status

Recipe/workspace reconciliation exact Draft head `e49b64aef97011d7a7ebffae8f6db0b21f7ab506` passed all five permanent checks in CI run `32660321870` (#2667), including full browser user-outcome coverage on Ubuntu and Windows. The same head was reviewed for merge with no review threads or outstanding code changes, and PR #56 merged as `44c853f00766795399de9addf74ba79cef2c35c4`.

The browser evidence proves both sides of the product boundary: preserved-only recipes are absent from new-project discovery, while a preserved Action Transfer project remains readable without inheriting Targeted Edit, Sequence Continuity, Dubbing or Performance panels.

Stage 9 remains blocked until Class C cold-start evidence and installed Windows human acceptance are complete. Missing `main` branch protection remains an external repository-setting P0.

## Next authorized slice

`product-usability-class-c-cold-start`, defined by `project-context/NEXT_TASK.md`.

The next slice must start from a clean user-equivalent state, use only advertised recipes and visible product controls, distinguish genuine product defects from optional runtime/provider absence, and produce durable browser evidence without direct Project Store fixtures, hidden API readiness seeding or developer-only shortcuts.
