# Next Task

<!-- uv-next-slice: architecture-hardening-execution-truth -->

## Goal

Remove the remaining parallel product truth around legacy project execution planning after installed Windows human acceptance is complete.

## Required direction

- inventory real consumers of `/api/uv/projects/{project_id}/execution-plan` and `uv_studio/recipes/execution.py`;
- treat Product Orchestrator `/workflow` as the current product-facing authority;
- do not modernize two competing execution models in parallel;
- if compatibility consumers still exist, derive the legacy response from Product Orchestrator/domain truth behind an explicit compatibility boundary;
- otherwise retire the legacy endpoint and its obsolete contract/tests together;
- preserve current Project Store, D-017 authorization, capability selection and editor command ownership;
- add focused regression evidence that there is one modern product truth after the slice.

## Completion proof

The slice is complete when supported product paths no longer depend on an independently maintained legacy execution truth, compatibility behavior is explicit where still required, and permanent CI passes on the exact Review head.

## Entry gate

Begin only from idle `main` after `product-usability-installed-windows-human-acceptance` is reviewed, merged and lifecycle-closed.
