# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice in review on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained remote Action/reusable-workflow `uses:` references must use immutable full 40-character commit SHAs. The currently used `actions/checkout`, `actions/setup-python`, `actions/setup-node` and `actions/upload-artifact` SHAs are the exact revisions resolved by the previously used major tags at implementation time, so the hardening does not intentionally upgrade Action behavior. Workflow lines retain human-readable `# v4` / `# v5` comments beside the immutable refs.

Every maintained workflow has top-level `permissions: contents: read`. `ci.yml` and `editor-foundation-spike.yml` are fully read-only and every checkout explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` is the only approved writer because it contains the actual authenticated Git commit/push path, but its write authority is narrowed to the single `vendor` job: the workflow remains read-only at top level, that one job declares `contents: write`, and only checkout inside a write-authorized job may use `persist-credentials: true`. Any other checkout, including a future read-only job in the same workflow, must keep credentials disabled.

The permanent guard in `tests/test_actions_workflow_security.py` parses workflows structurally with pinned PyYAML. It checks root/job permission mappings and actual job step structures, binds checkout credential policy specifically to `steps[*].with.persist-credentials`, sees block and flow collection forms, rejects duplicate mapping keys, rejects `write-all` and unexpected write scopes, requires exactly one write-authorized job in the approved vendoring workflow, and requires that writer job to contain authenticated checkout.

GitHub owner/repository identity is case-insensitive, so remote `uses:` values are classified with `casefold()` before policy checks. Mixed-case references cannot bypass immutable-ref or checkout-credential validation. GitHub Runner action input names are also case-insensitive, so checkout `with:` keys are normalized with `casefold()` before credential validation and case-colliding logical duplicates such as `persist-credentials` plus `PERSIST-CREDENTIALS` are rejected fail-closed. Local `./...` actions/workflows remain permitted; remote `owner/repo[/path]@ref` uses require a 40-character SHA; Docker actions are rejected until an explicit immutable Docker-image policy exists.

PyYAML is kept in the development/test dependency layer rather than the UV Studio core runtime. Bootstrap proves the core dependency graph, server import and Python compile contract first, then installs pinned `PyYAML==6.0.2` immediately before the unit/security suite. Normal development/test setup receives it through `requirements-uv-dev.txt`.

## Semantic review history

Fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..d5f7b5fb4f12e191e12111aff7477b201e275da2` returned one P2. It was **CONFIRMED**: regex/text matching could miss valid YAML write authority and could mistake a credential decoy outside checkout `with` for the actual input.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..1003366e526df15242a7938dbd510eb451b5625f` returned one P2. It was **CONFIRMED**: the remaining handwritten parser could miss a complete job encoded as a YAML flow mapping. The parser was replaced with structural PyYAML parsing.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..8fe443bcee37036d3800973c5c26d9ecdcaef5d0` returned one P2. It was **CONFIRMED**: case-sensitive `actions/*` / checkout recognition could be bypassed by mixed-case GitHub repository identity. Action identity is normalized before classification, with regression coverage for both floating refs and persisted checkout credentials.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..2618046496c8a44aa018d745ccdcfacf3af3f28e` returned one P2 and four rejected candidates. It was **CONFIRMED**: PyYAML preserved differently-cased checkout input keys as distinct while GitHub Runner binds action inputs case-insensitively, so a later `PERSIST-CREDENTIALS: true` could override a guarded lowercase `persist-credentials: false`. Checkout input keys are now normalized before validation and case-insensitive logical duplicates are rejected, with regression coverage for the reported bypass.

All four prior reviews are stale because material security/acceptance fixes followed them. A fresh ordinary-ChatGPT semantic review is required on the final exact head before merge.

## Verification state

Hosted CI run #3976 on the fourth reviewed head `2618046496c8a44aa018d745ccdcfacf3af3f28e` passed all five permanent checks on Ubuntu and Windows, including the complete unit/security suite and browser evidence. That proof establishes that the pre-fix workflow definitions themselves were clean; the reported defect was in the permanent drift guard.

Because the fourth P2 required a material guard change, the new exact head must pass all five permanent checks again: `development-context`, Ubuntu/Windows `bootstrap`, and Ubuntu/Windows `app-baseline`, including browser evidence uploads. The required fresh semantic review must bind that same exact BASE/HEAD. Any further material branch change invalidates it.

## Native Ready connector state

The official connector exposes `mark_pull_request_ready_for_review`, but repeated live invocation failed because the connector queried nonexistent GraphQL field `Repository.fullDatabaseId`. Draft PR #85 was therefore closed unmerged and the same branch was reopened directly as non-draft PR #86. No privileged repository fallback was introduced.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
