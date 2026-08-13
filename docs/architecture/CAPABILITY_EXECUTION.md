# UV Studio Capability Execution

## Purpose

Capability discovery, selection and permission are separate concerns.

```text
semantic capability
  -> registry offers
  -> explicit SelectionPolicy
  -> ExecutionPreparation
  -> D-017 authorization when required
  -> exact execution adapter
  -> bounded result/provenance
```

Registry ordering or installed software is never permission to contact a service or spend money.

## Selection policies

- `manual`: no automatic choice.
- `pinned_offer`: execute only the named available offer.
- `local_free_first`: only `available + local + free`; never widen silently to remote/hybrid/non-free.

## D-017

Remote/hybrid execution requires `remote_execution` consent. Potentially-paid/paid execution additionally requires external-cost acknowledgement, and unknown price remains explicitly unknown. Grants are short-lived, one-shot, process-local and bound to project/capability/offer/policy/normalized input digest. They are never portable project state.

## Project filesystem boundary

Capability inputs use project identity and bounded project-relative references. Host paths are resolved only inside exact adapters/bindings with allowed roots. Generic public capability contracts do not expose arbitrary shell commands, FFmpeg flags/filtergraphs or output paths.

## Current execution adapters

### Local deterministic media

FFmpeg/FFprobe operations cover media probing, exact-range mechanics, accepted-edit/dubbing materialization, browser-preview projection and loudness evidence. MLT remains an editor/timeline engine behind a UV adapter, while authoritative final media output remains UV-controlled.

### MCP

Direct MCP uses the official SDK, exact configured `MCPToolBinding`, READY/discovery identity checks and binding-owned project-file translation. D-017 applies to remote/non-free offers. Portable provenance records semantic identity and bounded result facts without persisting authorization tokens or resolved host-only inputs.

### Exact native compatibility

Native VideoClaw compatibility is allowlisted offer-by-offer. Current Edge TTS reuse accepts only the defined speech input contract, writes a UV-owned artifact and requires D-017 remote consent. There is no generic Python dispatch into vendored code.

### Stage 5 local/optional adapters

- whisper.cpp: local/free ASR draft generation;
- Argos Translate: optional local/free translation draft;
- WhisperX: optional heavy local-cache forced alignment draft;
- WebVTT: built-in deterministic subtitle projection.

Draft-producing AI/model operations do not mutate accepted project state automatically; acceptance goes through the corresponding UV-owned review/command boundary.

## Security invariants

1. Registry metadata is not execution permission.
2. `local_free_first` cannot silently widen.
3. Remote/non-free work uses D-017.
4. Generic callers do not receive arbitrary host filesystem or command execution.
5. Project-file exposure is operation/binding-owned and root-bounded.
6. External provenance excludes reusable secrets/authorization tokens.
7. Provider/model/runtime identity does not become canonical project authority.
8. Generated/reviewed media must be rebound to current project identity before acceptance/materialization.

## Current hardening debt

The post-Stage-5 audit identified one important integrity follow-up: when Review/Accept/render trust a stored media SHA, critical boundaries should verify that the current project-owned file bytes still match that identity instead of only comparing historical metadata fields. This is the next Stage 5 hardening slice, not a redesign of the capability layer.
