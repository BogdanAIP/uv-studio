# UV Studio Recipes and Production Policy

## Purpose

A recipe describes **what kind of video work a project is doing** without deciding which provider, API or runtime will execute every media operation.

This is the boundary that prevents UV Studio from turning into one mandatory film, music-video or micro-drama pipeline.

```text
Project
  -> recipe_id
      -> RecipeDefinition
          -> logical steps
          -> semantic capabilities
          -> ProductionPolicy
```

Concrete execution belongs to the later Capability Registry.

## RecipeDefinition

Recipe schema v1 contains:

- stable `recipe_id`;
- user-facing title/description;
- required and optional input kinds;
- required and optional semantic capability IDs;
- ordered logical steps;
- provider-neutral production policy;
- small progressive-disclosure UI hints.

A project stores only its stable `recipe_id`. Full recipe definitions are not copied into every `project.json`.

## Semantic capabilities

Examples:

```text
video.generate
video.action_transfer
video.digital_human
speech.synthesize
timeline.assemble
media.understand
```

A capability ID states what is needed, not who supplies it.

Stage 3 may resolve the same semantic capability through:

- a local/free tool;
- direct MCP;
- an existing native VideoClaw integration;
- Qwen-MM-Plugins when explicitly configured;
- OpenClaw when useful;
- another provider adapter.

No provider name belongs in the recipe contract.

## ProductionPolicy

Production policy describes how much production discipline a recipe requires.

Each policy item has three states:

```text
off
optional
required
```

Current fields:

```text
source_review
direction_gate
sample_first
plan_gate
scene_ledger
final_review
continuity
```

This intentionally separates **professional workflow quality** from **paid AI execution**.

Examples:

### Simple general video

May use optional creative direction/sample/review, while continuity is off.

### Existing motion transfer

Requires actual source review, one sample before committing to the full operation, and final review.

### Future designed montage from real footage

Can require:

```text
source_review = required
direction_gate = required
plan_gate = required
scene_ledger = optional/required
final_review = required
```

without saying anything about Qwen, DashScope, OpenClaw or another provider.

## Qwen-MM-Plugins influence

Research of Qwen-MM-Plugins showed useful production practices in its `video-edit` skill:

- perceive source material before editing decisions;
- plan direction/taste before timeline assembly;
- audio-first and beat-aware cutting;
- sample-first generation;
- Scene Ledger for multi-scene work;
- mechanical plan/scene/review gates;
- evidence-based review with timestamps/frame references;
- no silent downgrade from an approved production path.

UV Studio models those ideas as provider-neutral policy. The policy does not require Qwen cloud services or `DASHSCOPE_API_KEY`.

See `QWEN_MM_PLUGINS_EVALUATION.md`.

## Built-in recipes in the first Stage 2 slice

### `general_video`

General create-from-brief video. Does not require narration, music, story, continuity or automatic final review.

### `narrated_video`

Narration-led explainer/informational workflow. Temporarily maps to the existing VideoClaw `standard` pipeline for future execution work.

### `action_transfer`

Existing VideoClaw action-transfer use case represented as a UV Studio recipe with required source review/sample/final review policy.

### `digital_human`

Existing talking/digital-human use case represented as a UV Studio recipe with required source review/sample/final review policy.

## Temporary VideoClaw bindings

Compatibility bindings live outside `RecipeDefinition`:

```text
narrated_video -> standard
action_transfer -> action_transfer
digital_human -> digital_human
```

They are migration metadata, not the long-term capability contract.

The large upstream film orchestration remains specialized and is not made the universal default.

## Project creation and recovery

New project creation and recipe changes accept registered recipes only.

Portable project archive import is intentionally different: an archive with a syntactically valid but currently unavailable recipe ID is still recoverable. User data must not become unrestorable merely because a future/optional recipe is not installed in the current build.

Execution/UI can later report that the recipe implementation is unavailable.

## UI rule

The New Project screen asks the user what they want to do and gets its choices from `/api/uv/recipes`.

It must not begin by asking for a provider/model/API key. Provider selection belongs to execution/configuration surfaces after the task is known.
