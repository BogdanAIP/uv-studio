# Next Task

<!-- uv-next-slice: legacy-direction-tool-migration -->

## Target

Bootstrap the first bounded D-070 legacy direction/tool migration slice from lifecycle-closed `main` after merged `execution-plan-retirement` PR #93 (`c8915e2aede2125136080156513ffc3bd4727038`).

## Starting state

The repository is `idle`. Recipe public entrypoints and the recipe-derived execution-plan surface are retired. The accepted migration map still preserves Product Orchestrator, internal Recipe Registry, legacy `/projects/{id}` compatibility and Stage8 until their own bounded caller migrations are proven.

## Required next work

1. Freshly inspect lifecycle-closed `main` and the accepted D-070 inventory.
2. Reconstruct exact live callers for legacy direction/tool composition paths; do not use zero GitHub Code Search results as absence proof.
3. Select one bounded responsibility group for the next slice and record exact write scope before product changes.
4. Preserve modern `Production Direction -> Studio Project`, canonical Project/Production/Timeline/Generation/Capability authorities, old/imported project recovery and Stage-18 mutation fences.
5. Move useful domain responsibility/state to modern Studio/domain authorities rather than deleting it with legacy composition.
6. Keep Product Orchestrator retirement, broad Stage8 retirement and the `micro_drama` golden vertical separate unless exact accepted evidence makes one independently ready.

## Accepted sequence after PR #93

- bounded legacy direction/tool migration slices;
- contextual-tool extraction slices for remaining dubbing, targeted-edit, continuity and music composition ownership;
- `product-orchestrator-retirement` after supported callers move;
- Stage8 runtime dependency migration / compatibility retirement after persisted-project proof;
- `micro-drama-golden-vertical` when independently provable.

The next concrete implementation slice ID must be chosen from fresh caller evidence, not guessed from the umbrella handoff name.
