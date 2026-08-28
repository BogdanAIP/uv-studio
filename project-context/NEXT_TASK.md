# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Target

Implement `project-identity-v2-compat-reader` as the next bounded D-070 migration slice.

## Goal

Preserve supported schema-v1 project readability while moving modern callers away from direct legacy `recipe_id` interpretation and toward canonical project/production-direction identity.

## Scope

- inventory remaining live schema-v1 identity readers after donor UI retirement;
- centralize legacy identity interpretation behind an explicit compatibility reader;
- move modern callers to canonical project and production-direction identity where available;
- preserve legacy read/round-trip behavior;
- leave Recipe Registry, Product Orchestrator, `/execution-plan`, Stage 8 and later retirement targets for their planned slices.

## Required proof

- exact caller inventory;
- focused legacy/current identity fixtures;
- no silent identity rewrite or loss of legacy readability;
- context validation and permanent Ubuntu/Windows CI;
- required exact-base/exact-head fresh ordinary-ChatGPT semantic review;
- zero unresolved findings and review threads before merge.

## Out of scope

Do not combine later recipe-entrypoint, execution-plan, Product Orchestrator or Stage 8 runtime retirement into this slice.
