# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 2 — Recipe Registry + Production Policy  
**Active branch:** `stage-2/recipe-execution-plan`  
**Main baseline:** `49dcef68ba5e91cdfb87202f66daba5dfe88821c`  
**Branch status:** truthful project execution planning implemented; final CI/PR required before merge.

## Product definition

UV Studio is a universal video production and editing studio with task-specific recipes. Music, narration, story, characters, continuity, lip-sync and automated review are optional. Paid AI APIs are optional capabilities, not hidden baseline dependencies.

## Current architecture

```text
Canonical Project
  -> recipe_id
      -> RecipeDefinition
          -> ProductionPolicy
          -> RecipeExecutionPlan
              -> semantic inputs/runtime capabilities
              -> optional compatibility target
                  -> Stage 3 Capability Registry / adapters
```

Permanent boundaries:

- pinned VideoClaw remains a vendored runtime/compatibility source, not canonical project state;
- Project Store + `.uvproj.zip` are UV Studio-owned;
- top-level `frontend/` is UV Studio-owned derived UI;
- RecipeDefinition is provider-neutral;
- ProductionPolicy describes professional workflow discipline, not vendor choice;
- ExecutionPlan may identify a temporary compatibility adapter but never chooses a paid provider/model;
- future Capability Registry resolves local, direct MCP, native VideoClaw, optional Qwen-MM, optional OpenClaw and other offers as peers;
- native Windows is first-class.

## Merged milestones

- `af24ed11...` — reproducible VideoClaw baseline;
- `8d175c25...` — UV Studio launcher + HTTP smoke;
- `2276a854...` — canonical Project Store v1;
- `21016061...` — UV server + Projects API;
- `9570658d...` — UV-owned frontend + Projects UI;
- `3214cec8...` — portable project archives/backups + Qwen-MM-informed provider-neutral architecture;
- `49dcef68ba5e91cdfb87202f66daba5dfe88821c` — provider-neutral Recipe Registry, ProductionPolicy, recipe API and task selection UI.

## Current Stage 2 slice

### `RecipeExecutionPlan`

Added `uv_studio/recipes/execution.py` with:

- execution schema v1;
- compatibility states `available | partial | unavailable`;
- content input slots;
- runtime capability/config slots;
- optional compatibility target;
- preserved ProductionPolicy;
- forward-compatible unavailable plan for recovered projects whose recipe is not installed.

The planning layer does not launch a task, spend money, create a legacy session or choose a provider/model.

### Truthful native compatibility audit

Inspected the actual pinned VideoClaw launch schemas/routes.

Current conclusions:

- `general_video` → **unavailable**. Native `standard` is narration/topic-led and must not be used as a silent fallback.
- `narrated_video` → **available** via native `standard`; content requires text and runtime requires text/image model capability, with video optional.
- `action_transfer` → **available** via native `action_transfer`; source motion video + target image align with recipe semantics; default instruction may fill the native required prompt when user does not specify one.
- `digital_human` → **partial** only. The pinned native pipeline is product-promo oriented and does not accept the recipe's required supplied speech input. No launch target is exposed for it.

This prevents upstream convenience from distorting UV Studio product semantics.

### API

Added:

```text
GET /api/uv/projects/{project_id}/execution-plan
```

Response includes:

- project/recipe identity;
- compatibility and reason;
- content input slots;
- runtime semantic capability slots;
- ProductionPolicy;
- optional native compatibility target.

Unknown-but-recovered recipe IDs return `unavailable` rather than making user data inaccessible.

### UI

Project page now shows:

- recipe title;
- process readiness (`available`, `partial`, `unavailable`);
- explicit reason;
- required/optional materials;
- semantic runtime requirements;
- archive download/recovery controls.

Legacy production workspace link is shown only when the plan reports an available native compatibility target.

### Tests/docs

Added:

- `tests/test_recipe_execution.py`;
- `tests_api/test_project_execution_api.py`;
- `docs/architecture/RECIPE_EXECUTION.md`.

Tests explicitly prevent:

- general video silently falling back to narrated `standard`;
- digital-human mismatch being reported as full compatibility;
- ProductionPolicy being dropped;
- concrete Qwen/OpenClaw/Wan/Seedance/Kling provider choice leaking into execution planning.

## Verification status

Functional head before context-only commits: `8f99a5a4e65cd9d32dc80493e157d81158ccc8b2`, CI run `31464568264`.

Observed:

- Ubuntu bootstrap/unit: success;
- Windows bootstrap/unit: success;
- Ubuntu API integration: success;
- Ubuntu real HTTP smoke: success;
- Ubuntu frontend production build: success;
- Windows API integration: success;
- Windows real HTTP smoke: success;
- Windows frontend dependency/build steps were still completing when this state file was written.

This context update triggers a newer CI run. Merge requires the actual final branch head to pass the complete Linux/Windows matrix.

## What works now

- durable cross-chat repository memory;
- canonical projects + portable recovery;
- UV-owned backend/frontend;
- provider-neutral Recipe Registry;
- ProductionPolicy;
- recipe catalog/API/task selection;
- honest project execution planning;
- real native compatibility audit without modifying vendor code;
- no paid API introduced by Stages 1–2.

## Not implemented yet

- actual input binding/task launch through UV-owned wrapper;
- Stage 3 semantic Capability Registry;
- direct MCP/Qwen/OpenClaw adapters;
- cost/provider resolution;
- true generic `general_video` executor;
- generic supplied-speech digital-human capability;
- range edit/dubbing/music modes;
- continuity mechanics.

## Current invariants

1. Recipe semantics must not be weakened to match an available upstream pipeline.
2. Recipe definitions never choose provider/runtime.
3. ProductionPolicy survives into execution planning.
4. Paid capabilities remain explicit and optional.
5. Project recovery is independent of installed recipe/runtime availability.
6. Canonical `project_id` is never a legacy VideoClaw session ID.
7. Vendor code stays unchanged unless a documented isolated compatibility patch becomes unavoidable.
8. Native Windows startup cannot depend on WSL-only optional tools.

## Next slice

Begin Stage 3 with metadata-only semantic Capability Registry and adapters/offers. No paid calls in the first Stage 3 slice. See `NEXT_TASK.md`.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work as completed.
