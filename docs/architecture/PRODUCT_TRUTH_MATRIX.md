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

Product Orchestrator workspace projection is authoritative for three migrated journeys:

- `photo_to_video` -> `photo_composition`;
- `visualizer` -> `audio_visualizer`;
- `free_project` -> `targeted_edit`.

For those projects the page mounts only the workspace declared by `ProjectWorkflowState.relevant_workspaces`. Photo/Visualizer do not inherit generic editor, dubbing or continuity panels. `free_project` now enters the targeted existing-video editor and no longer mounts the historical Stage 8 Free workspace, dubbing or sequence-continuity panels alongside it.

Non-migrated recipes still return an empty authoritative workspace projection and temporarily keep their existing domain panels until dedicated Product Orchestrator migrations replace that presentation. A bounded frontend compatibility adapter may call existing UV-owned targeted-edit domain/capability endpoints only when a fresh `ProjectWorkflowState` explicitly reports `workflow_not_migrated` and has no `targeted_edit` workspace. A migrated recipe cannot silently fall back around an Orchestrator failure.

## Core frontend -> backend truth

| User area | Current UI/API | Backend authority | Current truth |
|---|---|---|---|
| project create/open/archive | project pages + `projectsApi` | Project Store | **strong foundation** |
| Photo -> Video | Product Orchestrator -> `Stage8MediaPanel` | `compose_photos` -> `video.compose_photos` -> local FFmpeg | **working_orchestrated** |
| Visualizer | Product Orchestrator -> `Stage8MediaPanel` | `render_visualizer` -> `audio.visualize` -> local FFmpeg | **working_orchestrated** |
| targeted existing-video edit | Product Orchestrator -> `ProjectEditor` / replacement UI | semantic actions over existing Brief/Plan/Candidate/Review/Accepted stores | **working_orchestrated** |
| targeted range selection | `select_target_range` | `EditorCommandService` + Continuity Brief | **working_orchestrated** |
| replacement preparation | `prepare_replacement` | existing ReplacementPlan + ReplacementCandidate stores | **working_orchestrated**; hidden Plan remains durable domain state |
| replacement review/accept | `review_replacement`, `accept_replacement` | evidence-based ReplacementReview + AcceptedRangeEdit | **working_orchestrated** |
| accepted edit render | `render_accepted_edits` | `video.render_edits` capability + bounded local FFmpeg | **working_orchestrated** |
| sequence continuity | continuity panel/APIs | sequence domain | **working optional domain**, still exposed only on non-migrated compatible pages |
| dubbing | dubbing panels/APIs | ASR/translation/speech/alignment/review/render domains | **substantial working path**, setup/UX partial |
| music map/direction/assembly/review | music UI/APIs | Music domains + render | **working domains**, product orchestration partial |
| Story/Commercial preparation | `Stage8CompositionPanel` | Stage 8 composition state | **partial production journey** |
| Performance lip-sync | dedicated panel | optional MuseTalk capability path | **working_with_setup** |
| product workflow readiness | Product Orchestrator | Project Store + verified source/domain state + Recipe/Capability Registry | **Photo + Visualizer + Targeted Edit migrated**; others fail closed as partial/unavailable projection |

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

Visualizer does not call the capability execution endpoint directly from the product panel. The UI invokes `/workflow/actions/render_visualizer`, and allowed source IDs are projected through the action schema from verified project-owned media. Tampered audio disables the action and removes the invalid source from usable choices.

### Targeted existing-video edit

```text
verified project-owned source video
 -> targeted_edit workspace
 -> select_target_range
 -> canonical RangeContinuityBrief
 -> prepare_replacement
 -> hidden durable ReplacementPlan + full ReplacementCandidate
 -> review_replacement
 -> evidence-based ReplacementReview
 -> accept_replacement
 -> canonical AcceptedRangeEdit
 -> render_accepted_edits
 -> video.render_edits / local FFmpeg
 -> project video artifact
```

The Product Orchestrator owns only the read projection and semantic action contract. It does not persist a second workflow state. The existing domain stores remain authoritative.

`prepare_replacement` deliberately combines the technical Plan + Candidate steps into one user-facing action. The operation restores the exact prior plan state and removes any partially registered artifact if candidate preparation fails, so a failed semantic action cannot leave a hidden half-commit.

Approved reviews already represented by Accepted state are not advertised as repeatable Accept actions. A render artifact is `current_outcome` only when its `source_path` and `edit_ids` exactly match the current Accepted state for that source; an older successful render is retained in recent artifacts but cannot masquerade as the current result.

`WorkflowAction.suggested_input` is executable action input, not a side channel for UI-only option lists. Allowed choices and allowed edit/replacement pairs belong to the bounded `input_schema` and are revalidated immediately before mutation or provider dispatch.

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
| `visualizer` | audio + optional artwork -> video | Product Orchestrator `render_visualizer` -> local FFmpeg | `working_orchestrated` | preserve reference journey |
| `performance_lip_sync` | portrait + speech -> lip-sync | optional MuseTalk path | `working_with_setup` | project setup/readiness before use |
| `free_project` | targeted flexible editing baseline | Product Orchestrator targeted-edit actions over existing canonical editor/replacement domains | `working_orchestrated` for targeted edit | later decide broader free-tool palette without remounting every specialist workflow |

## Permanent release scenarios

| Scenario | Current truth | Status | Blocking gap |
|---|---|---|---|
| A. General video | no complete UV-owned journey | `partial` | orchestration + execution baseline |
| B. Narrated video | historical path fail-closed; replacement incomplete | `unavailable/partial` | current narrated workflow |
| C. Music-video excerpt | strong domains, schema-heavy journey | `partial` | intent-first orchestration |
| D. Dubbing | substantial real path with runtime/setup gates | `working_with_setup` / UX-partial | prerequisite projection + task isolation |
| E. Targeted edit | orchestrated range/replacement/review/accept/render path | `working_orchestrated` | Class C cold-start evidence + later installed acceptance |

## Confirmed remaining defects

### Non-migrated workspace leakage

Photo, Visualizer and targeted `free_project` are no longer evidence for this defect. Story, Music, Dubbing-related and other non-migrated recipes can still inherit generic specialist surfaces because their Product Orchestrator projection does not yet declare an authoritative workspace set.

### Recipe creation is readiness-blind

`/projects` still shows recipe cards before project-level `ready | setup_required | partial | unavailable` truth is available. Working, setup-gated and incomplete tasks therefore look more equivalent than they are before creation.

### Targeted edit still needs cold-start product evidence

The ordinary targeted-edit panel now presents the main replacement path as `Вариант -> проверка -> принять` and hides the separate technical Plan step, while preserving candidate/review/accept trust boundaries underneath. This is a product improvement, not proof of first-time discoverability. Existing browser coverage remains Class B informed regression; Class C must still prove the journey from user-equivalent clean state without implementation knowledge.

### Legacy routes remain source debt

Legacy `workflowApi.ts`, HomePage/WorkflowPanel/PipelinePage and `/pipelines/*` source still exists. The historical backend runtime remains intentionally absent. Correct recovery is dependency-proven migration/removal, not remounting it.

## D-033 editor truth

D-033 remains accepted. PR #44 repaired the concrete accepted-edit mutation bypass by routing removal through the semantic editor Command API and leaving `/edits` read-only. The targeted-edit migration preserves that direction: persistent edit decisions still flow through UV-owned semantic/domain boundaries; Product Orchestrator is a façade/projection, not editor ownership.

MLT stays a bounded engine representation, OpenCut Classic a selective UX/component donor, and Project Store/domain state remains canonical. Incomplete generic undo/redo or full GUI/script/AI/MCP equivalence are bounded follow-up concerns, not grounds to replace the editor foundation.

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

Semantic next actions do not need to map one-to-one to capabilities. Capability-backed media operations delegate through Capability Registry/D-017, while review/accept/decision actions remain UV-owned domain commands. `capability_id = null` means a bounded domain action, not an authorization bypass.

## Test evidence

Existing browser suites are Class B informed-regression evidence. The deterministic reference suite proves Photo and Visualizer through Product Orchestrator actions, workspace isolation, real local artifacts and source-integrity fail-closed behavior.

Targeted-edit browser evidence now uses a dedicated `free_project` journey and verifies that Dubbing/Continuity/old Free Workspace surfaces are absent there. Dubbing and Sequence Continuity remain a separate compatibility regression on a non-migrated `general_video` project rather than being forced into the targeted-edit product journey. The targeted path uses the Product Orchestrator semantic actions for range selection, replacement preparation, review, accept and final render.

Class C cold-start product tests must still start from user-equivalent state, avoid hidden workflow-decision seeding and prove a real result for any task advertised as ready. Installed Windows human acceptance remains release-blocking when release-candidate work resumes.
