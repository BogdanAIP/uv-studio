# Next Task

<!-- uv-next-slice: product-recovery-editor-ownership-resolution -->

## Goal

Re-resolve the D-033 editor ownership boundary before any further generic NLE growth: decide whether UV Studio remains a bounded task-oriented orchestrator/editor, reuses more OpenCut Classic UI primitives, or delegates more timeline behavior to MLT behind UV commands.

## Required direction

- audit the actual post-Stage-8 ownership of timeline state, preview, editing commands and final render;
- compare the accepted D-033 map with the code that now exists;
- evaluate the smallest credible ownership options using current executable evidence and license/deployment constraints;
- preserve Project Store and the one UV command model in every option;
- do not add new generic timeline, waveform, compositor or transition primitives during the decision slice;
- record the selected direction as a new ADR or an explicit D-033 amendment;
- require separate owner approval before implementing a fundamental ownership change.

## Completion proof

The slice is complete when one accepted ownership map states what UV Studio, MLT and any OpenCut-derived UI each own; current deviations are documented; rejected options have concrete evidence; and the next bounded implementation slice can be scoped without ambiguous editor authority.

## Entry gate

Do not begin until Product Orchestrator foundation is merged, its context is closed to `idle`, and the Photo-to-Video reference flow proves that product orchestration can remain separate from generic editor ownership.
