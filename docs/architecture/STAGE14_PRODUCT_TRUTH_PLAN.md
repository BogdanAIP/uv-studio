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

The final slice must add a machine-readable Product Truth Contract that resolves to the actual command/API, frontend entry and browser E2E test. This file is planning context only and must be updated or removed before review if implementation details differ.
