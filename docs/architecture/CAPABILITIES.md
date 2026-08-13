# UV Studio Capability Registry

## Purpose

Recipes/workflows depend on provider-neutral semantic capability IDs. `CapabilityRegistry` describes replaceable implementations without making registry metadata itself permission to execute.

```text
Recipe / workflow
  -> semantic capability_id
  -> CapabilityRegistry
  -> CapabilityOffer
  -> SelectionPolicy
  -> execution preparation / D-017 when required
  -> exact adapter
```

## Current model

- `CapabilityDefinition`: semantic operation, operation kind and input/output media kinds.
- `AdapterDefinition`: implementation family such as local FFmpeg, direct MCP or exact native compatibility.
- `CapabilityOffer`: one implementation of one capability with availability, locality, cost class and feature metadata.

Provider credentials and portable project state do not live in these definitions.

## Current implementation families

UV Studio currently has product-owned adapters for, among other operations:

- FFmpeg/FFprobe deterministic media probing/range/edit/render/loudness work;
- MLT editor/timeline projection behind the UV editor adapter;
- direct MCP discovery/execution through explicit bindings;
- exact native VideoClaw Edge TTS compatibility;
- local whisper.cpp speech transcription;
- optional local Argos Translate;
- optional local-cache WhisperX alignment;
- deterministic WebVTT subtitle export;
- browser-preview projection from authoritative rendered artifacts.

Optional runtimes can report `configuration_required`; absence must not trigger hidden installation/download or silent remote fallback.

## Selection and permission

Offer ordering is convenience metadata. It is not authorization.

`local_free_first` may choose only `available + local + free`. Remote/hybrid or paid-capable offers require explicit policies and D-017 consent/cost handling as applicable.

See `CAPABILITY_EXECUTION.md` and decisions D-013 through D-020.

## Project-file boundary

Adapters receive portable project identity/semantic inputs. Any translation to host filesystem paths is owned by the exact adapter/binding and restricted to approved Project Store roots. Generic callers do not receive a raw shell/FFmpeg surface.

## Reuse-first rule

Before adding a new media/editor capability, evaluate mature professional open-source implementations. UV-owned custom code should normally be orchestration, typed contracts, validation and adapters around reusable components rather than a new general-purpose media engine.

## Current gaps

The registry/execution architecture is established; current work is not “build Stage 3 execution”. Remaining work is capability breadth, stronger quality/integrity evidence and later provider additions. The next product hardening slice specifically closes Stage 5 correctness/browser user gates before Stage 6 continuity adds new semantic review/continuity capabilities.
