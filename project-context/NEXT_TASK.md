# Next Task

<!-- uv-next-slice: studio-v2-micro-drama-production-semantics -->

## Goal

After `studio-v2-application-transactions` is reviewed, merged and lifecycle-closed, use **micro-drama** as the first rich Production Direction to prove the D-065 shared Production Semantic Core without creating direction-private Scene/Shot/Take infrastructure.

## Required direction

- implement bounded shared `Scene`/`Shot`/`Take`/accepted-take contracts in the canonical `production/` storage established by Stage 12;
- add micro-drama extensions for Story, Characters, Locations and continuity/canon relationships;
- keep a Shot distinct from a Timeline Clip and project accepted production material to the canonical Timeline only through application commands/transactions;
- use the Stage-12 Project Unit of Work for cross-document mutations;
- keep GUI, Agent, scripts and MCP on the same semantic handlers;
- do not add a second timeline, new RecipeDefinition, Product-Orchestrator graph or Stage workspace;
- do not hide meaningful model choice or couple the domain model to one provider.

## Required proof

At minimum prove one user-meaningful flow such as:

```text
Micro-drama project
 -> create Scene
 -> create Shot with intent/references
 -> register multiple Takes/candidates
 -> accept one Take
 -> update shared Shot state
 -> bind accepted project-owned asset
 -> project to canonical Timeline through the transaction authority
 -> undo/redo without split state
```

Commercial, music-video and dub-battle directions must be able to reuse the resulting common Shot/Take contracts later rather than forking them.

## Following direction

After shared production semantics are proven in a real direction, add the backend-owned user-visible Model Registry, project-scoped Job Manager and first named AI generation path through the same application command and transaction boundaries.
