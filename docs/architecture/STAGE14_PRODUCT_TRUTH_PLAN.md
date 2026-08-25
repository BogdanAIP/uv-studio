# Stage 14 Product Truth plan

`studio-v2-model-registry-job-manager-generation` is the first implementation consumer of D-067.

Target user-visible feature: named-model generation of a new Take candidate for an existing Shot.

Required proof chain:

```text
Studio model choice
 -> canonical generation command/API
 -> project-scoped Job + Attempt
 -> GenerationContract + selected execution mapping
 -> project-owned generated media
 -> Take candidate
 -> Studio-visible result
 -> existing AcceptTake command
 -> canonical Timeline
```

D-069 continuation lineage is a bounded backend/contract seam inside Stage 14, **not** an additional user-visible feature claim. `continuation_source_reference_id` is accepted only for offers that declare `generation.continuation`, but Stage 14 intentionally ships no real continuation-capable offer, InfinityEdit/Helios runtime or Continue/Edit UI. A later user-visible continuation workflow needs its own Product Truth surface and E2E outcome proof.

The final slice must add a machine-readable Product Truth Contract that resolves to the actual command/API, frontend entry and browser E2E test. This file is planning context only and must be updated or removed before review if implementation details differ.
