# Next Task

<!-- uv-next-slice: product-recovery-dubbing-orchestration -->

## Goal

Project the existing dubbing production chain through Product Orchestrator readiness, prerequisites, relevant workspaces and outcome-oriented semantic next actions without replacing its durable transcript, translation, prepared-speech, alignment, review and render domains.

## Required direction

- preserve the existing D-034–D-037 dubbing domain boundaries and D-017 authorization/provider rules;
- derive readiness and prerequisites from current project-owned media, runtime availability and canonical dubbing state;
- expose understandable user outcomes such as import, transcribe, translate when requested, prepare speech, review, accept and export rather than making internal state-machine objects the primary UX;
- keep transcript/translation/prepared-audio/alignment/review state canonical in their existing stores;
- route the project page from Product Orchestrator `relevant_workspaces` rather than globally mounting dubbing panels;
- do not create a second dubbing workflow store or silently add remote/paid fallbacks.

## Completion proof

The slice is complete when a dubbing project has truthful Product Orchestrator readiness/prerequisites/next actions derived from canonical domain state, the frontend exposes only the relevant dubbing workspace and follows those actions without bypassing review/authorization boundaries, and focused API/browser tests prove setup-gated, transcribed, prepared/reviewed and exportable states.

## Entry gate

Do not begin until `product-recovery-targeted-edit-orchestration` is reviewed and merged, its lifecycle is closed to `idle`, and targeted existing-video editing is routed through Product Orchestrator without weakening D-028/D-032/D-033 invariants.
