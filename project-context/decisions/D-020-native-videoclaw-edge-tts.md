# D-020 — Native VideoClaw compatibility execution is exact-offer only

Status: accepted  
Date: 2026-08-11

## Decision

UV Studio may execute selected native VideoClaw compatibility offers directly, but only through product-owned adapters that explicitly whitelist exact semantic offer IDs.

The first executable native compatibility offer is exactly:

```text
offer_id      = native_videoclaw.edge_tts
capability_id = speech.synthesize
adapter_id    = native_videoclaw
locality      = remote
cost_class    = free
```

There is no generic Python module/function dispatcher and no fallback from an unknown `native_videoclaw.*` offer into vendored code.

## Why

The built-in registry already advertised Edge TTS as `AVAILABLE` when its optional Python dependency was importable. Leaving the offer non-executable made registry readiness misleading.

At the same time, using the vendored VideoClaw application as a general execution engine would violate the product-owned capability boundary established by D-008, D-011 and D-013. Native compatibility must therefore be narrow, explicit and replaceable.

Edge TTS also contacts a remote service even though it needs no API key and is catalogued free. D-017 therefore still requires a one-shot `remote_execution` acknowledgement before the adapter is invoked.

## Exact Edge TTS request contract

UV Studio accepts only:

```text
text   required non-empty string, bounded to 20,000 characters
voice  optional non-empty string, default zh-CN-YunjianNeural, bounded to 128 characters
speed  optional positive finite number, default 1.0
```

The adapter preserves the pinned VideoClaw speed-to-rate conversion:

```text
percent = round((speed - 1.0) * 100)
rate    = signed percent string
```

Callers cannot provide an output path, Python symbol, module name, command, arbitrary Edge TTS options or raw provider arguments.

## Project output boundary

UV Studio creates the output identity itself:

```text
artifacts/art_<uuid>.mp3
```

The path is resolved through `ProjectStore` with `allowed_roots=("artifacts",)` and existing outputs are never overwritten.

After successful synthesis, the project receives a canonical `ProjectReference(kind="audio")`. Artifact metadata may include stable capability/offer/voice/speed facts but not the speech text.

If synthesis fails before artifact registration, any partial MP3 is removed. Provider exception text is wrapped in a controlled capability-domain failure.

## External provenance

D-018 external run provenance is generalized at the in-memory target boundary so it can describe MCP and native external execution without changing the existing archive schema version.

Schema v1 intentionally retains historical serialized field names:

```text
profile_id
tool_name
```

Their meaning is transport-neutral at the common provenance layer:

- MCP: configured profile ID + exact bound tool name;
- native compatibility: stable adapter namespace + exact whitelisted operation name.

For Edge TTS these values are:

```text
profile_id = native_videoclaw
tool_name  = edge_tts
```

The run record stores the portable authorization input digest, consent scopes, locality/cost snapshot, status/timestamps and a digest/size summary of the portable result. It does not store authorization tokens, speech text, host filesystem paths or raw remote errors.

A future provenance schema may rename transport identity fields only through an explicit version/migration. This slice does not break existing MCP archive history merely for cleaner names.

## Dependency policy

`edge-tts` is a UV Studio runtime dependency bounded to the currently supported major line:

```text
edge-tts>=7.2.8,<8
```

The adapter still lazy-loads the module and fails truthfully with `CapabilityToolUnavailable` if the installed runtime is incomplete or unavailable.

CI substitutes a deterministic fake `Communicate` implementation and never contacts the live Edge TTS endpoint.

## Consequences

- `native_videoclaw.edge_tts` becomes truthfully executable after D-017 authorization.
- `local_free_first` still cannot choose it because locality is `remote`.
- free does not mean local and does not bypass remote consent.
- all other current native VideoClaw model offers remain non-executable/configuration-required until exact provider/model/credential contracts are designed.
- vendored VideoClaw remains a compatibility/reference boundary, not the UV Studio orchestration core.
- future native compatibility work must add another explicit offer contract rather than widening this adapter into arbitrary function execution.
