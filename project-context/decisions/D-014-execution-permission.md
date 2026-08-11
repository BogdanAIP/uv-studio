# D-014 — Capability metadata is not execution permission

**Status:** accepted  
**Date:** 2026-08-11

## Decision

UV Studio separates offer discovery from permission to execute it.

```text
Capability Registry
  -> CapabilityOffer metadata
      -> SelectionPolicy
          -> permitted Execution Adapter
```

The registry may report or order an offer, but that does not authorize invocation, remote access or spending.

The initial policies are:

- `manual` — never auto-select;
- `pinned_offer` — select exactly one named available offer;
- `local_free_first` — select only `available + free + local` offers.

`local_free_first` is deliberately fail-closed. It never widens to remote, hybrid, `potentially_paid` or `paid` offers when a local/free implementation is missing.

The first executable adapter is `local_ffmpeg`, and the Stage 3 execution API additionally requires the selected offer itself to be `free + local`. Known remote or paid-capable offers remain metadata-only until a separate adapter and explicit cost/permission flow are implemented.

## Reason

A deterministic preference order is useful for display but unsafe as an execution policy. Without a separate permission boundary, a future unavailable local tool could cause an apparently harmless workflow to fall through to a configured paid service.

The execution layer must also prevent generic media tooling from becoming arbitrary command or filesystem access.

## Consequences

1. Registry ordering is never treated as consent to invoke a provider.
2. Paid-capable and remote offers need their own explicit execution permission path.
3. Local media execution is project-scoped: caller paths are canonical paths inside the current project, not arbitrary OS paths.
4. Path traversal and symlink escape are rejected.
5. FFmpeg/FFprobe use argv subprocesses with `shell=false` and fixed operation-specific arguments.
6. No raw FFmpeg flags or command strings are exposed through the API.
7. `timeline.assemble` currently uses explicit stream-copy concat; incompatible clips fail instead of being silently transcoded.
8. Generated output is registered as a canonical project artifact only after successful execution; metadata-registration failure removes the new output.
9. Qwen-MM-Plugins, OpenClaw and future MCP/provider adapters must obey the same selection/execution boundary.
10. Adding a new adapter must not require changing RecipeDefinition or canonical project semantics.
