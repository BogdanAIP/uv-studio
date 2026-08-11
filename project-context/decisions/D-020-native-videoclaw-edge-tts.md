# D-020 — Native VideoClaw compatibility is exact, not a generic vendor bridge

Status: accepted  
Date: 2026-08-11

## Decision

UV Studio may execute selected pinned VideoClaw behavior through product-owned native compatibility adapters, but only for exact offer IDs with explicit semantic request/output contracts.

The first executable native compatibility offer is:

```text
native_videoclaw.edge_tts -> speech.synthesize
locality = remote
cost     = free
```

There is no API for a caller to provide a Python module, class, function, command, output path or arbitrary VideoClaw pipeline name.

## Edge TTS contract

The UV Studio request accepts only:

```text
text
voice
speed
```

Product-owned bounds are applied before remote execution. The caller cannot choose an output path. UV Studio creates:

```text
artifacts/run_<id>.mp3
```

inside the canonical project.

The compatibility behavior follows the pinned VideoClaw Edge TTS implementation, which uses `edge_tts.Communicate(text=..., voice=..., rate=...).save(...)`. The pinned vendor requirements currently declare `edge-tts==7.2.7`.

UV Studio does not dynamically import the vendored TTS pipeline by user-controlled name. The product adapter talks to the optional `edge_tts` dependency through a narrow runtime interface, which also makes CI deterministic without live network calls.

## Authorization

Edge TTS contacts a remote service even though the current adapter needs no API key and is classified `free`.

Therefore D-017 applies as:

```text
remote_execution = required
external_cost    = not required
unknown_cost     = not required
```

`local_free_first` remains unable to select this offer because it is not local.

Authorization remains one-shot and bound to the exact portable input digest. Replay and mutated-input reuse fail before native execution.

## Provenance v2

External run provenance is generalized from the MCP-specific v1 shape to schema v2:

```json
{
  "executor": {
    "kind": "native_videoclaw",
    "identity": {"operation": "edge_tts"}
  }
}
```

MCP v2 records use:

```json
{
  "executor": {
    "kind": "mcp",
    "identity": {
      "profile_id": "...",
      "tool_name": "..."
    }
  }
}
```

For compatibility, new MCP v2 records also retain top-level `profile_id` and `tool_name` aliases. Existing v1 project files are immutable history and are not rewritten or migrated in place.

Native success provenance may store only safe project-relative references such as:

```text
artifacts/run_<id>.mp3
```

It never stores the absolute host path or authorization token. Remote failures persist controlled error class/code only, not the raw provider response/body.

## Failure behavior

- missing optional `edge_tts` fails before a network attempt;
- unsupported native offer IDs fail closed;
- invalid semantic input fails before execution;
- partial output is removed after remote/output failure;
- a started run is finalized to success or failure;
- output must exist, be non-empty and remain within the product-owned size bound.

## Other native VideoClaw offers

Model-backed native offers remain `CONFIGURATION_REQUIRED`. Their presence in the pinned vendor tree is not enough to mark them executable.

Before any such offer can become `AVAILABLE`, UV Studio still needs an exact product-owned provider/model/credential/configuration contract and tests proving the execution/cost/locality behavior. This decision does not create a generic VideoClaw provider bridge.

## Reason

The Capability Registry must be truthful: an offer marked `AVAILABLE` must have a real execution path, while optional vendor code must not become an unrestricted execution surface.

A small exact adapter closes the Edge TTS inconsistency without coupling UV Studio recipes to VideoClaw internals or weakening the selection/consent/provenance boundaries already established for MCP.

## Consequences

- `native_videoclaw.edge_tts` becomes genuinely executable when its optional dependency is present;
- remote/free consent semantics are exercised independently of MCP;
- external provenance becomes transport-neutral;
- arbitrary vendored Python execution remains impossible through the capability API;
- model-backed native offers remain honest `CONFIGURATION_REQUIRED` placeholders until independently specified;
- after this slice, Stage 3 can be evaluated against its exit criteria without treating every possible provider integration as mandatory core work.
