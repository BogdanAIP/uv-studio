# UV Studio Product Truth Matrix

## Purpose

This document records the current product truth after Product Truth Recovery through Narrated PR #52. Historical Stage 8/9 findings remain useful engineering evidence, but they must not be presented as current product behavior after a journey has been recovered.

A feature is `working` only when a visible action reaches a current UV-owned semantic/domain or capability boundary and produces current canonical state or a verified artifact.

Status values:

- `working_orchestrated` — visible UI, truthful Product Orchestrator projection and current execution path are connected;
- `working_with_setup` — the complete path exists after an explicit runtime/configuration prerequisite;
- `partial` — useful implementation exists, but the normal product journey is incomplete;
- `unavailable` — intentionally fail-closed at the current product boundary;
- `legacy_isolated` — retained source/history that is not addressable from the supported product shell.

## Current top-level architecture

```text
/projects
 -> UV-owned AppShell
 -> Project Store / canonical domain stores
 -> Product Orchestrator projection + semantic actions
 -> Capability Registry / D-017 where execution is provider/runtime-backed
 -> local FFmpeg / MLT / local ML / MCP / provider adapters
```

Product Orchestrator is not a durable workflow database. Project Store and the dedicated domain stores remain canonical. Capability Registry and D-017 remain the provider/runtime selection, authorization and dispatch boundary.

## Recovered authoritative journeys

Six visible Class A/B journeys are now authoritative through Product Orchestrator:

1. `photo_to_video -> photo_composition`;
2. `visualizer -> audio_visualizer`;
3. `free_project -> targeted_edit`;
4. `dubbing -> dubbing`;
5. `music_video -> music_video`;
6. `narrated_video -> narrated_video`.

For these recipes, `ProjectWorkflowState.relevant_workspaces` controls the supported project-page surface. A migrated recipe must not silently fall back to a legacy workspace when its orchestrator projection fails.

## Core frontend -> backend truth

| User area | Current authority | Current truth |
|---|---|---|
| project create/open/archive | Project Store | **strong foundation** |
| Photo -> Video | Product Orchestrator -> `video.compose_photos` -> local FFmpeg | **working_orchestrated** |
| Visualizer | Product Orchestrator -> `audio.visualize` -> local FFmpeg | **working_orchestrated** |
| targeted existing-video edit | Product Orchestrator -> editor/replacement domain stores -> `video.render_edits` | **working_orchestrated** |
| Dubbing | Product Orchestrator -> Dubbing/PreparedSpeech/Review/Accepted state -> `video.render_dubbing` | **working_orchestrated** |
| Music Video | Product Orchestrator -> Music Map/Direction/Assembly/rhythm Review -> `video.render_music_video` | **working_orchestrated** |
| Narrated Video | Product Orchestrator -> Stage 8 workspace + PreparedAudio -> `video.render_narrated` | **working_orchestrated**, current master is image-led |
| sequence continuity | sequence domain | **working optional domain**, not a recovered top-level journey |
| Story/Commercial preparation | Stage 8 composition state | **partial** |
| Performance lip-sync | optional MuseTalk capability path | **working_with_setup** |
| General Video | incomplete general production journey | **partial** |

## Deterministic reference journeys

### Photo -> Video

```text
verified project-owned images
 -> photo_composition workspace
 -> compose_photos
 -> video.compose_photos
 -> local/free FFmpeg
 -> verified project video artifact
```

Source references are not sufficient evidence by themselves. Current project-owned bytes must match registered integrity metadata.

### Visualizer

```text
verified project-owned master audio
 + optional verified artwork
 -> audio_visualizer workspace
 -> render_visualizer
 -> audio.visualize
 -> local/free FFmpeg
 -> verified project video artifact
```

The product UI invokes the semantic workflow action rather than calling capability execution directly.

### Targeted existing-video edit

```text
verified source video
 -> select_target_range
 -> RangeContinuityBrief
 -> prepare_replacement
 -> ReplacementPlan + ReplacementCandidate
 -> review_replacement
 -> ReplacementReview
 -> accept_replacement
 -> AcceptedRangeEdit
 -> render_accepted_edits
 -> video.render_edits / local FFmpeg
 -> current artifact
```

The Product Orchestrator projects current state and allowed semantic actions; the existing editor/replacement stores remain canonical.

### Dubbing

```text
verified source video
 -> verified transcript or explicit local-ASR draft acceptance
 -> optional accepted translation
 -> prepared project-owned speech
 -> current evidence-bound Review
 -> accept_dubbing_review
 -> AcceptedDubbing
 -> render_accepted_dubbing
 -> video.render_dubbing / local FFmpeg
 -> current artifact
```

Prepared speech and source media fail closed when registered bytes no longer match metadata. Review acceptance is explicit-current; consumed or superseded reviews are not advertised as repeatable decisions. Composition policy remains server-owned.

### Music Video

```text
verified master song
 -> Music Map
 -> Music Direction
 -> deterministic rhythm audit
 -> Music Assembly bound to verified project-owned video
 -> render_music_master
 -> evidence-bound Music Video Review
 -> approved current outcome
```

`MusicMapStore`, `MusicDirectionStore`, `MusicAssemblyStore` and `MusicVideoReviewStore` are canonical. Rhythm audit remains `MusicDirectionStore.rhythm_audit()`; there is no duplicate `MusicAuditStore`. A render is current only when source bytes and exact Map/Direction/Assembly revisions match current canonical state.

### Narrated Video

```text
verified Stage 8 brief + non-empty script
 + verified project-owned image bindings
 + verified PreparedAudio narration
 -> narrated_video workspace
 -> render_narrated
 -> video.render_narrated / local FFmpeg
 -> current SHA-bound narrated master
```

The existing Stage 8 workspace remains canonical for brief/script/visual bindings and PreparedAudio remains canonical for narration. The action schema exposes only the exact current workspace revision and currently verified PreparedAudio IDs. Substituting an image, narration file or rendered output invalidates readiness/current-outcome evidence instead of being accepted silently.

The first recovered Narrated renderer is intentionally image-led. Stage 8 video bindings are preserved as canonical inputs but are not falsely presented as rendered by this capability. TTS is optional through the existing `speech.synthesize` capability and normal D-017 remote consent; TTS output must still become verified PreparedAudio before Narrated render can consume it.

## Recipe matrix — current recovery truth

| Recipe | Intended outcome | Status | Required recovery |
|---|---|---|---|
| `general_video` | brief -> general video | `partial` | next authoritative orchestrated production path |
| `narrated_video` | topic/script -> narration -> visuals -> video | `working_orchestrated` | preserve image-led truth; broader visual assembly is later scope |
| `music_video` | song-driven clip | `working_orchestrated` | preserve; Class C/install evidence later |
| `action_transfer` | motion source + target -> result | `unavailable` product journey | build authorized current workflow or keep unavailable |
| `digital_human` | portrait + speech -> talking video | `partial` | truthful capability-gated workflow |
| `story_video` | story -> video | `partial` | extend preparation to production |
| `commercial_product` | brief/materials -> ad video | `partial` | extend preparation to production |
| `photo_to_video` | photos + optional audio -> video | `working_orchestrated` | preserve |
| `visualizer` | audio + optional artwork -> video | `working_orchestrated` | preserve |
| `performance_lip_sync` | portrait + speech -> lip-sync | `working_with_setup` | setup/readiness refinement |
| `free_project` | targeted flexible editing baseline | `working_orchestrated` for targeted edit | broader tool palette is a later decision |
| `dubbing` | translated/replaced speech over source video | `working_orchestrated` | preserve; broader provider UX later |

## Legacy route truth

The supported shell is `/projects` plus `/settings`. The obsolete Next.js pages that made the old VideoClaw pipeline/sandbox UI directly addressable have been retired:

- `/pipelines/standard`;
- `/pipelines/action-transfer`;
- `/pipelines/digital-human`;
- `/sandbox`.

Historical legacy components may remain temporarily as isolated source until dependency-proven removal, but they are not supported product routes and the UV-owned backend does not remount the historical session/task/sandbox runtime.

## Confirmed remaining product work

### Project Store hardening is complete

PR #50 closed the foundation-level portable-JSON/listing gap before Narrated recovery. Canonical project mappings are recursively constrained to portable JSON values, non-finite numbers are rejected, archive import reaches the same strict boundary, and malformed projects are isolated from healthy-project listing without deleting their damaged bytes.

### General orchestration

General Video is the next unrecovered core top-level production journey. It must reuse canonical Project Store/editor/Stage 8/capability boundaries and the accepted D-033 editor ownership map; it must not introduce a generic workflow database or a second editing authority.

### Recipe creation is readiness-blind

`/projects` still shows recipe cards before project-level `ready | setup_required | partial | unavailable` state exists. Incomplete and ready tasks therefore look more equivalent before creation than they should.

### Class C and installed acceptance are still missing

Current browser suites are Class B informed-regression evidence. Recovered journeys have real API/browser/media evidence, but that does not prove first-time discoverability from a user-equivalent clean state. Class C cold-start validation and installed Windows human acceptance remain release-blocking.

### Repository branch protection is external P0

`main` currently has no branch protection. This is a repository-setting defect, not something application code can truthfully emulate. Required status checks should be enforced in GitHub settings when repository administration is available.

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

Semantic actions do not map one-to-one to capabilities. Capability-backed media operations delegate through Capability Registry/D-017; review, accept and other deterministic decisions remain UV-owned domain commands. `capability_id = null` means a bounded domain action, not an authorization bypass.

## Release gate

UV Studio is not release-ready. The current order is:

1. complete Narrated exact-head Draft/Review verification and merge;
2. General orchestration;
3. Class C cold-start validation;
4. installed Windows human acceptance;
5. only then resume Stage 9 packaging/release work.
