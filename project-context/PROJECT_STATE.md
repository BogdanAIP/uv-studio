# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: actions-hardening -->

**Updated:** 2026-08-30

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`actions-hardening` is the active bounded repository security/process slice in review on branch `chore/actions-hardening`, based on lifecycle-closed `main` `66410db447c896fb898636634258402fae1edbff`.

The slice changes GitHub Actions supply-chain controls only. UV Studio runtime, product behavior, canonical Project/Production/Timeline/Generation/Capability authorities and product migration logic are out of scope.

## Implemented security boundary

All maintained remote Action/reusable-workflow `uses:` references must use immutable full 40-character commit SHAs. The currently used `actions/checkout`, `actions/setup-python`, `actions/setup-node` and `actions/upload-artifact` SHAs are the exact revisions resolved by the previously used major tags at implementation time, so the hardening does not intentionally upgrade Action behavior. Workflow lines retain human-readable `# v4` / `# v5` comments beside the immutable refs.

Every maintained workflow has top-level `permissions: contents: read`. `ci.yml` and `editor-foundation-spike.yml` are fully read-only and every checkout explicitly sets `persist-credentials: false`.

`vendor-videoclaw.yml` is the only approved writer. Its write authority is narrowed to the single `vendor` job: the workflow remains read-only at top level, that job declares `contents: write`, and its authenticated checkout uses `persist-credentials: true` for the real branch push path. Any other checkout, including a future read-only job in the same workflow, must keep credentials disabled.

The sole writer exception no longer depends on a handwritten Bash predicate. The permanent guard parses YAML structurally with pinned PyYAML and compares the complete semantic structure of `vendor-videoclaw.yml` against a reviewed canonical writer-workflow contract. Comments and formatting may change without affecting the contract, but any semantic trigger, permission, job, step, Action, checkout input, shell, condition, environment, command or push-path change makes the guard fail closed until the security contract is deliberately updated and reviewed. This directly prevents `git push --dry-run`, the equivalent `git push -n`, non-executed heredoc text and disabled push steps from satisfying the write exception.

For all maintained workflows the guard checks root/job permission mappings and actual job step structures, binds checkout credential policy specifically to `steps[*].with.persist-credentials`, sees block and flow collection forms, rejects duplicate mapping keys, rejects `write-all` and unexpected write scopes, and validates every remote Action/reusable-workflow reference whenever present. A legitimate read-only workflow that needs no remote Action or checkout remains allowed.

GitHub owner/repository identity is case-insensitive, so remote `uses:` values are classified with `casefold()` before policy checks. Mixed-case references cannot bypass immutable-ref or checkout-credential validation. GitHub Runner action input names are also case-insensitive, so checkout `with:` keys are normalized with `casefold()` before credential validation and case-colliding logical duplicates such as `persist-credentials` plus `PERSIST-CREDENTIALS` are rejected fail-closed. Remote `owner/repo[/path]@ref` uses require a 40-character SHA and Docker actions are rejected until an explicit immutable Docker-image policy exists.

Repository-local `uses: ./...` are now fail-closed rather than implicitly trusted. A companion permanent guard rejects both step-level local Actions and job-level local reusable workflows because their transitive `uses` graph is not yet scanned by this slice. Local Actions/reusable workflows may be introduced later only together with an explicit reviewed transitive immutable-reference policy; until then they are not an allowed escape from the remote-SHA rule.

PyYAML is kept in the development/test dependency layer rather than the UV Studio core runtime. Bootstrap proves the core dependency graph, server import and Python compile contract first, then installs pinned `PyYAML==6.0.2` immediately before the unit/security suite. Normal development/test setup receives it through `requirements-uv-dev.txt`.

## Semantic review history

Fresh ordinary-ChatGPT review of exact `66410db447c896fb898636634258402fae1edbff..d5f7b5fb4f12e191e12111aff7477b201e275da2` returned one P2. It was **CONFIRMED**: regex/text matching could miss valid YAML write authority and could mistake a credential decoy outside checkout `with` for the actual input.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..1003366e526df15242a7938dbd510eb451b5625f` returned one P2. It was **CONFIRMED**: the remaining handwritten parser could miss a complete job encoded as a YAML flow mapping. The parser was replaced with structural PyYAML parsing.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..8fe443bcee37036d3800973c5c26d9ecdcaef5d0` returned one P2. It was **CONFIRMED**: case-sensitive `actions/*` / checkout recognition could be bypassed by mixed-case GitHub repository identity. Action identity is normalized before classification, with regression coverage for both floating refs and persisted checkout credentials.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..2618046496c8a44aa018d745ccdcfacf3af3f28e` returned one P2 and four rejected candidates. It was **CONFIRMED**: PyYAML preserved differently-cased checkout input keys as distinct while GitHub Runner binds action inputs case-insensitively, so a later `PERSIST-CREDENTIALS: true` could override a guarded lowercase `persist-credentials: false`. Checkout input keys are now normalized before validation and case-insensitive logical duplicates are rejected.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..750829da9cdc4039a3761a979313743baeb23535` returned one P2 and seven rejected candidates. It was **CONFIRMED**: the writer-liveness helper still attempted to infer shell execution from text and therefore accepted the short Git dry-run flag `-n` and could count non-executed heredoc content. The shell heuristic has been removed entirely; the complete parsed writer workflow is now frozen against the canonical reviewed structure, with explicit regression coverage for both dry-run forms, heredoc text and a disabled push step.

Fresh review of exact `66410db447c896fb898636634258402fae1edbff..b709de941f7444c6cf71296d54eef0d6bd9f4261` returned one P2 and five rejected candidates. It was **CONFIRMED**: repository-local `uses: ./...` bypassed the remote-ref validator, so a future local composite Action could hide a floating transitive remote Action. Current maintained workflows use no local Actions/reusable workflows. The fix therefore fails closed on all local `uses` until a separate transitive immutable-reference policy is implemented, with regression coverage for both local composite Actions and local reusable workflows.

All six prior review results are stale because material security/acceptance fixes followed them. A fresh ordinary-ChatGPT semantic review is required on the final exact head before merge.

## Verification state

Hosted CI on prior reviewed heads established that the pinned Action revisions execute successfully on Ubuntu and Windows and that the product/browser baselines remain viable. The sixth reported defect was again in the permanent future-drift guard rather than the currently maintained workflows.

The sixth fix adds a repository-level companion guard without changing any maintained workflow: all three current workflow files were rechecked and contain no `uses: ./...`. The new regression suite rejects both a workflow step that calls `./.github/actions/example` and a job that delegates to a local reusable workflow.

Because the sixth P2 required a material acceptance-guard change, the new exact head must pass all five permanent checks again: `development-context`, Ubuntu/Windows `bootstrap`, and Ubuntu/Windows `app-baseline`, including browser evidence uploads. The required fresh semantic review must bind that same exact BASE/HEAD. Any further material branch change invalidates it.

## Native Ready connector state

The official connector exposes `mark_pull_request_ready_for_review`, but repeated live invocation failed because the connector queried nonexistent GraphQL field `Repository.fullDatabaseId`. Draft PR #85 was therefore closed unmerged and the same branch was reopened directly non-draft as PR #86. No privileged repository fallback was introduced.

## Known adjacent implementation risk

The timing-sensitive `ProductionWorkspacePanel` remount race remains separate and unchanged.

## Handoff

After Actions hardening merges and its D-038 lifecycle closure returns `main` to idle, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.
