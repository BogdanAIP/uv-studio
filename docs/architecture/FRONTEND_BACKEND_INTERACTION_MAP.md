# UV Studio Frontend / Backend Interaction Map

## Purpose

This is the current interaction/ownership map after Product Truth Inventory, Product Orchestrator foundation, D-033 conformance and the deterministic workspace-routing recovery.

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

The frontend renders projected product state, collects bounded input and invokes semantic/domain actions. It is not the canonical workflow or timeline store.

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

## Product Orchestrator HTTP seam

```text
GET  /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

`ProjectWorkflowState` is a read projection over canonical project/domain state plus runtime capability availability. It creates no second workflow database.

## Migrated deterministic journeys

### Photo -> Video

```text
verified project images
 -> readiness/prerequisites
 -> relevant workspace: photo_composition
 -> semantic action: compose_photos
 -> video.compose_photos
 -> local/free FFmpeg adapter
 -> project video artifact
```

### Visualizer

```text
verified project audio
 + optional verified artwork
 -> readiness/prerequisites
 -> relevant workspace: audio_visualizer
 -> semantic action: render_visualizer
 -> audio.visualize
 -> local/free FFmpeg adapter
 -> project video artifact
```

Both flows use the same product contract and source-integrity rule. Visualizer no longer invokes the raw capability execution endpoint from its product panel. The action schema exposes only verified project source IDs, and `suggested_input` remains an executable action payload rather than UI-only metadata.

## Current project-page routing

For a migrated journey, `ProjectWorkflowState.relevant_workspaces` is authoritative:

```text
ProjectWorkflowState.relevant_workspaces
        |
        v
project-page workspace renderer
        |
        +--> photo_composition
        +--> audio_visualizer
```

When a dedicated Product Orchestrator workspace is projected, the page does not also mount generic Project Editor, Sequence Continuity or Dubbing panels. This removes the duplicate recipe-driven workspace decision path for Photo and Visualizer.

Non-migrated recipes still return no authoritative workspace projection and retain their current domain panels until their own bounded migration. The next such migration is targeted existing-video edit.

## Targeted edit path — current backend truth

```text
source upload/probe
 -> project source registration
 -> select range + requested change
 -> EditorCommandService / RangeContinuityBrief
 -> replacement plan
 -> candidate preparation/capability
 -> evidence-based review
 -> accepted edit
 -> bounded render/export
```

This chain is real. Recovery should project it as understandable prerequisites and next actions rather than replacing its durable Brief -> Plan -> Candidate -> Review -> Accept invariants.

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

`RangeTimeline.tsx` and `timelineMath.ts` selectively adapt OpenCut Classic interaction ideas while UV integer-microsecond identity remains canonical. `MLTTimelineAdapter` derives an engine representation from accepted UV edit state; raw MLT state is not a public mutation authority.

PR #44 repaired the concrete accepted-edit removal bypass by moving mutation to semantic `remove_accepted_edit` under `/editor/commands` and leaving `/edits` read-only.

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

Substantial real functionality exists. Product gaps are setup visibility, workflow isolation and intent-first orchestration.

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

The domain model is real. Recovery should propose/populate structure and surface decisions without deleting durable Music Map/Direction/Review state.

## Story / Commercial / Free

Stage 8 workspace APIs persist useful brief/script/material choices. They are preparation state, not complete production journeys. Product Orchestrator must expose truthful next actions before these modes can be called complete.

## Performance lip-sync

MuseTalk-backed `video.digital_human` execution is real when the optional runtime/model/CUDA preflight succeeds. Product readiness should project that setup requirement before the user enters the workflow.

## Legacy VideoClaw migration debt

The Stage 8 baseline had a root shell that linked and polled the old VideoClaw runtime through `workflowApi.ts`. The supported AppShell no longer gives that runtime product authority.

Still-present legacy source includes:

- `frontend/lib/workflowApi.ts`;
- HomePage / WorkflowPanel;
- PipelinePage and `/pipelines/*` routes;
- related old sandbox/session/task helpers.

The UV-owned server intentionally does not restore their historical endpoint families. Wanted outcomes must be rebuilt on current UV semantic/domain/capability paths; unwanted surfaces should be removed after dependency proof.

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

1. Product Orchestrator currently covers two deterministic recipes, not the core production journeys.
2. Non-migrated pages can still expose unrelated domain surfaces because they have no authoritative projected workspace set yet.
3. Recipe creation does not show readiness before project creation.
4. Targeted edit, dubbing, music, narrated and general journeys still need intent-first Product Orchestrator projections.
5. D-033 follow-up such as shared undo/redo and full GUI/scripts/AI/MCP mutation equivalence remains bounded work, not a reason to redefine the editor foundation.
6. Legacy frontend route source still needs dependency-proven retirement.

## Next interaction-layer slice

Migrate targeted existing-video edit to Product Orchestrator without replacing its accepted domain model. The product surface should expose source/range/change/review/export as understandable next actions while the durable Brief -> Plan -> Candidate -> Review -> Accept chain remains underneath.
