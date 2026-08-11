# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 2 — Recipe Registry + Production Policy  
**Active branch:** `stage-2/recipe-registry`  
**Main baseline:** `3214cec8728fa358520c56a9ce0938617669dc7a`  
**Branch status:** first Stage 2 recipe/catalog/UI slice implemented; final CI/PR required before merge.

## Product definition

UV Studio is a universal video production and editing studio. It uses task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities. Paid AI APIs are optional capabilities, not hidden baseline dependencies.

## Current architecture

- pinned VideoClaw runtime: `HITsz-TMG/VideoClaw@5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- immutable runtime/comparison snapshot: `vendor/videoclaw-app`;
- UV Studio backend entrypoint: `uv_studio.server`;
- canonical project state: file-first Project Store (`project.json` v1);
- portable recovery unit: validated `.uvproj.zip`;
- product frontend: top-level `frontend/`;
- Recipe Registry is product-owned and provider-neutral;
- Production Policy is separate from provider/model choice;
- future Capability Registry resolves semantic capabilities through peer adapters: local tools, direct MCP, native VideoClaw, optional OpenClaw, optional Qwen-MM-Plugins, other providers;
- continuity/review remain optional policies.

## Merged milestones

- `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca` — reproducible VideoClaw baseline;
- `8d175c2535806841c712582532efea403a2f8599` — UV Studio launcher + HTTP smoke boundary;
- `2276a854c4109f0039ae1aeb55304650840e1652` — canonical Project Store v1;
- `21016061be2a2aedd59e7ed7b0424467d82bfd2f` — UV Studio server + Projects API;
- `9570658d18553b5a3cae5a53264376ab00a3ee3a` — UV-owned frontend + Projects UI;
- `3214cec8728fa358520c56a9ce0938617669dc7a` — portable project archives/backups + provider-neutral media architecture after Qwen-MM review.

## Stage 2 implemented on current branch

### Recipe model

Added `uv_studio/recipes/` with schema v1:

- `RecipeDefinition`;
- `RecipeStep`;
- `RecipeUIHints`;
- `ProductionPolicy`;
- `PolicyMode = off | optional | required`;
- strict semantic-ID/duplicate/overlap/step-capability validation;
- deterministic `RecipeRegistry` with explicit duplicate/unknown errors.

Recipes describe the task and semantic capabilities only. They contain no DashScope, Qwen, OpenClaw or VideoClaw provider/runtime selection.

### Production Policy

Provider-neutral fields:

```text
source_review
direction_gate
sample_first
plan_gate
scene_ledger
final_review
continuity
```

This is the first implementation of the professional workflow layer motivated by the Qwen-MM `video-edit` research. It captures production discipline without importing a paid API dependency.

### Initial built-in recipes

1. `general_video`
   - no mandatory narration/music/story/continuity/final automatic review;
   - generic visual plan → shots → video → assembly.

2. `narrated_video`
   - narration-led flow;
   - temporarily maps to VideoClaw `standard` only in separate compatibility metadata.

3. `action_transfer`
   - requires source review, sample-first and final review;
   - temporary compatibility mapping to existing VideoClaw pipeline.

4. `digital_human`
   - talking/performance flow;
   - requires source review, sample-first and final review;
   - temporary compatibility mapping to existing VideoClaw pipeline.

The large upstream film orchestration remains specialized and is not the universal default.

### Recipe API

Added:

```text
GET /api/uv/recipes
GET /api/uv/recipes/{recipe_id}
```

Project create/PATCH now accepts registered recipe IDs only. Portable archive import intentionally still restores projects whose recipe is unavailable in the current build, so user data remains recoverable across future/optional recipe versions.

### Projects UI

New Project creation now loads the recipe catalog from backend and asks **what needs to be done** rather than hard-coding `general_video` or asking for a provider/model first.

Current choices:

- Обычный видеоролик;
- Видео с диктором;
- Перенос движения;
- Говорящий персонаж.

Project cards display the recipe title when available. Archive import remains available.

### Tests/documentation

Added:

- recipe model/registry unit tests;
- recipe catalog API tests;
- project create/update recipe validation tests;
- explicit API test that catalog output contains no Qwen/DashScope/OpenClaw/VideoClaw coupling;
- `docs/architecture/RECIPES.md`.

## Verification status

CI run `31463857712` for head `1c6ded0e2ad401cf5073458ececf3f8afce17d33` showed:

- Ubuntu bootstrap/unit: success;
- Windows bootstrap/unit: success;
- Ubuntu API integration + real HTTP smoke + frontend production build: success;
- Windows API integration + real HTTP smoke: success;
- Windows frontend dependency install/build was still completing when this state file was written.

This state-file commit triggers a newer CI run; merge requires the final actual branch head to pass the complete Linux/Windows matrix.

## What works now

- durable cross-chat development state;
- canonical projects and portable recovery;
- UV Studio-owned backend/frontend;
- provider-neutral recipe catalog;
- provider-neutral production-policy contract;
- backend recipe catalog API;
- registered recipe validation on project create/update;
- task-type selection in New Project UI;
- existing VideoClaw pipelines retained as temporary specialized compatibility targets;
- no paid API added by Stage 2.

## Not implemented yet

- recipe execution planning/binding through UV Studio-owned API;
- recipe-specific workspaces/input collection;
- semantic Capability Registry execution;
- direct MCP/OpenClaw/Qwen adapters;
- cost routing;
- range edit/dubbing/music modes;
- continuity implementation;
- full migration/localization of legacy production screens.

## Current invariants

1. Recipe definitions never choose a provider/runtime.
2. Production Policy describes workflow quality, not vendor selection.
3. No paid provider becomes a hidden prerequisite where an adequate local/free path exists.
4. Archive recovery must not fail merely because a recipe implementation is currently unavailable.
5. Keep canonical `project_id` separate from legacy VideoClaw session IDs.
6. Keep vendor code unchanged unless an explicit isolated compatibility reason exists.
7. Native Windows remains first-class; WSL-only integrations stay optional.
8. The upstream film orchestrator remains specialized rather than becoming UV Studio core.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
