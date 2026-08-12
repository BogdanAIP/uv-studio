# Next Task

<!-- uv-next-slice: stage-4-range-edit-user-workflow -->

Updated: 2026-08-12

## Expected handoff

After `stage-4-editor-foundation-spike` / PR #30 merges, continue Stage 4C as `stage-4-range-edit-user-workflow`.

D-033 has selected the reusable foundation. Do **not** reopen the general editor-engine decision or write a parallel custom timeline stack.

Use:

- MLT as the editing/timeline engine behind a UV Studio adapter;
- OpenCut Classic pinned at `cf5e79e919144200294fb9fed22a222592a0aeea` as a selective MIT editor-UX/component donor;
- UV Studio Project Store/domain state as canonical;
- one UV Studio-owned Command API for GUI, scripts, AI and MCP;
- the existing UV FFmpeg one-pass path as authoritative final accepted-edit render until parity evidence justifies changing it.

## Required user outcome

```text
open/create project
  -> import/register existing source video
  -> preview source in the editor workspace
  -> select exact requested range directly on reusable timeline UX
  -> create/bind the UV edit intent through the Command API
  -> inspect bounded context / Brief / approved Plan
  -> prepare or select ReplacementCandidate
  -> preview candidate in source context
  -> inspect ReplacementReview evidence/verdict
  -> accept approved candidate OR reject/request revision
  -> see accepted non-destructive edit on timeline
  -> repeat for multiple edits
  -> explicit preview/render/export
```

## Implementation requirements

- define the product-owned Command API and MLT adapter boundary before wiring editor interactions directly to engine state;
- GUI, scripts, AI and MCP must call the same meaningful UV commands and receive the same domain validation/transaction semantics;
- do not expose raw MLT XML, raw OpenCut store mutation, host file paths or caller-controlled accepted-edit creation as a privileged automation path;
- add source registration/import into canonical project-owned locations with recursive portability/path hardening appropriate to new media metadata;
- add safe browser media delivery with HTTP Range support suitable for `<video>` seeking; do not expose arbitrary host filesystem paths;
- adapt/reuse OpenCut Classic player/timeline interaction components where they reduce custom editor code, preserving applicable MIT attribution/notice;
- map editor time/frame positions to canonical integer-microsecond UV range identity without making display precision the identity source;
- preserve D-029/D-030/D-031/D-032/D-028 acceptance chain: timeline selection may create intent, but acceptance still requires an approved current review bound to exact candidate bytes;
- preserve original source media and non-destructive project state;
- support deterministic/prepared replacements and optional generated replacements through existing capability/authorization APIs;
- expose review targets, evidence and `approved` / `rejected` / `needs_revision` states in the editor rather than requiring raw API use;
- show accepted edits back on the timeline and support more than one non-overlapping accepted edit;
- keep authoritative final export on the existing UV FFmpeg path for this slice and add consistency evidence so editor/MLT preview does not silently disagree with canonical output;
- add frontend/unit/accessibility coverage plus browser E2E and real-media evidence for the permanent 5–10 second targeted-edit scenario;
- keep donor/engine code behind explicit adapters so future upstream changes do not become canonical project-schema changes;
- do not begin dubbing, music-video mode or desktop packaging in this slice.

## Done means

A normal user can perform the complete targeted existing-video edit from the editor UI without manual API calls, while the same edit operations are also available through the shared command contract for scripts/AI/MCP and all existing security/review invariants remain enforced.
