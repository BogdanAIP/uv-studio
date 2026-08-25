# D-063 — Studio-first product architecture

**Status:** Partially superseded by D-064  
**Date:** 2026-08-24  
**Current product-composition authority:** D-064

## Decision history

D-063 correctly rejected recipe-by-recipe Product Orchestrator growth as the long-term center and promoted a shared professional Studio Core built on Project Store, canonical Timeline, D-033 MLT adapter, common application commands, Model Registry, Job Manager and capability/adapter boundaries.

It overcorrected in one important place: it treated meaningful top-level production choice itself as the problem and stated that story, commercial, music-video and related concepts should not be normal project identities. D-064 corrects that overreach.

## Clauses that remain accepted

- Project is the canonical product object.
- Project Store and UV-owned project/domain documents remain authoritative.
- D-033 remains the editor foundation; MLT is derived behind a UV adapter and no second canonical timeline is authorized.
- GUI, Agent, scripts and MCP use the same Studio/Application Commands.
- User-significant model choice remains visible through a backend-owned Model Registry.
- Long-running AI execution requires project-scoped Job Manager semantics and provenance.
- Capability Registry / D-017 / adapters remain execution and authorization boundaries, not product identity.
- Open-source/donor reuse remains reuse-first behind UV-owned boundaries.
- Recipe/Stage expansion remains frozen for new product work.
- Compatibility code is removed only after call-site/dependency proof.

## Clause superseded by D-064

New Studio projects **may and should select a first-class Production Direction** when the production type has meaningful domain structure. The problem is not having directions; the problem is implementing each direction as a separate recipe engine/workspace/application.

Current first-class directions are micro-drama/story, commercial/product, music video, narrated video, dub battle/cinematic revoicing and free project.

A Production Direction may own characters, locations, scenes, shots, takes, briefs, products, audiences, Music Maps, dialogue/cast state or other domain documents while sharing the same Studio Core.

Operation-level capabilities such as photo-to-video, visualizer, ordinary dubbing, action transfer, talking character and lip-sync remain contextual tools unless a later accepted decision establishes a separate production model.

## Migration direction retained

Continue the strangler migration: preserve useful targeted-edit/dubbing/music/continuity/media primitives, move supported mutations toward common application commands and Project Unit of Work, add Model Registry and Job Manager, and retire recipe/Product Orchestrator/Stage surfaces only after their callers have moved.

The original full D-063 rationale, target diagram and rejected alternatives remain available in Git history. For current composition use D-064 and `docs/architecture/CURRENT_ARCHITECTURE.md`.
