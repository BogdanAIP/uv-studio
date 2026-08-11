# PR #16 / Stage 3 Exit Audit

Updated: 2026-08-11

## Purpose

This note records the Stage 3 exit audit while PR #16 is still open. It complements `PROJECT_STATE.md`; it does not claim the PR is merged before exact-head CI is verified.

## Truthfulness issue being closed

The built-in capability registry can advertise:

```text
native_videoclaw.edge_tts -> speech.synthesize
locality = remote
cost     = free
```

as `AVAILABLE` when the optional `edge_tts` dependency is installed. Before PR #16, `/execute` had no `native_videoclaw` transport, so the registry could expose an available offer that was not actually executable.

PR #16 closes that inconsistency with an exact product-owned compatibility adapter. It does not add a generic bridge into arbitrary vendored Python code.

## Stage 3 exit interpretation

Stage 3 is complete for the current roadmap baseline when all of the following are true:

1. Every built-in offer that may be `AVAILABLE` has a real execution family.
2. Local FFmpeg execution is project-scoped, bounded and token-free.
3. Exact MCP execution is gated by explicit bindings, READY discovery state, configuration-drift checks and D-017 authorization where required.
4. MCP project-file translation is binding-owned and cannot expose arbitrary host filesystem paths.
5. Native VideoClaw compatibility execution is exact-offer-only rather than an unrestricted vendor runtime bridge.
6. Remote/cost consent is product-owned and transport-independent.
7. External execution writes durable non-secret provenance and portable project-relative output references.
8. Provider/model offers that still lack exact provider/model/credential contracts remain `CONFIGURATION_REQUIRED` rather than being falsely marked executable.
9. Linux and Windows CI remain first-class merge gates.

Stage 3 completion does not require integrating every optional model provider.

## PR #16 executor contract

Exact executable offer:

```text
native_videoclaw.edge_tts
```

Accepted semantic input:

```text
text
voice
speed
```

Not accepted:

- caller-selected output paths;
- Python module/class/function names;
- arbitrary commands;
- arbitrary vendor pipeline identifiers;
- unrestricted Edge TTS kwargs.

Canonical output:

```text
artifacts/run_<id>.mp3
```

Consent:

```text
remote_execution = required
external_cost    = not required
unknown_cost     = not required
```

## Provenance transition

New external run records use schema v2 with transport-neutral executor identity:

```json
{
  "executor": {
    "kind": "native_videoclaw",
    "identity": {"operation": "edge_tts"}
  }
}
```

MCP records use `executor.kind = "mcp"` and retain top-level `profile_id` / `tool_name` aliases for compatibility. Existing schema-v1 project records are historical data and are not rewritten in place.

## Built-in native offer guard

A regression test is included so that only the exact Edge TTS native offer may become `AVAILABLE` under the current built-in native compatibility family. Other model-backed native VideoClaw offers must remain `CONFIGURATION_REQUIRED` until UV Studio defines exact product-owned provider/model/configuration contracts for them.

## Next roadmap target after merge

If PR #16 passes the exact-final-head Ubuntu/Windows matrix and is merged, development moves to Stage 4 rather than adding providers indefinitely.

First Stage 4 target: provider-neutral precise time-range extraction/editing of an existing project video, with validated source/start/end semantics, bounded local FFmpeg execution, canonical artifacts and portable provenance.
