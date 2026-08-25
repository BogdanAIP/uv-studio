# UV Studio Capability Execution

**Status:** CURRENT SUPPORTING TECHNICAL CONTRACT  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064

## Purpose

Capability discovery, model/offer selection, permission and execution are separate concerns.

```text
semantic capability
  -> registry offers
  -> explicit SelectionPolicy / named-model mapping where applicable
  -> ExecutionPreparation
  -> D-017 authorization when required
  -> exact execution adapter
  -> bounded result/provenance
```

Installed software or registry ordering is never permission to contact a service or spend money.

## Selection policies

- `manual` — no automatic offer choice;
- `pinned_offer` — only the named available offer;
- `local_free_first` — only `available + local + free`, never silent remote/non-free widening.

When model identity materially affects the creative result, D-064 requires a user-visible Model Registry/tool choice above this layer; an execution policy must not erase that choice.

## D-017

Remote/hybrid execution requires explicit remote-execution consent. Potentially-paid/paid work additionally requires the applicable external-cost acknowledgement. Grants are short-lived, one-shot, process-local and bound to the exact project/capability/offer/policy/input identity; they are never portable project state.

## Project filesystem boundary

Capability inputs use project identity and bounded project-relative references. Host paths are resolved only inside exact adapters/bindings with allowed roots. Generic public contracts do not expose arbitrary shell commands, FFmpeg flags/filtergraphs or output paths.

## Current adapters

Current tested families include deterministic FFmpeg/FFprobe media operations, MLT-derived editor projection, direct MCP execution through explicit bindings, exact bounded native compatibility, local/optional speech and translation tooling, and deterministic subtitle/export helpers.

MCP execution and D-017 integration are implemented; older discovery-only descriptions are historical.

## Security and product invariants

1. Registry metadata is not execution permission.
2. `local_free_first` cannot silently widen.
3. Remote/non-free work uses D-017.
4. Generic callers do not receive arbitrary host filesystem or command execution.
5. Project-file exposure is operation/binding-owned and root-bounded.
6. External provenance excludes reusable secrets/authorization tokens.
7. Provider/runtime identity does not become canonical product identity.
8. User-significant model identity remains visible above this layer.
9. Generated/reviewed media must be rebound to current project identity before acceptance/materialization.
10. Multi-document acceptance/materialization must eventually commit through Project Unit of Work rather than ad-hoc partial writes.

Historical Stage-5 hardening findings are retained in Git history and tests; they are not the current next-slice definition. Current next work is the application transaction/identity boundary described by `project-context/NEXT_TASK.md`.
