# Project State

<!-- uv-active-slice: stage-4-non-destructive-edit-state -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4A — Non-destructive accepted edit state

**Last verified `main` baseline:** `93e0d62824bf72752499a8a3850c434ea7df7e08`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio has a product-owned Project Store, recipe/policy and capability boundaries, D-017 authorization, secure UV-owned application/runtime dependencies, real cross-platform FFmpeg evidence for exact range mechanics, and a review-ready non-destructive accepted-edit boundary under D-028.

PR #24 / D-027 proved the D-021/D-022 FFmpeg mechanics are correct on representative deterministic CFR/VFR/audio/no-audio/timestamp-offset fixtures while whole-output FFV1 is unsuitable as canonical repeated-edit state. PR #25 addresses that state-model problem without weakening the proven render path.

## Stage 4A non-destructive state — review-ready

Canonical accepted edit state lives in the typed/versioned project document:

```text
timeline/range-edits.json
```

Each decision contains only:

```text
edit_id
source_path
start_us
end_us
replacement_path
```

The implemented boundary now provides:

- immutable integer-microsecond intervals and project-relative media references;
- deterministic ordering and unique edit IDs;
- fail-closed same-source overlap policy with touching boundaries allowed;
- serialized atomic accept/remove under the Project Store lock;
- storage-only acceptance: no FFmpeg/FFprobe/provider execution and no rendered artifact;
- existing-file validation for a newly accepted decision;
- structural readability/removal after a referenced replacement later disappears, with explicit `validate_project()` for current-reference health;
- UV-owned GET/POST/DELETE project edit-state API;
- portable `.uvproj.zip` export/import/fresh-store reopen preserving typed decisions exactly;
- explicit local/free semantic capability `video.render_edits` using the normal capability selection/execution path;
- one-pass deterministic render of all accepted non-overlapping edits for one source;
- render-time stream/resolution/duration/AV compatibility checks and rollback;
- compositional package-level `LocalFFmpegAdapter` facade rather than further adapter inheritance growth.

## Real-media proof

Draft PR #25 head `dee5f664f31879a048a7a4e7f79679eca2024e02` passed all five required checks in run #623 (`31585401479`).

The real-media suite on Ubuntu and Windows proves:

- two accepted video-only edits create no rendered media until one explicit `video.render_edits` call;
- one render produces the expected `blue → red → blue → green → blue` content order;
- the same multi-edit path with FLAC audio produces exactly one video and one audio stream and the same visual edit order;
- a technically incompatible but existing replacement is accepted without hidden media analysis and then rejected with 422 at explicit render, with no output artifact registered;
- the earlier Stage 4A CFR/VFR/audio/no-audio/timestamp/rollback golden cases remain green.

Unit/API tests additionally prove strict JSON typing, overlap rules, missing-reference rejection, stale-reference repairability and archive round-trip.

D-028 is accepted. The final state-only review head must repeat the same five required checks before merge.

## Expected following work

After PR #25 merges, continue with `stage-4-range-continuity-brief`: bounded provider-neutral continuity/evidence state attached to exact accepted edit decisions, without provider/runtime identity in canonical state.

## Remaining cross-cutting gaps

- D-023 still needs a post-merge/idle lifecycle state and live diff-vs-write-scope enforcement;
- free-form general project `settings`, `extensions` and reference `metadata` still need proportionate recursive portable-JSON hardening;
- semantic pre-commit validation of every future typed project document during archive import remains later archive hardening; typed reopen already fails closed;
- broader device/container/codec real-media coverage remains incremental hardening;
- Stage 4C still owns the complete timeline/preview/accept/export UI.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
