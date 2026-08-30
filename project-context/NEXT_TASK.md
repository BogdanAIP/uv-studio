# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Target

Resume the accepted D-070 migration sequence with `project-identity-v2-compat-reader` after the current `actions-hardening` security/process slice is merged and lifecycle-closed.

## Required product scope

- introduce an explicit newer project-schema/identity compatibility boundary without breaking schema-v1 project/archive readability;
- preserve known legacy, known-but-uncreatable and historically unknown schema-v1 recipe identities as compatibility state rather than silently guessing a modern Production Direction;
- migrate supported direct runtime readers of `recipe_id` to typed Studio identity / Production Direction or an explicit compatibility discriminator supplied by the v1 reader before the newest schema can stop depending on `recipe_id` as canonical identity;
- keep source/media/artifact identities and canonical Timeline state stable through migration;
- prove representative modern and unmigrated-v1 export/import round trips;
- keep later recipe entrypoint, execution-plan, Product Orchestrator and Stage8 retirement as separate bounded slices.

## Entry gate

Do not start this product slice until:

1. `actions-hardening` has merged;
2. its D-038 lifecycle closure has returned `main` to `idle`;
3. the repository-level full-SHA Actions policy has been enabled after workflow compatibility is proven, when that setting is available to the repository owner;
4. the mandatory fresh bootstrap is rerun against that new `main`.

## Out of scope

Do not mix GitHub Actions supply-chain work, Ready-for-review connector work, recipe endpoint retirement, execution-plan retirement, Product Orchestrator retirement or Stage8 runtime retirement into the identity compatibility slice.
