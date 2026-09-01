# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen for review in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The repaired implementation remains unchanged from material head `a3ad22bf1bcca52ada4f887715e9a3fcf45a98ea`, which passed exact-head CI #4208 5/5. The later context assertion about project-fence duration was corrected on Draft head `734c83dff65939d5720400ac46de2d602317f2c8`. Exact-head CI #4219 passed all five required checks after re-running only the Windows app-baseline job; its first attempt failed because `Invoke-WebRequest` to `download.kde.org` timed out while provisioning the pinned Kdenlive/FFmpeg/MLT bundle, while the re-run passed API integration, pinned media toolchain, real-media verification, frontend lint/audit/build and browser Product Truth. The related P2 review thread is resolved. No runtime, test or product behavior changed in this documentation repair.

## Implemented boundary

This bounded D-070 slice includes:

- canonical Project schema v2 with schema-v1 project/archive readability;
- explicit legacy recipe compatibility identity rather than fake modern Production Direction identity;
- stable project/source/artifact/media/Timeline identities across migration and archive round trips;
- durable schema-v1 ProjectUnitOfWork undo/redo;
- archive import validation against the raw stored Project schema before migration;
- one shared cross-runtime project fence for recovery snapshots and consequence-bearing media publication;
- exact ZIP-byte hashing from the stream written into the archive;
- fail-closed technical-lock symlink handling while preserving ordinary unregistered portable files;
- proactive source upload staging outside every canonical project directory;
- proactive `timeline.assemble` staging for arbitrary canonical output names;
- proactive WebVTT staging for `artifacts/sub_<uuid>.vtt`;
- proactive named Generation staging for `artifacts/generated_<attempt>.*`, with final artifact/Take/job publication under the shared project fence;
- Production UI/history refresh repair so permanent browser Product Truth tests exercise the immediate visible next-user action without stale-DOM synchronization.

For `timeline.assemble`, WebVTT and named Generation, long render/provider work remains outside the project fence and only final canonical publication plus owning metadata/state enters the fence. Source upload is the explicit exception: request-body streaming and staging remain outside the fence, but `_publish_source_upload` deliberately keeps final move, FFprobe validation, portable metadata derivation and source registration inside the shared project fence so archives cannot observe published source bytes without their validated canonical reference.

## Verification evidence

Earlier review cycles and CI evidence tied to older frozen heads are stale for merge authority after subsequent changes.

Current accepted implementation evidence:

- material repair head `a3ad22bf1bcca52ada4f887715e9a3fcf45a98ea`;
- CI #4208: 5/5 required checks green;
- corrected Draft head `734c83dff65939d5720400ac46de2d602317f2c8`;
- CI #4219: 5/5 required checks green after a single Windows app-baseline infrastructure retry;
- all inline review threads resolved before this freeze.

The focused deterministic regressions prove that archive export holding the shared fence cannot capture WebVTT or Generation canonical bytes without their registered Project metadata, while a later archive/import preserves the complete published identity/path/bytes. Existing generation recovery, cancellation, idempotency, authorization and Product Truth behavior remain covered by the permanent suite.

## Final review gate

Lifecycle is now `review`. The frozen exact head must remain unchanged except for PR metadata operations.

Before merge, PR #89 requires:

1. Ready-for-review state on the exact frozen head;
2. authoritative exact frozen-head CI with all five required checks green;
3. no unresolved review threads;
4. a new fresh ordinary-ChatGPT semantic review under the BASE `.agents/skills/code-review/SKILL.md` v1.0 policy with zero surviving findings;
5. final re-resolution of PR base/head identity immediately before merge.

Any material code, test or behavior change invalidates the review cycle and requires returning lifecycle to `draft`.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
