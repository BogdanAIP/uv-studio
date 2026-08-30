# Project State

<!-- uv-context-state: idle -->
<!-- uv-last-completed: actions-hardening -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` merged through PR #86 as `975a64855a739398139c90a094bdde9435542299`. The repository lifecycle is now `idle`; no product-development slice has started from this merge yet.

The declared handoff remains `project-identity-v2-compat-reader` in `NEXT_TASK.md`. Before that slice starts, the repository-level full-SHA Actions policy should be enabled when the GitHub setting is available, then the mandatory fresh bootstrap must be rerun from the new lifecycle-closed `main`.

## Accepted GitHub Actions security boundary

All maintained direct remote Action `uses:` references are immutable exact commit SHAs. The currently approved execution allowlist contains only the exact pinned `actions/checkout`, `actions/setup-python`, `actions/setup-node` and `actions/upload-artifact` revisions that were already represented by the previous v4/v5 major tags; their pinned `action.yml` metadata was independently checked and each uses the Node runtime rather than a composite Action with nested `uses`.

Every maintained workflow has top-level `permissions: contents: read`. Read-only checkouts explicitly use `persist-credentials: false`. `vendor-videoclaw.yml` is the sole approved writer and narrows `contents: write` to its single `vendor` job, whose authenticated checkout is required for the canonical branch-push path.

The permanent workflow security tests parse YAML structurally with pinned `PyYAML==6.0.2` in the development/test layer only. They fail closed on ambiguous YAML, unexpected write authority, checkout credential drift, case-colliding checkout inputs, floating/malformed Action refs, Docker actions without an immutable policy, repository-local `uses: ./...`, job-level reusable workflows and any new/unreviewed remote Action. The sole write-authorized workflow is compared against its complete reviewed semantic YAML structure instead of relying on handwritten shell interpretation.

Supporting a new local, composite, reusable or third-party Action later requires a deliberate reviewed extension of the transitive execution allowlist rather than silently bypassing this guard.

## Review and verification

Six successive fresh ordinary-ChatGPT reviews found concrete P2 fail-open cases in earlier guard revisions; each was classified **CONFIRMED**, fixed materially and therefore made its prior review stale. The final fresh ordinary-ChatGPT semantic review of exact `66410db447c896fb898636634258402fae1edbff..4cac795b0086f48569a316174230edfca3a8576c` returned `PASS`, `CURRENT`, `reported_findings=0` and `rejected_candidates=9`.

Exact-head CI run #4003 passed all five permanent checks on Ubuntu and Windows, including both browser user-outcome suites and real-media evidence uploads. Duplicate exact-head runs that initially retained the known timing-sensitive Windows browser race were rerun without changing the reviewed SHA; their required Windows `app-baseline` checks subsequently passed as well. The final commit-level check state was green, evidence artifacts were present and bound to the reviewed head, and PR #86 had no unresolved inline review threads before merge.

No UV Studio runtime, product behavior, frontend product composition, canonical Project/Production/Timeline/Generation/Capability authority or migration semantics were changed by this security/process slice.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged by Actions hardening.

## Handoff

After this lifecycle closure merges, enable the repository-level full-SHA Actions policy when available, then start `project-identity-v2-compat-reader` only from the resulting idle `main` after the mandatory fresh bootstrap.
