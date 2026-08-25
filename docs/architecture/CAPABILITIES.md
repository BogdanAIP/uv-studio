# UV Studio Capability Registry

**Status:** CURRENT SUPPORTING TECHNICAL CONTRACT  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064 / D-066

## Purpose

`CapabilityRegistry` describes provider-neutral semantic operations and replaceable execution offers. It sits **below** Production Directions, Studio tools and the user-visible Model Registry. Capability metadata answers *how an operation can be executed*; it does not define project identity, production navigation or creative model choice.

```text
Production Direction / Studio Tool / Application Command
  -> user-visible Model selection where meaningful
  -> semantic capability_id
  -> CapabilityRegistry / CapabilityOffer
  -> SelectionPolicy
  -> execution preparation / D-017 when required
  -> exact adapter
```

## Current model

- `CapabilityDefinition` — semantic operation and typed input/output kinds.
- `AdapterDefinition` — implementation family such as local FFmpeg, direct MCP or exact compatibility adapter.
- `CapabilityOffer` — one implementation with availability, locality, cost class and bounded feature metadata.

Credentials, provider secrets and machine-only runtime state do not enter portable project state.

## Current implementation families

The repository has product-owned capability/adapters for deterministic FFmpeg/FFprobe media work, MLT projection behind the UV editor boundary, direct MCP discovery/execution, exact bounded VideoClaw compatibility, local whisper.cpp transcription, optional Argos translation, optional WhisperX alignment, WebVTT export and other tested domain operations.

Optional runtimes may report `configuration_required`; absence must not cause hidden installation, hidden remote fallback or hidden spend.

## Selection and permission

Registry order is convenience metadata, not authorization.

- `local_free_first` may choose only `available + local + free`.
- explicit/pinned selection may target a known offer.
- remote or non-free execution remains subject to D-017 and the exact execution contract.
- the Model Registry maps named creative models onto capabilities/offers without letting Capability Registry hide user-significant model choice.

## Effects visibility for Jobs and Agent policy

D-066 adapts the useful JarvisHub tool-effects pattern into UV's existing command/capability layer rather than creating a parallel tool registry.

Where meaningful, definitions/commands should be able to expose effects such as:

- mutates project state;
- mutates canonical Timeline state;
- generates media;
- destructive;
- long-running;
- reversible;
- cost-bearing.

This metadata is descriptive input for Job orchestration, Agent policy and trace. It is **not** authorization by itself. Existing availability/locality/cost metadata and D-017 remain the execution permission boundary.

## Project-file boundary

Adapters receive portable project identity and bounded semantic inputs. Translation to host paths occurs only inside the exact adapter/binding and remains constrained to allowed Project Store roots. Generic callers never receive a raw shell/FFmpeg command surface.

## D-064 / D-066 boundary

Do not add a RecipeDefinition, Production-Direction-specific capability stack or JarvisHub-style parallel Protocol Bridge. Directions, tools, Jobs and the future Agent Harness reuse the same capability layer.

New generation work should flow:

```text
direction/domain intent
 -> Studio/Application Command or Tool Service
 -> named Model
 -> project Job / Attempt
 -> semantic Capability / Offer
 -> bounded authorized execution
 -> project-owned result + provenance
```

Stage 13 has already proven the shared Scene/Shot/Take production-semantic path. Current next work is the visible Model Registry + retry-safe Job Manager + GenerationContract + first named generation-to-Take-candidate flow described by `project-context/NEXT_TASK.md`.
