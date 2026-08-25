# UV Studio Capability Execution

**Status:** CURRENT SUPPORTING TECHNICAL CONTRACT  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064 / D-066

## Purpose

Model identity, Job/Attempt lifecycle, capability discovery, offer selection, permission and exact execution are separate concerns.

```text
named Model / production intent
  -> GenerationContract where applicable
  -> project Job / Attempt
  -> semantic capability
  -> registry offers
  -> explicit SelectionPolicy / named-model mapping
  -> ExecutionPreparation
  -> D-017 authorization when required
  -> exact execution adapter
  -> project-owned result + bounded provenance
```

Installed software or registry ordering is never permission to contact a service or spend money.

## Selection policies

- `manual` — no automatic offer choice;
- `pinned_offer` — only the named available offer;
- `local_free_first` — only `available + local + free`, never silent remote/non-free widening.

When model identity materially affects the creative result, D-064 requires a user-visible Model Registry/tool choice above this layer; an execution policy must not erase that choice.

## D-017

Remote/hybrid execution requires explicit remote-execution consent. Potentially-paid/paid work additionally requires the applicable external-cost acknowledgement. Grants are short-lived, one-shot, process-local and bound to the exact project/capability/offer/policy/input identity; they are never portable project state.

Job idempotency does not replace D-017. Replaying an idempotent request must not silently manufacture or widen authorization. The Job Manager may reuse already recorded successful output/provenance when the normalized idempotency identity matches, but any new external execution remains subject to the normal permission contract.

## Long-running execution and idempotency

D-066 requires the project Job Manager to protect long-running, cost-bearing or externally mutating execution from duplicate retries/replayed requests.

The UV-native contract must bind an idempotency key to a stable normalized request/context digest covering the project/semantic target, named model, selected execution mapping and generation inputs/contract.

Required behavior:

- same key + materially different normalized request -> conflict/fail closed;
- equivalent work already queued/running -> do not execute a second copy;
- equivalent work already succeeded -> reuse/return recorded result rather than rerun expensive execution;
- deliberate new creative attempt -> receives a new attempt identity rather than masquerading as an infrastructure retry;
- failed/cancelled history remains durable enough for provenance and later Agent trace.

## Generation Contract boundary

A `GenerationContract` is provider-neutral production/execution intent attached to a generation request/attempt, not a provider prompt blob.

It may constrain:

- fixed semantic facts/references;
- explicitly editable variables;
- forbidden semantic changes;
- approved project reference/keyframe identity where applicable.

Provider adapters translate the contract to provider-specific prompt/options. Canonical production identities remain in UV project state.

## Effects visibility

For Job orchestration and future Agent policy/trace, the command/capability layer should expose relevant effects such as project mutation, Timeline mutation, media generation, destructive behavior, long-running behavior, reversibility and cost-bearing execution.

Effects metadata describes risk/behavior. It does not itself grant execution permission or create a parallel JarvisHub-style Protocol Bridge.

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
10. Multi-document acceptance/materialization commits through Project Unit of Work rather than ad-hoc partial writes.
11. Retry/replay of an equivalent long-running/cost-bearing generation must not execute twice.
12. Provider prompt text must not replace provider-neutral semantic generation constraints.
13. Job/Attempt provenance remains historical even if later semantic acceptance is undone.

Stage 13 has completed the shared production-semantics proof. Current next work is the Model Registry + retry-safe Job Manager + GenerationContract + first named generation-to-Take-candidate flow described by `project-context/NEXT_TASK.md`.
