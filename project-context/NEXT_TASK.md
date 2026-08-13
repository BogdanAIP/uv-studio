# Next Task

<!-- uv-next-slice: stage-5-dubbing-translation -->

Updated: 2026-08-13

## Expected handoff

After `stage-4-range-edit-user-workflow` / PR #31 merges, continue with Stage 5 dubbing and translation on the reusable editor/media foundation selected by D-033.

Stage 5 must compose the permanent primitives delivered by Stage 4C rather than introducing a second project model, timeline, media importer or automation path.

## Stage 5 starting constraints

- UV Studio Project Store/domain state remains canonical;
- MLT remains the reusable editing/timeline engine behind the UV adapter;
- OpenCut-derived editor UX remains behind UV-owned adapters;
- GUI, scripts, AI and MCP continue to use the same UV Studio Command API;
- source media stays project-owned and ID-addressed rather than exposed by host paths;
- provider/model choice remains behind semantic Capability Registry offers;
- paid/remote execution remains subject to D-017 authorization;
- generated/replacement media that changes accepted source content must preserve the existing review/acceptance boundary where applicable;
- final render/export remains explicit and deterministic;
- browser preview is a deterministic projection of an accepted/rendered artifact, not a parallel editing authority.

## Stage 5 product outcome

Add professional dubbing/translation workflows on top of the Stage 4C editor so a user can select media/ranges, create or import transcript/translation, prepare speech/audio replacements, review synchronization and resulting media, and explicitly accept/render the final result without manual API calls.

Do not begin Stage 5 until PR #31 proves the complete Stage 4C normal-user targeted-edit workflow and merges.
