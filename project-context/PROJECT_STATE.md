# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-29

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice in review on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained first-party `actions/*` references in the three repository workflows are pinned to exact full commit SHAs. The selected SHAs are the revisions resolved by the previously used major tags at implementation time, so the hardening does not intentionally upgrade Action behavior.

Read-only `ci.yml` and `editor-foundation-spike.yml` keep `permissions: contents: read` and every checkout step explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` remains the only approved `contents: write` workflow because it contains the actual authenticated Git commit/push path. Its checkout explicitly keeps `persist-credentials: true`, making the write exception visible and reviewable rather than relying on the checkout default.

The permanent guard in `tests/test_actions_workflow_security.py` parses workflows as YAML with PyYAML instead of using a partial handwritten parser. It validates root/job permission mappings and actual job step structures, binds checkout credential policy specifically to `steps[*].with.persist-credentials`, sees block and flow collection forms at every relevant schema boundary, rejects duplicate mapping keys, rejects `write-all`, rejects all unexpected write scopes, and requires every maintained first-party Action to use a full 40-character commit SHA.

GitHub repository identity is case-insensitive, so the guard now case-folds `uses:` values before identifying `actions/*` and `actions/checkout`. Mixed-case first-party references therefore cannot bypass either immutable-SHA validation or checkout credential validation.

PyYAML is kept in the development/test dependency layer rather than the UV Studio core runtime. Bootstrap proves the core import/compile contract first, then installs pinned `PyYAML==6.0.2` immediately before the unit/security suite. Normal development/test setup receives it through `requirements-uv-dev.txt`.

## Semantic review history

Fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..d5f7b5fb4f12e191e12111aff7477b201e275da2` returned `FINDINGS` with one P2 and three rejected candidates.

That first P2 was **CONFIRMED**: the original regex/text guard could fail open on valid YAML, including job-level `permissions: {contents: write}`, and could mistake a `persist-credentials: false` decoy outside checkout `with` for the actual checkout input. The first material fix bound `with.persist-credentials` correctly and added block/flow handling.

A second fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..1003366e526df15242a7938dbd510eb451b5625f` also returned `FINDINGS` with one P2 and three rejected candidates.

That second P2 was also **CONFIRMED**: a complete job encoded as a YAML flow mapping could still hide nested job permissions and checkout steps from the handwritten scanner. The fix therefore removed the partial parser entirely and switched to safe structural YAML parsing. Regression coverage includes whole-job flow mappings carrying hidden `contents: write`, whole-job flow mappings persisting checkout credentials, flow-style first-party Action refs, credential decoys outside `with`, and duplicate YAML keys.

A third fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..8fe443bcee37036d3800973c5c26d9ecdcaef5d0` returned `FINDINGS` with one P2 and five rejected candidates.

That third P2 was **CONFIRMED**: first-party Action and checkout recognition remained case-sensitive even though GitHub repository identity is case-insensitive. A mixed-case `Actions/checkout` or `AcTiOnS/setup-python` reference could therefore bypass the permanent full-SHA and/or credential checks. The fix normalizes `uses:` identity with `casefold()` before classification and adds separate regression tests for a mixed-case floating first-party Action and a mixed-case pinned checkout that tries to persist credentials.

All three prior reviews are stale because material security/acceptance fixes followed them. A fresh ordinary-ChatGPT semantic review is required on the final exact head before merge.

## Verification state

Earlier hosted CI proved that the exact pinned checkout/setup-python/setup-node revisions execute successfully on Ubuntu/Windows and that the product/browser baselines remain viable.

The first PyYAML exact-head bootstrap run also proved that maintained workflows themselves pass the structural guard. Its only unit failure was a regression assertion expecting a narrower error string: the decoy fixture was correctly rejected as `checkout with must be a mapping`. That assertion has been relaxed to match the actual fail-closed rejection.

After the third confirmed P2 fix, the new final exact head must pass all five permanent checks. In particular, both bootstrap jobs must prove core import before PyYAML installation and then pass the complete unit/security suite, and both app-baseline jobs must still produce browser evidence. The fresh semantic review must bind the same final BASE/HEAD. Any further material change invalidates that review again.

## Native Ready connector state

The official connector exposes `mark_pull_request_ready_for_review`, but repeated live invocation failed because the connector queried nonexistent GraphQL field `Repository.fullDatabaseId`. Draft PR #85 was therefore closed unmerged and the same branch was reopened directly as non-draft PR #86. No privileged repository fallback was introduced.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
