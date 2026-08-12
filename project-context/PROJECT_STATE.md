# Project State

<!-- uv-active-slice: stage-4-range-edit-user-workflow -->

**Updated:** 2026-08-12

**Repository:** `BogdanAIP/uv-studio`

**Active roadmap stage:** Stage 4C targeted range-edit user workflow — Draft PR #31

Machine-readable slice intent, branch scope, coordination ownership and required checks live only in `ACTIVE_SLICE.json`.

## Product now

The targeted existing-video backend path is complete through Stage 4B:

```text
targeted range intent
  -> RangeContinuityBrief (D-029)
  -> approved ReplacementPlan (D-030)
  -> ReplacementCandidate (D-031)
  -> evidence-based ReplacementReview (D-032)
  -> AcceptedRangeEdit (D-028)
  -> explicit one-pass render/export
```

PR #29 merged the independent review gate and removed caller-controlled direct edit acceptance. Exact range mechanics and the Stage 4B decision chain are covered by real-media tests on Ubuntu and Windows.

## Stage 4C foundation

D-033 is accepted and PR #30 is merged. Stage 4C uses:

```text
OpenCut Classic-derived editor UX
              |
GUI --------- |
Scripts ------+--> UV Studio Command API --> domain validation/transaction --> MLT adapter
AI -----------|                                         |
MCP ----------|                                         +--> derived preview/edit representation
                                                        |
                                                        +--> UV Project Store remains canonical

approved replacement workflow --> D-032 review --> D-028 AcceptedRangeEdit --> UV FFmpeg final render
```

- MLT is the selected editing/timeline engine behind a UV-owned adapter. Linux passed the full 16-capability executable gate and the pinned relocatable Windows runtime passed serialized mutation and real render evidence.
- OpenCut Classic commit `cf5e79e919144200294fb9fed22a222592a0aeea` is the selected MIT editor-UX/component donor.
- UV Project Store/domain state remains canonical.
- GUI, scripts, AI and MCP must use one UV-owned Command API rather than mutating raw MLT/OpenCut state.
- the existing UV FFmpeg one-pass renderer remains authoritative final export until another render path earns parity evidence.

## Active Stage 4C implementation

Draft PR #31 implements the complete normal-user targeted-edit path rather than another backend-only slice.

The first permanent layer is now present on the branch:

- `ProjectSourceMediaStore` allocates server-owned `src_*` identities and `sources/...` paths without accepting host filesystem paths from callers;
- source uploads stream into a hidden temporary project file, hash while writing, atomically move into place, then register only after media inspection succeeds;
- the existing `local_ffmpeg.media_probe` adapter supplies technical media metadata rather than introducing a second FFprobe implementation;
- only portable source metadata is stored; raw probe streams and host paths are not persisted;
- registered source media has ID-based HTTP delivery suitable for browser `<video>` seeking, including byte Range requests;
- failed/empty/non-video uploads are cleaned up rather than leaving half-registered project state;
- API coverage for upload, portable metadata, cleanup, 404s and byte-range delivery passes on both Ubuntu and Windows app-baseline jobs.

The next implementation layer is the UV-owned editor Command API and exact source/range intent binding, followed by the reusable OpenCut-derived editor workspace and the existing Brief -> Plan -> Candidate -> Review -> Accept workflow in that workspace.

## Current verification

The first PR #31 CI run confirmed the new API integration tests pass on Ubuntu and Windows. `development-context` failed only because this file still carried the previous slice marker; the marker is now corrected to `stage-4-range-edit-user-workflow` and exact-head CI must be rechecked after this context commit.

## Remaining Stage 4C user outcome

- shared UV editor Command API and MLT adapter boundary;
- reusable editor workspace/player/timeline using compatible OpenCut Classic primitives rather than a new bespoke editor stack;
- exact timeline range selection mapped to canonical integer microseconds;
- visible Brief/Plan/Candidate/Review state;
- candidate-in-context preview and approve/reject/revise;
- accepted non-destructive edits visible on the timeline, including multiple edits;
- explicit authoritative render/export;
- browser E2E, real-media and preview-vs-render consistency evidence.

## Cross-cutting debt retained outside this slice

- D-023 still needs an explicit merged/idle lifecycle and live PR diff-vs-write-scope enforcement;
- the aggregate decision index needs lifecycle/process maintenance;
- broader free-form project JSON fields still need recursive portability hardening outside the newly typed source-media boundary;
- broader accepted-file/content-addressing integrity remains future hardening;
- the compatibility `/api/stages` catalog should be retired when no UV-owned screen needs it;
- broader codec/device fixtures remain incremental hardening.
