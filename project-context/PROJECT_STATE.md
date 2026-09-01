# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in `draft` in PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The repaired implementation remains unchanged from material head `a3ad22bf1bcca52ada4f887715e9a3fcf45a98ea`, which passed exact-head CI #4208 5/5. Documentation-only Draft head `c11ca20bbf09dba23fa146d55797cb060736a802` passed CI #4212 and #4213. The later context-only frozen head `f93f7bfe7bf8e56744410ef4f5310e9e4107c919` passed authoritative post-Ready CI #4216 5/5, but a new inline P2 found one inaccurate concurrency sentence in this state document. That finding is **CONFIRMED**: source upload staging is outside the project tree, but `_publish_source_upload` holds the shared project fence across final publication, FFprobe validation, metadata derivation and source registration. PR and lifecycle returned to Draft before correcting the durable context.

No runtime, test or product behavior change is required for this finding.

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

Current implementation evidence remains:

- material repair head `a3ad22bf1bcca52ada4f887715e9a3fcf45a98ea`;
- CI #4208: 5/5 required checks green;
- documentation-only Draft head `c11ca20bbf09dba23fa146d55797cb060736a802`;
- CI #4212: success;
- CI #4213: success;
- previous frozen head `f93f7bfe7bf8e56744410ef4f5310e9e4107c919`;
- authoritative post-Ready CI #4216: 5/5 success before this documentation correction.

The focused deterministic regressions prove that archive export holding the shared fence cannot capture WebVTT or Generation canonical bytes without their registered Project metadata, while a later archive/import preserves the complete published identity/path/bytes. Existing generation recovery, cancellation, idempotency, authorization and Product Truth behavior remain covered by the permanent suite.

## Current repair target

This repair is context-only: keep the source-probe exception explicit and avoid the false blanket claim that all long media work is outside the project fence. After this correction, the exact Draft head must pass the required CI, then the context may freeze `draft -> review` again. The PR must become Ready on that exact frozen head, authoritative post-Ready CI must pass 5/5, all review threads must be resolved, and a new fresh ordinary-ChatGPT semantic review under the BASE `.agents/skills/code-review/SKILL.md` v1.0 policy must report zero surviving findings.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
