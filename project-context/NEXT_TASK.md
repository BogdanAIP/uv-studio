# Next Task

**Primary target:** begin Stage 2 with a provider-neutral Recipe Registry and Production Policy model. Do not implement Capability Registry/provider execution in this slice.

## Why this comes next

Stage 1 now provides a canonical durable project, Projects API/UI, and a validated portable `.uvproj.zip` recovery unit. The next architectural boundary is deciding **what kind of work a project is doing** without forcing every project through one film/music/narration pipeline.

Recent Qwen-MM-Plugins research also showed that professional source-review/planning/sample/review discipline should be represented independently from the paid model/provider that performs an operation.

Therefore Stage 2 starts by making recipes and production policies explicit data/contracts before adding more provider integrations.

## Do first

1. Add `uv_studio/recipes/` as product-owned code.
2. Define a strict versioned `RecipeDefinition` model with at least:
   - `recipe_id`;
   - title/description;
   - required and optional input kinds;
   - required and optional semantic capability IDs;
   - ordered logical steps;
   - `production_policy`;
   - small UI metadata/progressive-disclosure hints.
3. Define provider-neutral `ProductionPolicy` switches/levels for:
   - source review;
   - direction/taste planning;
   - sample-first generation;
   - plan gate;
   - scene/take ledger;
   - final evidence-based review;
   - continuity policy reference (disabled by default at this stage).
4. Implement `RecipeRegistry` with deterministic registration, lookup/list, duplicate rejection and schema validation.
5. Add built-in recipes without executing them yet:
   - `general_video` — simple video, no mandatory narration/music/continuity;
   - `narrated_video` — maps conceptually to existing VideoClaw standard/narrated workflow;
   - wrappers/metadata for existing `action_transfer` and `digital_human` capabilities where their current pipeline is usable.
6. Keep existing `project.json.recipe_id` as the stable reference. Do not inflate project schema with copies of full recipe definitions.
7. Add API endpoint to list available recipes and get one recipe definition.
8. Change New Project UI from hard-coded `general_video` to selecting from registry-backed recipes, while preserving progressive disclosure.
9. Add unit/API/frontend build coverage on Windows and Linux.
10. Record mapping from built-in recipes to existing VideoClaw pipelines, but keep the large film orchestrator specialized.

## Production Policy rule

The policy describes **how carefully work is produced**, not **which vendor executes it**.

Example shape:

```text
production_policy:
  source_review: required | optional | off
  direction_gate: required | optional | off
  sample_first: required | optional | off
  plan_gate: required | optional | off
  scene_ledger: required | optional | off
  final_review: required | optional | off
```

Exact enum naming may be refined, but avoid booleans if three-state behavior is useful.

For example:

- mechanical standalone work may have most gates `off`;
- a designed existing-footage montage may require source review + plan + final review;
- a multi-scene professional piece may require Scene Ledger;
- none of these policy choices imply DashScope/Qwen/OpenClaw.

## Qwen-MM boundary

Use `docs/architecture/QWEN_MM_PLUGINS_EVALUATION.md` as design input.

Allowed in Stage 2:

- adapt concepts such as source review, Scene Ledger, sample-first and evidence review;
- write our own small provider-neutral contracts/tests;
- copy specific Apache-2.0 code only if clearly superior and attribution is recorded.

Not allowed in Stage 2:

- requiring `DASHSCOPE_API_KEY`;
- making Qwen-MM-Plugins a runtime prerequisite;
- installing WSL2-only components on the native Windows startup path;
- implementing OpenClaw or direct MCP execution yet.

## Suggested files

```text
uv_studio/recipes/__init__.py
uv_studio/recipes/models.py
uv_studio/recipes/registry.py
uv_studio/recipes/builtin.py
uv_studio/api/recipes.py

tests/test_recipe_registry.py
tests_api/test_recipes_api.py
frontend/lib/recipesApi.ts
```

Likely frontend changes:

```text
frontend/app/projects/page.tsx
```

Keep UI changes small: select a task/recipe and show only minimal description at creation time. Full recipe workspaces belong to later slices.

## Acceptance criteria

- recipe definitions are strict/versioned and provider-neutral;
- duplicate or invalid recipe definitions fail explicitly;
- `general_video` does not require music, narration, story, continuity or automatic review;
- `narrated_video` clearly requires narration-related logical steps but does not become the universal default;
- available recipes are exposed through UV Studio API;
- project creation accepts only known registry recipes (or has an explicitly documented compatibility policy if legacy IDs must temporarily pass);
- New Project UI no longer hard-codes `general_video` as the only choice;
- no paid API/runtime is introduced;
- no files under `vendor/videoclaw-app` are modified;
- tests and frontend build pass on Windows and Linux.

## Explicitly out of scope for this slice

- actual semantic Capability Registry execution;
- Qwen-MM/OpenClaw MCP connections;
- cost routing;
- existing-video range editor;
- dubbing implementation;
- continuity engine;
- Music Video Mode;
- full rebranding/localization of legacy screens.

After this slice, Stage 2 can bind built-in recipes to existing pipelines and add richer recipe-specific UI progressively without changing the Project Store contract.
