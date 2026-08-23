# Product Orchestrator

## Purpose

Product Orchestrator is the product-facing projection between user intent and the existing UV Studio project/domain/capability architecture. It explains what a project can do now, what is missing, which workspace is relevant and which semantic action is valid next.

It is not a second workflow database and it is not a generic execution engine.

Canonical ownership remains:

| Concern | Owner |
|---|---|
| project identity, sources, artifacts | Project Store |
| current source bytes/integrity | Project Source Media Store / registered media integrity |
| recipe intent/policy | Recipe Registry |
| durable domain state | dedicated domain stores |
| readiness/prerequisites/workspaces/next actions | Product Orchestrator |
| runtime offers | Capability Registry |
| provider/runtime selection, authorization and dispatch | D-017 execution boundary |
| deterministic local media execution | bounded local adapters such as FFmpeg / MLT |

No orchestration state file, duplicate task/session database or second durable workflow store is introduced.

## HTTP contract

```text
GET  /api/uv/projects/{project_id}/workflow
POST /api/uv/projects/{project_id}/workflow/actions/{action_id}
```

`ProjectWorkflowState` contains:

- project/recipe identity and truthful `readiness`;
- user-facing summary;
- structured prerequisites and resolution hints;
- relevant workspaces only;
- stable semantic action IDs with bounded input schemas and verified suggested inputs;
- current/recent result artifacts;
- active jobs, user decisions and diagnostics.

A source reference alone is not readiness evidence. Project-owned media used by an action must pass the existing byte-integrity boundary. Missing or substituted bytes are excluded from projected choices and fail closed before mutation/provider dispatch.

## Authoritative recovered journeys

The orchestrator currently owns seven product journeys:

### Photo -> Video

```text
verified images
 -> photo_composition
 -> compose_photos
 -> video.compose_photos
 -> local/free FFmpeg
 -> current project video artifact
```

### Visualizer

```text
verified master audio + optional verified artwork
 -> audio_visualizer
 -> render_visualizer
 -> audio.visualize
 -> local/free FFmpeg
 -> current project video artifact
```

### Targeted Edit

```text
verified source video
 -> targeted_edit
 -> select_target_range
 -> prepare_replacement
 -> review_replacement
 -> accept_replacement
 -> render_accepted_edits
 -> current artifact
```

Range/continuity brief, replacement plan/candidate/review and accepted edit remain canonical domain state. Product Orchestrator only composes those states into user-facing readiness and semantic actions.

### Dubbing

```text
verified source
 -> dubbing
 -> transcript/import or local-ASR draft acceptance
 -> optional translation
 -> prepared speech
 -> current Review
 -> accept_dubbing_review
 -> render_accepted_dubbing
 -> current artifact
```

Dubbing, PreparedSpeech, Review and AcceptedDubbing stores remain authoritative. The orchestrator rejects stale/tampered source and prepared-audio evidence and does not expose superseded/consumed Review as repeatable acceptance.

### Music Video

```text
verified master song
 -> music_video
 -> save_music_map
 -> save_music_direction
 -> deterministic rhythm audit
 -> save_music_assembly
 -> render_music_master
 -> review_music_master
 -> approved current outcome
```

Music Map, Direction, Assembly and Music Video Review remain canonical. Rhythm audit is computed by `MusicDirectionStore.rhythm_audit()`; there is no duplicate audit store. Current render/review truth is bound to exact source bytes and exact current revisions.

### Narrated Video

```text
verified Stage 8 brief + non-empty script + verified project-owned images
 + verified PreparedAudio narration
 -> narrated_video
 -> render_narrated
 -> video.render_narrated
 -> local/free FFmpeg
 -> current SHA-bound narrated master
```

Narrated recovery reuses the existing Stage 8 workspace as the canonical brief/script/visual binding and the existing PreparedAudio store for narration. The semantic action accepts only the exact current workspace revision and a currently verified PreparedAudio ID. The current outcome remains current only while its workspace revision, image bindings, narration fingerprint and registered output bytes still match.

The first recovered Narrated master is intentionally image-led. Video bindings may remain in the canonical Stage 8 workspace, but this render does not silently claim to include them. Remote TTS remains an optional existing `speech.synthesize` route and continues to require the normal D-017 remote-consent boundary before its output can be promoted to PreparedAudio.

### General Video

```text
verified Stage 8 brief + ordered project-owned images/videos
 + zero or one explicit project-owned audio source
 -> general_video
 -> render_general
 -> video.render_general
 -> local/free FFmpeg
 -> current SHA-bound general master
```

General Video recovery reuses the existing Stage 8 workspace as the canonical task text and ordered media binding. `video.render_general` normalizes each visual to H.264 1280×720 at 30 fps, uses images for a fixed two seconds, uses video clips for their full verified duration and then joins the normalized segments. The bounded path deliberately strips embedded clip audio; it either produces a silent master or muxes one explicitly selected workspace audio source as AAC.

The semantic action accepts only the exact current workspace revision. More than one selected workspace audio source blocks readiness rather than choosing implicitly. Current outcome truth requires the exact workspace revision, ordered current visual fingerprints, optional audio fingerprint and registered output bytes to still match. Arbitrary clip timing, transitions, multi-track mixing, provider-backed generation and generic NLE mechanics are outside this first recovery path and are not implied by readiness.

## Action contract rules

`WorkflowAction.suggested_input` is executable input, not an untrusted UI side channel. Allowed choices belong to the projected input schema and are revalidated against freshly projected state immediately before dispatch.

Semantic actions do not need to map one-to-one to capabilities:

- capability-backed actions delegate through Capability Registry/D-017;
- deterministic domain decisions such as Review/Accept remain UV-owned domain operations;
- `capability_id = null` means a bounded domain action, not an authorization bypass.

A migrated recipe cannot silently fall back around an orchestrator failure. Unknown recipes fail closed as unavailable; known unrecovered recipes project partial/unavailable truth until a dedicated recovery slice exists.

## UI boundary

The supported shell exposes `/projects`, project workspaces selected by `relevant_workspaces`, and `/settings`.

The historical addressable VideoClaw routes have been retired:

- `/pipelines/standard`;
- `/pipelines/action-transfer`;
- `/pipelines/digital-human`;
- `/sandbox`.

The UV-owned server does not remount their historical session/task/sandbox backend. Any remaining legacy component source is migration evidence only and must not become an implicit fallback product path.

## Verification boundary

For each recovered journey, exact Draft and Review heads are expected to pass the five permanent CI jobs:

- `development-context`;
- `bootstrap (ubuntu-latest, 3.11)`;
- `bootstrap (windows-latest, 3.11)`;
- `app-baseline (ubuntu-latest)`;
- `app-baseline (windows-latest)`.

The app-baseline jobs include API/HTTP verification, real-media execution, frontend lint/audit/build and browser user-outcome coverage. This is Class A/API plus Class B informed-browser evidence; it does not by itself establish Class C cold-start usability or installed Windows acceptance.

## Remaining program

Project Store portable-JSON/listing hardening was completed in PR #50 before Narrated recovery, preserving the same canonical store rather than hiding persistence defects inside product orchestration.

After General Video, the next preparation-only journey to recover is Story Video. It must reuse the current Stage 8 story workspace, existing continuity/planning/editor primitives, Project Store and Capability Registry/D-017 boundaries rather than introducing a story workflow database or a second editor authority. Commercial Product remains a separate follow-up recovery path.

Repository settings such as `main` branch protection remain separate external P0 work. Stage 9 packaging/release work stays blocked until Product Truth Recovery, Class C cold-start validation and installed Windows human acceptance are complete.
