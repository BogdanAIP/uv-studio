# Next Task

<!-- uv-next-slice: stage-4-range-edit-user-workflow -->

Updated: 2026-08-12

## Expected handoff

After `stage-4-editor-foundation-spike` selects and proves the reusable editor foundation, continue Stage 4C as `stage-4-range-edit-user-workflow`.

The implementation slice must consume the selected foundation and the product-owned Command API direction rather than writing a parallel custom timeline/editor stack.

## Required user outcome

```text
open/import existing video
  -> preview source in the editor workspace
  -> select the exact requested range on the reusable timeline UX
  -> inspect bounded context / Brief / approved Plan
  -> prepare or select ReplacementCandidate
  -> review candidate in context
  -> accept approved candidate or continue revision
  -> keep edits non-destructive
  -> explicit final render/export
```

Requirements:

- use the foundation selected by D-033 and keep third-party code behind explicit adapters/license boundaries;
- expose meaningful edit mutations through one UV Studio command contract usable by GUI, scripts, AI and MCP;
- do not allow scripts/AI to bypass Project Store path rules, review approval, execution authorization or canonical domain validation;
- add source registration/import and safe browser-preview delivery if the selected foundation does not already solve them within the UV security boundary;
- preserve integer-microsecond range identity even if the UI displays human-readable time/frame positions;
- preserve original media and project-owned non-destructive edit state;
- support deterministic/prepared replacements and optional generated replacements through the existing capability/authorization APIs;
- expose review targets, evidence and `approved` / `rejected` / `needs_revision` states;
- add frontend/unit/accessibility coverage and browser E2E for the permanent 5–10 second targeted-edit scenario;
- do not begin dubbing, music-video mode or desktop packaging in this slice.
