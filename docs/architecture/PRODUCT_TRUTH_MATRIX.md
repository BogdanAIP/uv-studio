# UV Studio Product Truth Matrix

## Purpose

This document separates the historical D-062 Stage 8 failure baseline from the current Product Truth Recovery implementation. Historical findings explain why the installed product felt broken; they are not allowed to masquerade as current behavior after the recovery slices.

A feature is `working` only when a user-visible action reaches a current UV-owned execution path and produces the expected state or artifact.

Status values:

- `working` — current UI -> current API/domain path -> result;
- `working_orchestrated` — `working` plus truthful Product Orchestrator readiness, prerequisites, relevant workspace and semantic next action;
- `working_with_setup` — complete path exists after an explicit optional runtime/config prerequisite;
- `partial` — valuable implementation exists but the product journey is incomplete;
- `unavailable` — intentionally fail-closed at the current product boundary;
- `legacy_isolated` — legacy source remains but is not part of supported normal navigation.

## Current top-level architecture

```text
/projects
 -> UV-owned AppShell
 -> Project Store / Recipe Registry
 -> Product Orchestrator where migrated
 -> UV semantic/domain APIs
 -> Capability Registry / D-017
 -> FFmpeg / MLT / local ML / MCP / provider adapters
```

The supported shell exposes Projects and Settings. It does not poll the historical VideoClaw session/task/sandbox runtime and does not advertise `/pipelines/*` as primary product navigation.

## Current project-page composition

Product Orchestrator workspace projection is authoritative for the two migrated deterministic journeys:

- `photo_to_video` -> `photo_composition`;
- `visualizer` -> `audio_visualizer`.

For those projects the page does **not** also mount generic Project Editor, Sequence Continuity or Dubbing panels. The workspace decision therefore comes from `ProjectWorkflowState.relevant_workspaces`, not a second `recipe_id` switch.

Non-migrated recipes still return an empty workspace projection and keep their existing domain panels until dedicated Product Orchestrator migrations replace that presentation. Cross-workflow leakage is therefore fixed for the migrated deterministic journeys, not application-wide.

## Core frontend -> backend truth

| User area | Current UI/API | Backend authority | Current truth |
|---|---|---|---|
| project create/open/archive | project pages + `projectsApi` | Project Store | **strong foundation** |
| Photo -> Video | Product Orchestrator -> `Stage8MediaPanel` | `compose_photos` -> `video.compose_photos` -> local FFmpeg | **working_orchestrated** |
| Visualizer | Product Orchestrator -> `Stage8MediaPanel` | `render_visualizer` -> `audio.visualize` -> local FFmpeg | **working_orchestrated** |
| generic video import/preview | `ProjectEditor` / `editorApi` | project source media/editor state | **working** |
| targeted range selection | `ProjectEditor` -> `/editor/commands` | `EditorCommandService` + Continuity Brief | **working**, orchestration next |
| replacement plan/candidate/review | replacement UI/APIs | UV replacement domains + capabilities | **working**, internal state too visible |
| accepted edit render | render path | accepted edit state + bounded media render | **working** |
| sequence continuity | continuity panel/APIs | sequence domain | **working optional domain**, still overexposed on non-migrated pages |
| dubbing | dubbing panels/APIs | ASR/translation/speech/alignment/review/render domains | **substantial working path**, setup/UX partial |
| music map/direction/assembly/review | music UI/APIs | Music domains + render | **working domains**, product orchestration partial |
| Story/Commercial preparation | `Stage8CompositionPanel` | Stage 8 composition state | **partial production journey** |
| Performance lip-sync | dedicated panel | optional MuseTalk capability path | **working_with_setup** |
| product workflow readiness | Product Orchestrator | Project Store + verified source state + Recipe/Capability Registry | **Photo + Visualizer migrated**; other recipes fail closed as `partial`/unavailable projection |

## Deterministic reference journeys

### Photo -> Video

```text
verified project-owned images
 -> readiness/prerequisites
 -> photo_composition workspace
 -> compose_photos
 -> video.compose_photos
 -> local/free FFmpeg offer
 -> project video artifact
```

Damaged/substituted image bytes do not satisfy readiness. The semantic action remains capability-backed and bounded by Project Store source IDs.

### Visualizer

```text
verified project-owned master audio
 + optional verified artwork
 -> readiness/prerequisites
 -> audio_visualizer workspace
 -> render_visualizer
 -> audio.visualize
 -> local/free FFmpeg offer
 -> project video artifact
```

Visualizer no longer calls the capability execution endpoint directly from the product panel. The UI invokes `/workflow/actions/render_visualizer`, and allowed source IDs are projected through the action schema from verified project-owned media. Tampered audio disables the action and removes the invalid source from the usable choices.

`WorkflowAction.suggested_input` is executable action input, not a side channel for UI-only option lists. Allowed source choices belong to the bounded `input_schema`.

## Recipe matrix — current recovery truth

| Recipe | Intended outcome | Current UV-owned path | Status | Required recovery |
|---|---|---|---|---|
| `general_video` | brief -> general video | no complete brief -> plan -> assets -> assembly -> export journey | `partial` | build orchestrated current path |
| `narrated_video` | topic/script -> narration -> visuals -> video | stale pipeline target removed; replacement full journey absent | `unavailable` product execution | implement current semantic path |
| `music_video` | song-driven clip | real Music Map/Direction/Assembly/Review domains | `partial` UX | intent-first orchestration over existing domains |
| `action_transfer` | motion source + target -> result | semantic capability exists; stale pipeline target removed | `unavailable` product journey | build authorized current workflow or keep unavailable |
| `digital_human` | portrait + speech -> talking video | capability/domain pieces exist; no complete baseline journey | `partial` | truthful capability-gated workflow |
| `story_video` | story -> video | brief/script/material workspace | `partial` | extend preparation to orchestrated production |
| `commercial_product` | brief/materials -> ad video | preparation workspace | `partial` | orchestrated production path |
| `photo_to_video` | photos + optional audio -> video | Product Orchestrator `compose_photos` -> local FFmpeg | `working_orchestrated` | preserve reference journey |
| `visualizer` | audio + optional artwork -> video | Product Orchestrator `render_visualizer` -> local FFmpeg | `working_orchestrated` | preserve second reference journey |
| `performance_lip_sync` | portrait + speech -> lip-sync | optional MuseTalk path | `working_with_setup` | project setup/readiness before use |
| `free_project` | flexible tools | reusable primitives, no coherent next-action owner | `partial` | orchestrated tool palette, not every specialist workflow at once |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | no complete UV-owned journey | `partial` | orchestration + execution baseline |
| B. Narrated video | historical path fail-closed; replacement incomplete | `unavailable/partial` | current narrated workflow |
| C. Music-video excerpt | strong domains, schema-heavy journey | `partial` | intent-first orchestration |
| D. Dubbing | substantial real path with runtime/setup gates | `working_with_setup` / UX-partial | prerequisite projection + task isolation |
| E. Targeted edit | real range/replacement/review/render | `working` / UX-partial | Product Orchestrator next-action projection |

## Confirmed remaining defects

### Non-migrated workspace leakage

Photo and Visualizer are no longer evidence for this defect. Story, Music, Dubbing-related and other non-migrated recipes can still inherit generic specialist surfaces because their Product Orchestrator projection does not yet declare an authoritative workspace set.

### Recipe creation is readiness-blind

`/projects` still shows recipe cards before project-level `ready | setup_required | partial | unavailable` truth is available. Working, setup-gated and incomplete tasks therefore look more equivalent than they are before creation.

### Targeted edit exposes implementation vocabulary

The durable Brief -> Plan -> Candidate -> Review -> Accepted model is valuable, but the ordinary user still sees too much of that state machine. The next recovery slice should preserve the domain chain while projecting clear prerequisites and next actions.

### Legacy routes remain source debt

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and `/pipelines/*` source still exists. The historical backend runtime remains intentionally absent. Correct recovery is dependency-proven migration/removal, not remounting it.

## D-033 editor truth

D-033 remains accepted. PR #44 repaired the concrete accepted-edit mutation bypass by routing removal through the semantic editor Command API and leaving `/edits` read-only. MLT stays a bounded engine representation, OpenCut Classic a selective UX/component donor, and Project Store/domain state remains canonical.

Incomplete generic undo/redo or full GUI/script/AI/MCP equivalence are bounded follow-up concerns, not grounds to replace the editor foundation.

## Product Orchestrator contract

```text
ProjectWorkflowState
- schema_version
- project_id / recipe_id
- readiness
- summary / current_outcome
- prerequisites[]
- relevant_workspaces[]
- next_actions[]
- active_jobs[]
- user_decisions[]
- recent_artifacts[]
- diagnostics[]
```

The contract is a projection over canonical state and runtime availability, not a second workflow database.

Semantic next actions do not need to map one-to-one to capabilities. Capability-backed media operations may delegate through Capability Registry/D-017, while review/accept/decision actions may remain UV-owned domain commands.

## Test evidence

Existing browser suites are Class B informed-regression evidence. The deterministic reference suite now proves both Photo and Visualizer through Product Orchestrator actions, workspace isolation, real local artifacts and source-integrity fail-closed behavior.

Class C cold-start product tests must still start from user-equivalent state, avoid hidden workflow-decision seeding and prove a real result for any task advertised as ready. Installed Windows human acceptance remains release-blocking.
