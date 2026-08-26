# Stage 14 Product Truth evidence

`studio-v2-model-registry-job-manager-generation` is the first implementation consumer of D-067.

User-visible feature: named-model generation of a new Take candidate for an existing shared Shot.

Implemented proof chain:

```text
Studio model choice
 -> GenerationWorkspacePanel
 -> POST /api/uv/projects/{project_id}/studio/generation/jobs
 -> GenerationService.submit
 -> project-scoped Job + execution Attempt
 -> GenerationContract + selected execution mapping
 -> project-owned generated media + provenance
 -> shared Take candidate
 -> Studio-visible result/status
 -> existing production.accept_take
 -> canonical Timeline
 -> Undo acceptance while Job/Attempt remains durable
```

The machine-readable contract is:

```text
docs/architecture/product-truth/generate-shot-take.json
```

`uv_studio/product_truth.py` validates the contract deterministically against the real domain class/method, FastAPI route, frontend component/control labels, dependency symbols and declared API/browser test methods. `tests/test_product_truth_contracts.py` makes that validation part of the permanent unit-test suite.

The successful execution proof uses `UV_STUDIO_E2E_TEST_GENERATION=1` and `Stage14E2ETestExecutor`. That transport is explicitly test-only and is absent from the normal model catalog unless the environment gate is set. Normal named models with `configuration_required`/unavailable execution remain visible but blocked with the truthful reason; Stage 14 does not claim an unconfigured provider as runnable.

D-069 continuation lineage is a bounded backend/contract seam inside Stage 14, **not** an additional user-visible feature claim. `continuation_source_reference_id` is accepted only for offers that declare `generation.continuation`, but Stage 14 intentionally ships no real continuation-capable offer, InfinityEdit/Helios runtime or Continue/Edit UI. A later user-visible continuation workflow needs its own Product Truth record and E2E outcome proof.
