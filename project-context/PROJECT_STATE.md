# Project State

<!-- uv-active-slice: stage-5-dubbing-translation -->

**Updated:** 2026-08-13

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 5 dubbing / translation — draft implementation slice

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

Stage 4C is merged through PR #31. UV Studio now has a complete existing-video range-edit workflow through the product UI:

```text
project-owned source import
  -> browser preview + exact integer-microsecond timeline selection
  -> RangeContinuityBrief
  -> ReplacementPlan
  -> ReplacementCandidate
  -> ReplacementReview
  -> AcceptedRangeEdit
  -> explicit authoritative FFmpeg render
  -> deterministic browser-preview projection
```

The editor foundation is reusable rather than range-edit-specific:

- Project Store/domain state is canonical;
- MLT is the editing/timeline engine behind a UV-owned adapter;
- OpenCut Classic remains a selective MIT editor-UX/component donor;
- GUI, scripts, AI and MCP share UV-owned command/workflow contracts;
- provider/model selection remains behind the semantic Capability Registry;
- remote/non-free execution remains behind D-017 authorization;
- authoritative final render/export remains explicit and deterministic.

## Active Stage 5 outcome

Stage 5 adds professional dubbing and translation without invoking a filmmaking workflow or creating another project/timeline model.

The intended user path is:

```text
existing project video / selected range
  -> extract speech/audio evidence
  -> transcript (imported or ASR capability)
  -> optional translation
  -> prepared spoken replacement (recorded/imported or TTS capability)
  -> timing/alignment + subtitle state
  -> synchronization/audio review
  -> explicit accept
  -> non-destructive audio/timeline state
  -> deterministic preview/render/export
```

Baseline engineering rules for this slice:

- local/free speech recognition must be preferred where viable;
- ASR, translation, TTS and optional lip-sync stay provider-neutral capabilities;
- no mandatory Qwen, DashScope, OpenAI or paid media API enters canonical state;
- source and produced media remain project-owned and ID-addressed;
- transcript/translation/alignment state must be typed/versioned and portable;
- AI and UI may request operations but may not mutate project JSON or raw MLT directly;
- recorded/imported speech must be a first-class path, not a fallback hidden behind TTS;
- audio preservation, timing and loudness must have explicit review evidence;
- final browser preview is derived from an accepted/rendered artifact and is not an editing authority.

## Stage 4C reusable evidence retained

PR #31 proved MLT/FFmpeg parity on real encoded media across Ubuntu and Windows and fixed two real MLT integration defects found only by strict timeline comparison. That adapter remains the Stage 5 timeline foundation; dubbing must compose it rather than reopen the editor-engine decision.

## Cross-cutting debt retained outside this slice

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index needs lifecycle/process maintenance;
- broader free-form project JSON fields still need recursive portability hardening outside newly typed boundaries;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.

## Next product slice

After Stage 5 user and engineering exits are proven and merged, continue with `stage-6-sequence-continuity-review` using the same canonical Project Store, capability and review boundaries.
