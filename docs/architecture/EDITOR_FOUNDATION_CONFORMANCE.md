# D-033 Editor Foundation Conformance Audit

## Status

Audit baseline: `main@f7ba7e8d4a9e41294ba8f4104c4330d24e80a93f`  
Active slice: `product-recovery-editor-ownership-resolution` / PR #44  
Decision baseline: D-033 **accepted**

This document checks the implementation against D-033. It does not reopen UV Studio product identity and does not ask which single system should “own the editor”. D-033 deliberately selected a composite architecture.

## Accepted ownership map

```text
User / GUI / Script / AI / MCP
             |
             v
      UV semantic commands
             |
             v
 Project Store / UV domain state    <- canonical
             |
     +-------+--------+
     |                |
     v                v
 MLT adapter      FFmpeg / other adapters
     ^
     |
OpenCut-derived interaction/UI helpers
```

### UV Studio owns

- project identity, source/artifact paths and portability;
- canonical edit/domain state;
- semantic mutation commands and validation;
- acceptance/review/provenance/security invariants;
- conversion to engine representations;
- transaction/undo-redo integration as those product semantics are implemented;
- authoritative final export until another renderer passes the D-033 parity gate.

### MLT owns behind the adapter

- reusable low-level timeline mechanics used by UV;
- playlist/tractor/track and clip mechanics where mapped;
- engine serialization/preview/render primitives where adopted;
- no independent public project authority.

### OpenCut Classic contributes selectively

- suitable MIT editor interaction/UI components and implementation ideas;
- no inherited backend, authentication, project storage or alternate canonical editor store.

## Current implementation map

| Concern | Current implementation | D-033 assessment |
|---|---|---|
| Canonical project | `ProjectStore` + project domain stores | **conforming** |
| Exact targeted-edit intent | `EditorCommandService.select_range()` -> `RangeContinuityBriefStore` | **conforming** |
| Browser playhead/drag selection | React local/transient state in `ProjectEditor` / `RangeTimeline` | **conforming adaptation**; not canonical state |
| Timeline interaction reuse | `RangeTimeline.tsx`, `timelineMath.ts` explicitly adapt pinned OpenCut Classic concepts | **conforming** |
| MLT representation | `MLTTimelineAdapter` derives ephemeral MLT XML from accepted UV edit state | **conforming** |
| Raw MLT mutation access | not exposed through public editor API | **conforming** |
| Accepted edit state | `RangeEditStateStore`, D-028 | **conforming authority** |
| Accepted edit removal | semantic `remove_accepted_edit` -> `EditorCommandService`; `/edits` HTTP surface is read-only | **conformance defect repaired in PR #44** |
| Accepted edit render | UV accepted state -> bounded media render/FFmpeg path | **conforming with D-033 initial export rule** |
| MLT generic mechanics | current product uses MLT mainly as a derived projection/render seam | **incomplete relative to potential Stage 4C breadth**, not evidence that D-033 is wrong |
| OpenCut reuse breadth | selective ruler/playhead/snap interaction reuse | **allowed by D-033**; reuse percentage is not a goal by itself |
| Generic undo/redo | no complete shared product-level proof yet | **incomplete** |
| GUI/scripts/AI/MCP convergence | established for selected semantic/capability paths, not proven for every editor mutation | **incomplete** |

## Important distinctions

### React local state is not automatically editor ownership drift

The browser must hold transient interaction state such as current playhead position, drag handles, unsaved form text and zoom. This is compatible with D-033 as long as durable timeline/edit mutations cross a UV-owned command/domain boundary.

The audit therefore does not classify every React `useState` in the editor as duplicated canonical state.

### Selective OpenCut reuse is intentional

D-033 calls OpenCut Classic a **selective donor**. UV Studio is not required to copy its full editor or state store. A custom UV component is a problem only when it recreates a mature general-purpose primitive without a documented UV-specific reason and without evaluating reusable code.

### MLT does not need to become canonical

MLT XML and in-memory state remain engine representations. Increasing MLT responsibility means routing suitable reusable mechanics through the bounded adapter, not replacing Project Store or allowing callers to mutate MLT project files directly.

### Domain APIs may remain domain APIs

“One command model” does not require collapsing every coherent domain into one giant endpoint. Music Map, Dubbing Review and Replacement Review may keep dedicated UV-owned domain contracts. The prohibited pattern is a privileged route that mutates canonical editor/project state while bypassing the product-owned semantic/domain command boundary.

## First bounded remediation — implemented

Accepted range edits are canonical non-destructive timeline state under D-028. The read API remains appropriate:

```text
GET /api/uv/projects/{project_id}/edits
```

The historical direct mutation was not:

```text
DELETE /api/uv/projects/{project_id}/edits/{edit_id}
    -> RangeEditStateStore.remove(...)
```

PR #44 now:

1. adds typed semantic `RemoveAcceptedEditCommand` and result contracts to `EditorCommandService`;
2. exposes `remove_accepted_edit` through `/api/uv/projects/{project_id}/editor/commands`;
3. validates accepted-edit identity before mutation and preserves project/edit not-found semantics;
4. removes the direct mutating DELETE route so `/edits` is HTTP read-only;
5. adds domain and API regression coverage that proves the canonical state changes only through the semantic command path.

No production frontend call site depended on the removed DELETE route; the current editor client did not expose accepted-edit deletion. The direct route was therefore removable API debt rather than a required UI contract.

This is a D-033 conformance repair, not new NLE functionality.

## Deferred conformance work

The following require separate bounded slices/evidence rather than being silently solved here:

- product-level transaction grouping and undo/redo semantics;
- determining which future multi-track/trim/split/ripple mechanics should delegate more directly to MLT;
- increasing OpenCut-derived UI reuse only where a concrete duplicated primitive is identified;
- proving GUI/scripts/AI/MCP equivalence for each migrated meaningful editor mutation;
- MLT preview/render parity before any change to the authoritative accepted-edit export rule.

These are explicit implementation gaps. They do not block the current recovery from using the already-working bounded targeted-edit path, but generic NLE growth must not outrun them.

## Decision result for this slice

**Reaffirm D-033 with the 2026-08-21 clarification recorded in the decision itself.**

A superseding editor-foundation ADR is not warranted by the current evidence. The implementation has bounded incomplete portions, but the tested composite ownership model remains coherent with UV Studio's product goals and the first concrete mutation bypass has been repaired.

Any future proposal to replace this foundation must include reproducible counter-evidence showing why a specific accepted D-033 boundary cannot satisfy the product. Preference, UI taste or the amount of existing custom code is not sufficient evidence.
