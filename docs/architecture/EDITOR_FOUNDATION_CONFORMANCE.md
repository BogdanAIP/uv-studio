# D-033 Editor Foundation Conformance Audit

**Status:** HISTORICAL CONFORMANCE SNAPSHOT — PR #44  
**Current editor authority:** D-033 plus D-064 / `CURRENT_ARCHITECTURE.md`

This file records the PR #44 audit that reaffirmed the composite editor foundation. It is useful evidence, not a statement of the current active slice.

## Durable conclusions

```text
User / GUI / Script / AI / MCP
             |
      UV semantic/application commands
             |
 Project Store / UV domain state      <- canonical
             |
       +-----+-----+
       |           |
   MLT adapter   FFmpeg/other adapters
       ^
       |
 selective OpenCut UI/interaction reuse
```

UV Studio owns project identity/portability, canonical edit/domain state, semantic mutation validation, review/provenance/security and transaction/undo semantics. MLT supplies reusable engine mechanics behind the UV adapter and is not a public project authority. OpenCut Classic remains a selective MIT interaction/UI donor, not an alternate storage/backend model.

## Important durable distinctions

- React transient playhead/drag/form/zoom state is not automatically duplicate canonical editor state.
- Selective donor reuse is intentional; reuse percentage is not a product goal.
- MLT does not need to become canonical to own useful low-level mechanics.
- Coherent domain APIs may remain separate; “one command model” prohibits mutation bypasses, not domain modularity.

## Historical repair proven by PR #44

The audit identified and repaired a direct accepted-edit mutation bypass: accepted-edit deletion moved behind the shared semantic editor command boundary. The original detailed paths/tests and exact baseline SHA remain available in Git history.

## Current relevance

The gaps identified then that remain architecturally relevant are now handled by the Studio-v2 plan:

- Project Unit of Work and product-level undo/redo;
- broader GUI/Agent/scripts/MCP equivalence;
- appropriate delegation of reusable timeline mechanics to MLT;
- selective donor reuse when a concrete duplicated primitive is found.

D-064 does not supersede D-033. Production Directions sit above one shared editor core; they do not get separate timeline engines.
