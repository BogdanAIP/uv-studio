# D-033 — Reuse-first scriptable editor foundation

Status: proposed  
Date: 2026-08-12

## Decision under evaluation

UV Studio adopts two permanent architecture constraints before implementing the Stage 4C editor workflow.

First, editor/media infrastructure is reuse-first and orchestration-first: a mature, maintained, professional and license-compatible open-source component is integrated before UV Studio writes an equivalent general-purpose primitive. Custom code is reserved for UV-specific orchestration, bounded adapters/integration, or a documented technical gap.

Second, editor mutations use one product-owned Command API. GUI actions, user scripts, AI actions and MCP automation invoke the same command contracts. No caller receives a privileged route that directly mutates canonical timeline/project state.

## Why this needs a spike

The best foundation may be hybrid rather than one upstream application. The candidates have different strengths and license boundaries:

- OpenShot's Qt application is not assumed to be a source-code UI donor; the independently packaged `libopenshot` engine is evaluated on its own terms;
- MLT is evaluated as a separate scriptable editing/render engine;
- OpenCut is evaluated as a reusable editor UX/component source only for capabilities that exist in a pinned revision, not for roadmap promises.

The selection must therefore be based on executable operations, redistribution obligations, Windows feasibility, project portability and the fit with UV Studio's Project Store/domain boundaries.

## Required evidence before acceptance

The spike must record, for each relevant candidate, evidence for these capabilities or an explicit failure/rejection reason:

1. open/probe real source media;
2. create a timeline/edit model;
3. add clips;
4. multiple tracks/layers;
5. move/reposition clips;
6. trim in/out;
7. split/cut;
8. ripple/reorder equivalent;
9. query timeline state;
10. serialize/save portable edit state;
11. reload/round-trip state;
12. accept external programmatic mutations suitable for a UV command adapter;
13. support transaction/undo-redo integration or expose enough state for UV to own it;
14. preview/decode a selected frame;
15. render/export real media;
16. express an exact range-replacement operation without destructive source mutation.

The spike must also record license, maintenance/activity, integration surface, Windows deployment viability and how much custom editor code remains.

## Non-negotiable boundaries

- UV Studio remains owner of Project Store, capability/security authorization, Brief/Plan/Candidate/Review/Accept domain state and canonical product invariants.
- Upstream GUI code is not copied across an incompatible license boundary merely to save implementation time.
- Scripts and AI never mutate raw project files as an alternate editing path.
- Aspirational upstream features do not count until their pinned revision contains an executable interface.

## Acceptance outcome

This decision remains `proposed` until the repository-owned GitHub Actions spike produces reproducible results and the selected foundation is named with its precise ownership/license/adapter boundaries. Stage 4C user-workflow implementation follows only after that result is recorded.
