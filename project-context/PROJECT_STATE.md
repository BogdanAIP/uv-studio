# Project State

<!-- uv-active-slice: stage-4-non-destructive-edit-state -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4A — Non-destructive accepted edit state

**Last verified `main` baseline:** `93e0d62824bf72752499a8a3850c434ea7df7e08`

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

UV Studio has a product-owned Project Store, recipe/policy and capability boundaries, D-017 authorization, secure UV-owned application/runtime dependencies, and real cross-platform FFmpeg evidence for exact range extraction and reinsertion.

PR #24 / D-027 proved two separate facts: the current D-021/D-022 FFmpeg mechanics are correct on representative deterministic CFR/VFR/audio/no-audio/timestamp-offset fixtures, while materializing a complete FFV1 output after every accepted short edit is not an acceptable canonical repeated-edit state. The measured compressed-source output was 4.824x the source size on both Ubuntu and Windows.

## Active slice

`stage-4-non-destructive-edit-state` introduces a dedicated typed/versioned project document under `timeline/` rather than storing edit state in free-form `extensions`.

The target state is:

```text
original project media
  + immutable integer-microsecond requested interval
  + accepted project replacement media
  + deterministic ordering/overlap policy
  -> lightweight canonical edit decisions
  -> explicit preview/render/export projection only when media is needed
```

Acceptance itself must not invoke FFmpeg or create a full rendered artifact.

The slice also exposes the state through the UV-owned project API, validates it during archive import, and proves an explicit real-media render projection for multiple non-overlapping edits while preserving D-021/D-022 exactness and rollback expectations.

## Expected following work

If this boundary proves portable and deterministic, the next slice is `stage-4-range-continuity-brief`: bounded provider-neutral context/continuity intelligence attached to exact edit ranges, without provider/runtime identity in canonical state.

## Remaining cross-cutting gaps

- D-023 still needs a post-merge/idle lifecycle state and live diff-vs-write-scope enforcement;
- free-form general project `settings`, `extensions` and reference `metadata` still need proportionate recursive portable-JSON hardening;
- broader device/container/codec real-media coverage remains incremental hardening;
- Stage 4C still owns the complete timeline/preview/accept/export UI.

## Development invariant

Before ending a development slice, the coordinator synchronizes `ACTIVE_SLICE.json`, this file, `NEXT_TASK.md` and the pull request body, then verifies the exact final GitHub head and all required checks.
