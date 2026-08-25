# UV Studio Capability Registry

**Status:** CURRENT SUPPORTING TECHNICAL CONTRACT  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064

## Purpose

`CapabilityRegistry` describes provider-neutral semantic operations and replaceable execution offers. It sits **below** Production Directions, Studio tools and the future user-visible Model Registry. Capability metadata answers *how an operation can be executed*; it does not define project identity, production navigation or creative model choice.

```text
Production Direction / Studio Tool / Application Command
  -> optional user-visible Model selection
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
- a future Model Registry may map named creative models onto capabilities/offers, but Capability Registry itself must not hide user-significant model choice.

## Project-file boundary

Adapters receive portable project identity and bounded semantic inputs. Translation to host paths occurs only inside the exact adapter/binding and remains constrained to allowed Project Store roots. Generic callers never receive a raw shell/FFmpeg command surface.

## D-064 boundary

Do not add a RecipeDefinition or Production-Direction-specific capability stack. Directions and tools reuse the same capability layer. New product work should normally flow:

```text
direction/domain intent
 -> Studio/Application Command or Tool Service
 -> Model/Capability selection
 -> bounded execution
 -> project-owned result
```

Stage 12 establishes the application transaction boundary. The next product slice proves shared production semantics in the micro-drama direction; capability breadth is still not the architectural bottleneck.
