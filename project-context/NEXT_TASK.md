# Next Task

<!-- uv-next-slice: architecture-hardening-execution-truth -->

## Goal

After the intent-first product journey is accepted, remove the remaining parallel product truth around legacy project execution planning and compatibility tails.

## Required direction

- inventory real consumers of `/api/uv/projects/{project_id}/execution-plan` and `uv_studio/recipes/execution.py`;
- treat the intent-first application/product projection and Product Orchestrator actions as the modern product-facing authority;
- do not modernize two competing execution models in parallel;
- if compatibility consumers still exist, derive the legacy response from modern project/orchestrator truth behind an explicit compatibility boundary;
- otherwise retire the legacy endpoint and its obsolete contract/tests together;
- prove whether the `vendor/videoclaw-app/backend` `sys.path` injection is still needed and remove it if no supported path depends on it;
- retire unrouted donor-era frontend code instead of translating or modernizing it;
- replace the dangerous "reset frontend to pinned VideoClaw baseline" maintenance path with provenance/diff-only donor comparison;
- preserve Project Store, D-017 authorization, Capability Registry selection and editor command ownership;
- add focused regression evidence that there is one modern product truth after the slice.

## Completion proof

The slice is complete when supported product paths no longer depend on an independently maintained legacy execution truth, compatibility behavior is explicit where still required, VideoClaw is reduced toward provenance-only donor status, and permanent CI passes on the exact Review head.

## Entry gate

Begin only from idle `main` after `product-architecture-intent-first-creation` is reviewed, merged and lifecycle-closed.
