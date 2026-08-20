# Recipe execution planning

## Purpose

`RecipeDefinition` describes the user's task. `RecipeExecutionPlan` describes whether the current UV Studio build has a compatible implementation for that task.

They are intentionally separate.

```text
Project.recipe_id
  -> RecipeDefinition
      -> ProductionPolicy
      -> RecipeExecutionPlan
          -> compatibility target (optional)
          -> content input slots
          -> runtime capability/config slots
```

A recipe must never be distorted just because an existing upstream pipeline happens to be convenient.

## Compatibility states

### `available`

The current compatibility target matches the recipe closely enough to prepare execution.

### `partial`

A related implementation exists but its contract does not fully match the recipe. UV Studio must not silently launch it as though it were equivalent.

### `unavailable`

No truthful implementation exists in the current build. Project data remains valid and recoverable.

## Current native compatibility

### `general_video` → unavailable

The existing VideoClaw `standard` pipeline is narration/topic-led and requires a text/LLM/image generation workflow. Mapping general video to it would reintroduce mandatory narration into the supposedly universal default.

Therefore UV Studio explicitly reports that a true general-video execution path is not implemented yet.

### `narrated_video` → unavailable

The historical VideoClaw `standard` request accepted:

- `text` (topic or narration script);
- `llm_model`;
- `image_model`;
- optional `video_model` and additional rendering/TTS settings.

That historical contract is broadly compatible with `narrated_video`, but its `/api/pipelines/standard/tasks` target is not mounted by the Stage 3.5 UV-owned server. The current build therefore exposes no launch target and reports the recipe unavailable until a current UV-owned workflow exists.

### `action_transfer` → unavailable

The historical VideoClaw request accepted:

- target image path;
- reference motion video path;
- prompt text;
- video model.

UV Studio preserves source video + target reference as required content slots and the provider-neutral `video.action_transfer` capability requirement. The historical `/api/pipelines/action_transfer/tasks` route is not mounted, so the current build exposes no launch target and reports the recipe unavailable.

### `digital_human` → partial

The UV Studio recipe means a general talking character from portrait + supplied speech.

The current VideoClaw `digital_human` pipeline is instead product-promo oriented. It accepts a character image, optional goods/product information, LLM/image/video model IDs and TTS settings; it does **not** accept the recipe's required supplied speech input.

UV Studio therefore marks this binding `partial`, exposes no launch target and does not pretend the workflow is ready.

## Input slots vs runtime config slots

Content/material slots describe user/project inputs:

```text
text
image
video
audio
```

Runtime config slots describe capability choices needed by a compatibility implementation:

```text
llm_model -> text.generate
image_model -> image.generate
video_model -> video.generate
```

Runtime slots expose semantic capability IDs, not a concrete provider/model. Stage 3 will resolve them through the Capability Registry.

## Production Policy continuity

The execution plan carries the recipe's full `ProductionPolicy` unchanged.

This prevents a future execution adapter from dropping requirements such as:

- source review;
- sample-first generation;
- plan gate;
- Scene Ledger;
- final evidence-based review;
- continuity policy.

The present slice does not yet execute those gates; it preserves the contract so later launch/execution code cannot bypass them accidentally.

## Forward-compatible recovered projects

Portable archive import is allowed to restore a project whose `recipe_id` is not installed in the current build.

Execution planning for such a project returns `unavailable` with an explicit reason instead of rejecting the project or losing data.

## Provider boundary

`RecipeExecutionPlan` may identify a temporary compatibility adapter such as `native_videoclaw`, but it does not contain paid provider IDs/API keys.

It must not name Qwen/DashScope/OpenClaw as an implicit requirement. Those become Stage 3 adapter choices only when a semantic capability is resolved.

## API

```text
GET /api/uv/projects/{project_id}/execution-plan
```

The response includes:

- project ID;
- recipe ID/title;
- compatibility state/reason;
- whether native execution can be prepared;
- content input slots;
- runtime capability/config slots;
- Production Policy;
- optional compatibility target.

This endpoint is planning-only: it does not spend money, start generation, create a legacy VideoClaw session or launch a task.
