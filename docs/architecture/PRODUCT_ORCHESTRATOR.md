# Product Orchestrator foundation

## Purpose

Product Orchestrator is the product-facing projection between user intent and the
existing UV Studio domain/capability architecture. It explains what the project
can do now, what is missing and which semantic action should happen next.

It is not a second workflow database and it is not a generic execution engine.
Project Store remains canonical, domain modules retain their own durable state,
Capability Registry owns runtime offers, and the D-017 execution boundary owns
selection, consent and adapter dispatch.

## First supported journey

```text
Photo -> Video intent
  -> GET ProjectWorkflowState
  -> readiness + structured prerequisites
  -> relevant workspace: photo_composition
  -> action: compose_photos
  -> POST workflow/actions/compose_photos
  -> existing video.compose_photos execution boundary
  -> local_ffmpeg offer
  -> Project Store video artifact
  -> refreshed current_outcome/recent_artifacts projection
```

The action accepts only registered source IDs, an optional registered audio ID
and a bounded per-image duration. It cannot pass filesystem paths or arbitrary
FFmpeg arguments.

## HTTP contract

```text
GET  /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

`ProjectWorkflowState` schema version 1 contains:

- project/recipe identity and truthful `readiness`;
- a user-facing summary;
- structured prerequisites and their resolution hints;
- relevant workspaces only;
- stable next-action IDs with bounded input schemas and execution metadata;
- current/recent result artifacts;
- separate jobs, decisions and diagnostics collections.

Recipes not migrated to Product Orchestrator fail closed as `partial` with no
advertised action or workspace. Unknown imported recipe IDs remain recoverable
but project as `unavailable` with a `recipe_unknown` diagnostic.

## Ownership boundary

| Concern | Owner |
|---|---|
| project identity, sources, artifacts | Project Store |
| recipe intent/policy | Recipe Registry |
| runtime availability | Capability Registry |
| readiness/prerequisites/relevant workspace/next action | Product Orchestrator |
| selection, exact authorization, adapter dispatch | existing capability execution boundary |
| deterministic photo composition | existing local FFmpeg adapter |

No orchestration state file or duplicate task/session record is introduced.

## UI boundary

The normal shell exposes UV Studio projects only. It no longer imports or polls
the legacy `workflowApi` session/task/sandbox layer and no longer advertises
`/pipelines/*` or `/sandbox` navigation. Legacy route source remains isolated
migration evidence until a later explicit retirement slice.

For `photo_to_video`, the project page renders only the
`photo_composition` workspace returned by Product Orchestrator; generic editor,
continuity and dubbing panels are not mounted.

## Next architectural decision

Broader editor ownership is intentionally not decided here. D-033 reuse and
generic NLE ownership must be resolved in a separate ADR before expanding the
orchestrated surface into a generic editor foundation.
