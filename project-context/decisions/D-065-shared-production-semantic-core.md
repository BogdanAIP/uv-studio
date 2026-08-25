# D-065 — Shared Production Semantic Core beneath Production Directions

**Status:** Accepted  
**Date:** 2026-08-25

## Context

D-064 correctly restores first-class Production Directions over one shared Studio Core. Its examples, however, place `scenes / shots / characters / locations / takes` under direction-specific production state. Read literally, that can recreate another form of duplication: micro-drama, commercial, music-video and dub-battle production all need overlapping semantic concepts such as shots, takes, subjects/characters, source scenes, accepted material and continuity relationships.

That would miss the strongest LocalMiniDrama-derived idea: UV Studio should understand **what is being produced**, not merely which files sit on a timeline. The timeline is the assembly authority, while production semantics describe scenes/shots/takes and their intent, references, candidates and accepted results.

The shared semantics must not become a giant mandatory film schema. A free project may use none of them; a commercial may use Shots/Takes without Story; a music video may organize Shots under Music Map sections; a dub battle may use source Scene/Characters/Takes with dialogue/cast extensions.

## Decision

Insert a **shared Production Semantic Core** between Production Direction composition and the lower Studio editing/execution core.

```text
Project
  |
  +-- Production Direction
  |     organization / navigation / policy / Agent context
  |
  +-- Shared Production Semantic Core (optional entities)
  |     Sequences / Scenes
  |     Shots
  |     Takes / Candidates / Accepted Take
  |     semantic references / bindings
  |     continuity / canon links
  |     production-to-asset / production-to-timeline links
  |
  +-- Direction Extensions
  |     micro-drama: story / characters / locations / dramaturgy
  |     commercial: brief / product / brand / audience / concepts
  |     music video: song / Music Map / sections / visual direction
  |     narrated: script / narration / semantic segments
  |     dub battle: source scene / dialogue / cast / mix policy
  |
  +-- Shared Studio Core
        Media / Assets
        Preview / Canvas
        Inspector / AI Tools / Model Picker
        Canonical Timeline
        Studio/Application Commands
        Project Unit of Work / Undo-Redo
        Jobs / Generations
        Agent
        Export
```

### 1. Common production entities are common contracts

When multiple directions need the same semantic concept, they MUST reuse one UV-owned contract rather than create direction-specific parallel versions.

The first shared primitives should be deliberately small and composable. At minimum the architecture must support:

- `Scene`/`Sequence` where a production has scene grouping;
- `Shot` as a semantic production unit independent from a timeline clip;
- `Take`/candidate material for a Shot;
- explicit accepted-take identity;
- references from production entities to project-owned assets/generations;
- optional continuity/canon relationships;
- projection/binding from accepted production material to canonical Timeline clips.

A direction is free not to instantiate a primitive it does not need.

### 2. Direction extensions organize, not fork, the core

A Production Direction may add its own versioned documents and policies, but it must reference shared semantic identities when the underlying concept is shared.

Examples:

- a commercial Product Shot and a micro-drama Shot use the same base Shot identity/Take lifecycle, with different extension metadata;
- a Music Map section may group/link shared Shots rather than define a second shot system;
- dub-battle recording Takes may reuse the same candidate/accepted-take lifecycle with dialogue/cast-specific metadata.

Avoid over-generalizing distinct concepts only to make schemas look uniform. Share only semantics that are genuinely common.

### 3. Timeline remains assembly authority, not production meaning

A Timeline Clip answers where media is assembled in time. A Shot answers production intent/context and which Take was accepted. They are related but are not the same object.

```text
Shot 12.3
  -> intent / refs / continuity
  -> candidate takes
  -> accepted take #4
  -> project-owned asset
  -> Timeline clip(s)
```

There is still only one canonical Timeline. The Production Semantic Core is not a second timeline.

### 4. Project Unit of Work spans both layers

The application transaction boundary must coordinate semantic production state and assembly state atomically.

Representative operation:

```text
AcceptTake(shot_12_3, take_4)
  -> accepted take
  -> Shot state
  -> asset/reference registration
  -> Timeline projection/update
  -> undo transaction
```

This remains the required shape for the next application-transaction foundation.

### 5. Production Direction identity must be a typed invariant

D-064 correctly separates `direction_id` from compatibility `recipe_id`, but the current implementation stores Studio identity in generic `extensions` JSON and writes `schema_version: 2` as part of the initial Studio-v2 extension.

The next foundation slice must define a typed Studio metadata contract with an independently meaningful schema version. A schema-version number versions the metadata contract; it must not merely mirror the marketing/architecture label “Studio v2”. The literal `2` in the D-064 example is therefore illustrative current implementation data, not a permanent normative version requirement.

Modern Studio projects must have a known valid direction identity. Legacy recipe projects may remain readable/editable through an explicit compatibility mode without silently pretending to have a modern direction. Direction-specific domain commands require a valid modern identity or an explicit migration/upgrade operation.

### 6. Storage remains file-first and optional

Shared production semantics should live in versioned project-owned documents under a deliberate production/domain root or equivalent bounded Project Store layout. Do not inflate `project.json` with every possible entity.

Archive/import, path security, integrity and rollback rules apply exactly as for other canonical state.

## Consequences

- Micro-drama remains the first rich direction used to prove the scene/shot/take model, but it does not own those common primitives forever.
- Later commercial/music/dub-battle work reuses shared Shot/Take/asset/timeline semantics instead of building parallel systems.
- Direction-specific documents stay meaningful and specialized without multiplying common identities.
- Agent reasoning can use one semantic production vocabulary across directions while still receiving direction-specific context/policy.
- The first Stage-11 transaction work must be generic enough for shared production documents, not only timeline files.

## Relationship to earlier decisions

- **D-064 remains the product-composition authority.** D-065 refines how overlapping direction-domain semantics are factored beneath it.
- **D-063 remains useful for the shared Studio/application infrastructure** but not for its earlier generic-editor overcorrection.
- **D-033 remains the editor/timeline engine foundation.** Production semantics do not create a second canonical timeline.
- Recipe/Product-Orchestrator/Stage models remain compatibility only.
