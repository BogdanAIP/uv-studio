# Next Task

<!-- uv-next-slice: stage-6-sequence-continuity-review -->

Updated: 2026-08-13

## Goal

Add optional linked-shot/sequence continuity only where accepted prior state matters, while keeping standalone clips and simple projects free of continuity machinery.

## Required direction

- keep Project Store/domain state canonical;
- represent planned and observed continuity state with typed, versioned, provider-neutral contracts;
- model locks, allowed changes, accepted/rejected takes and re-anchor policy explicitly rather than hiding them in prompts;
- keep GUI, scripts, AI and MCP on the same UV-owned command/workflow boundaries;
- use Capability Registry for optional VLM/generation/review providers and D-017 for remote/non-free execution;
- preserve a human confirmation fallback when automated visual evidence is unavailable or uncertain;
- reuse mature professional open-source components for visual/reference analysis before adding custom general-purpose infrastructure;
- do not force sequence state onto independent one-shot clips.

## Entry gate

Do not start this slice until `stage-5-correctness-browser-e2e` has merged, its post-merge context has returned `main` to `idle`, and the idle closure CI is green.

## Completion proof

Continuity state must survive archive/reopen, distinguish planned from observed evidence, reject stale/rejected take bindings, provide an explicit re-anchor path and prove through UI/tests that simple standalone clips do not inherit sequence complexity.
