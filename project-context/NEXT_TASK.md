# Next Task

<!-- uv-next-slice: project-store-portable-json-hardening -->

## Goal

Harden the canonical Project Store before Narrated recovery so persisted project state is strict portable JSON and one damaged project cannot make unrelated healthy projects disappear from listing. Keep the change bounded to Project Store/model/import/list semantics; do not mix in Narrated orchestration or Stage 9 packaging.

## Required direction

- recursively validate `ProjectDocument.settings`, `ProjectDocument.extensions` and `ProjectReference.metadata` as JSON-safe values at canonical model boundaries;
- reject `NaN`, `Infinity` and `-Infinity` rather than relying on Python's permissive JSON encoder;
- make canonical writes strict (`allow_nan=False` or equivalent) while preserving atomic-write behavior;
- cover project creation, update/save, archive/import and reopen paths so non-portable nested values cannot enter through another seam;
- isolate malformed/invalid projects during `list_projects()` so healthy projects remain visible;
- preserve corrupt project data for diagnosis/recovery and expose bounded diagnostics/errors instead of silently deleting or rewriting it;
- preserve project ID/path/symlink escape protections and existing migration semantics;
- add focused tests for nested non-JSON/non-finite values plus one-corrupt-project/multiple-healthy-project listing behavior;
- preserve all five recovered Product Orchestrator journeys and all permanent CI checks.

## Completion proof

The slice is complete when canonical project state cannot persist non-portable JSON values, strict save/import/reopen behavior is covered, one corrupt project no longer blocks healthy-project discovery, and exact Draft and Review heads pass all five permanent Ubuntu/Windows CI jobs.

## Entry gate

Begin only from idle `main` after repository-hygiene PR #49 is reviewed, merged and lifecycle closure records its truth/contract cleanup as complete. After this hardening slice merges and returns to idle, `product-recovery-narrated-orchestration` becomes the next product-recovery journey.
