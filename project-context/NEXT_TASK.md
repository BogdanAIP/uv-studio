# Next Task

<!-- uv-next-slice: product-recovery-narrated-orchestration -->

## Goal

Project the existing `narrated_video` journey through Product Orchestrator readiness, prerequisites, relevant workspaces and semantic next actions after Music orchestration is reviewed, merged and closed to idle.

## Required direction

- reuse existing project/editor, prepared-audio/speech and capability boundaries rather than adding a second narrated workflow store;
- make the narration/script -> speech -> visual plan/assets -> assembly journey explicit from canonical project state;
- preserve D-017 authorization and provider/runtime selection for speech or generative capabilities;
- treat imported/recorded project-owned speech as a valid path where the recipe allows it instead of silently requiring a remote provider;
- route visible product UI from Product Orchestrator state and keep unrelated specialist workspaces out of the narrated journey;
- preserve the recovered Photo, Visualizer, Targeted Edit, Dubbing and Music routes.

## Completion proof

The slice is complete when `narrated_video` has truthful Product Orchestrator readiness/prerequisites/actions, semantic actions reuse canonical project and capability state, the visible UI follows the projected journey, and focused API/browser evidence proves at least one local/project-owned narration outcome plus fail-closed stale/tampered input handling.

## Entry gate

Do not begin until `product-recovery-music-orchestration` is reviewed and merged, its lifecycle is closed to `idle`, and Music Map -> Direction -> Assembly -> Review -> final outcome is authoritative through Product Orchestrator without a duplicate music state store.
