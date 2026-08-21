# UV Studio Frontend / Backend Interaction Map

## Purpose

This is the current interaction/ownership map after Product Truth Inventory (#42) and the first Product Orchestrator foundation (#43). Historical Stage 8 coupling is retained only where it explains migration debt.

## Supported product path

```text
UV-owned AppShell
      |
      v
   /projects
      |
      +--> Project Store / Recipe Registry
      |
      +--> Product Orchestrator (migrated recipes)
      |        |
      |        +--> readiness / prerequisites / relevant workspaces / next actions
      |
      +--> UV semantic/domain APIs
               |
        +------+----------------+
        |                       |
   Project/domain state    Capability Registry + D-017
        |                       |
        +-----------+-----------+
                    v
       FFmpeg / MLT / local ML / MCP / providers
```

The frontend renders product state, collects bounded inputs and invokes semantic/domain actions. It is not the canonical workflow/timeline store.

## Canonical authorities

| Concern | Current authority | Direction |
|---|---|---|
| project identity/sources/artifacts | Project Store | preserve |
| recipe intent/policy | Recipe Registry | preserve |
| product readiness/prerequisites/workspaces/next actions | Product Orchestrator | expand recipe-by-recipe |
| capability metadata/selection | Capability Registry + SelectionPolicy | preserve |
| remote/non-free consent | D-017 authorization | preserve |
| edit/dubbing/music/continuity durable state | UV project/domain stores | preserve |
| meaningful editor mutations | UV semantic/domain command boundaries | enforce D-033 |
| editor engine representation | MLT behind UV adapter | preserve/expand only with evidence |
| reusable editor interaction UI | selective OpenCut Classic-derived components/helpers | reuse where valuable |
| accepted-edit final export | current bounded FFmpeg path | preserve until parity evidence changes ownership |

## Product Orchestrator status

Implemented HTTP seam:

```text
GET  /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

`ProjectWorkflowState` is a read projection over canonical project/domain state plus runtime capability availability. It does not create a second workflow database.

### Photo -> Video

Current first migrated journey:

```text
project images
 -> verify project-owned bytes
 -> Product Orchestrator readiness/prerequisites
 -> relevant workspace: photo_composition
 -> semantic action: compose_photos
 -> video.compose_photos
 -> local FFmpeg adapter
 -> project video artifact
 -> refreshed current_outcome/recent_artifacts
```

This is `working_orchestrated`.

### Visualizer

Current execution path is real:

```text
project audio + optional artwork
 -> audio.visualize
 -> local FFmpeg adapter
 -> project artifact
```

But Visualizer is **not yet Product-Orchestrator-migrated**. `project_workflow_state()` currently returns the generic not-migrated/partial projection for it. It is the next deterministic reference candidate.

## Current project-page routing

Photo-to-Video uses Product Orchestrator `relevant_workspaces` to decide its primary workspace and avoids unrelated generic panels.

The remaining recipes still use a parallel frontend `recipe_id` decision tree and, for every non-photo project, mount generic `ProjectEditor`, Sequence Continuity and three Dubbing panels before/alongside specialist panels.

Target direction:

```text
ProjectWorkflowState.relevant_workspaces
        |
        v
workspace registry / renderer
        |
        +--> only declared task workspaces
```

Do not replace this with another universal page that appends every specialist tool.

## Editor path and D-033 ownership

```text
browser interaction
(playhead/drag/zoom/forms)
        |
        | transient only
        v
UV semantic/domain command
        |
        v
canonical Project Store/domain state
        |
        +--> MLT derived engine projection
        |
        +--> bounded FFmpeg/render adapters
```

`RangeTimeline.tsx` and `timelineMath.ts` selectively adapt OpenCut Classic ruler/playhead/snap interaction ideas. UV integer-microsecond identity remains canonical.

`MLTTimelineAdapter` derives ephemeral engine XML from accepted UV edit state. Raw MLT XML is not exposed as a public mutation surface.

PR #44 repairs one concrete D-033 bypass: accepted-edit removal moves from direct `DELETE /edits/{edit_id}` store mutation to semantic `remove_accepted_edit` on `/editor/commands`; `/edits` becomes read-only inspection.

This does not imply all coherent domains must collapse into one endpoint. Replacement Review, Dubbing Review and Music domains may keep dedicated UV-owned contracts when those contracts themselves are the semantic/domain mutation boundary.

## Targeted edit path

```text
source upload/probe
 -> project source registration
 -> select range + change request
 -> EditorCommandService / RangeContinuityBrief
 -> replacement plan
 -> candidate preparation/capability
 -> evidence-based review
 -> accepted edit
 -> bounded render/export
```

The backend chain is real. Recovery work is primarily next-action/prerequisite projection and reducing implementation vocabulary exposed to ordinary users.

## Dubbing path

```text
project video
 -> speech.transcribe capability
 -> accepted transcript
 -> optional translation
 -> prepared speech / TTS / import
 -> review/alignment
 -> accepted dubbing state
 -> video.render_dubbing
 -> artifact/subtitles
```

This is substantial real functionality. Remaining product gaps are setup visibility, workflow isolation and intent-first orchestration.

## Music Video path

```text
song
 -> Music Map
 -> Direction
 -> assets
 -> Assembly
 -> rhythm/final review
 -> render artifact
```

The domain model is real. Product recovery should propose/populate plans and expose decisions, not delete the durable Music Map/Direction/Review state.

## Story / Commercial / Free

Stage 8 workspace APIs persist useful brief/script/material choices. They are preparation state, not complete production engines. Product Orchestrator must expose truthful next actions before these modes can be called complete journeys.

## Performance lip-sync

Verified MuseTalk-backed `video.digital_human` execution is real when optional runtime/model/CUDA preflight succeeds. Product readiness should project that setup requirement before the user enters the workflow.

## Legacy VideoClaw migration debt

The Stage 8 baseline had a root AppShell that linked/polled the old VideoClaw runtime through `workflowApi.ts`. PR #43 removed that authority from the supported shell.

Still-present legacy source includes:

- `frontend/lib/workflowApi.ts`;
- HomePage / WorkflowPanel;
- PipelinePage and `/pipelines/*` routes;
- related old sandbox/session/task helpers.

These call historical families such as `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/upload_media` and old `/api/project/*` routes. The UV-owned server intentionally does not restore those families.

Migration rule:

```text
wanted outcome?
  yes -> rebuild on Product Orchestrator + current UV semantic/domain/capability path
  no  -> remove after call-site/dependency proof
```

Never use a broken legacy page as justification to remount the complete old backend.

## Capability architecture to preserve

```text
CapabilityDefinition
 -> CapabilityOffer(s)
 -> SelectionPolicy
 -> D-017 authorization when required
 -> Execution adapter
 -> result + provenance + artifact
```

Invariants:

- semantic IDs stay provider-neutral;
- `local_free_first` fails closed;
- remote/non-free execution is explicit;
- project-scoped inputs prevent arbitrary host-path execution;
- MCP/local/provider adapters are peers, not mandatory product authorities.

Product Orchestrator consumes this layer; it does not replace it.

## Current major gaps

1. Product Orchestrator coverage is still only one recipe.
2. Non-photo project pages still reconstruct workspace relevance in React and overexpose unrelated domains.
3. Recipe creation does not show readiness before project creation.
4. Core journeys (targeted edit, dubbing, music, narrated, general) still need intent-first Product Orchestrator projections.
5. D-033 conformance is incomplete in areas such as shared undo/redo and full GUI/scripts/AI/MCP mutation equivalence; these are bounded follow-up problems, not a reason to redefine the product/editor foundation.
6. Legacy frontend route source still needs dependency-proven retirement.

## Next interaction-layer slice

After the D-033 conformance PR closes, migrate Visualizer to Product Orchestrator and introduce/strengthen a workspace renderer driven by `relevant_workspaces` for the orchestrated deterministic journeys. Photo and Visualizer should then prove one product contract can isolate two different local intent-to-artifact workflows without generic NLE growth.
