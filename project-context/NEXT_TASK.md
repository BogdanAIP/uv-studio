# Next Task

<!-- uv-next-slice: product-usability-class-c-cold-start -->

## Goal

Prove UV Studio from a user-equivalent clean state after Product Truth recovery, without implementation knowledge, hidden workflow-decision seeding, direct Project Store fixtures, or developer-only shortcuts.

## Required direction

- start from a clean user-equivalent configuration/projects state and the normal UV Studio application entry path;
- use only currently advertised recipes and visible product controls for the acceptance journey;
- verify that catalog discovery, project creation, prerequisite guidance, workspace routing and at least representative ready outcomes are understandable without repository knowledge;
- distinguish genuine product defects from missing optional runtimes/providers and report those states truthfully;
- do not bypass Product Orchestrator with direct domain-store writes, hidden API setup, retired pipeline routes or test-only readiness seeding;
- preserve the fail-closed creation catalog established by Product Truth recovery;
- include recovery behavior for an existing/imported project where useful, but do not turn compatibility preservation into a new-workflow claim;
- collect durable browser/user-outcome evidence suitable for comparing a clean-state user journey on Ubuntu/CI with the later installed Windows human-acceptance gate;
- keep all five permanent CI checks green on exact Draft and Review heads.

## Completion proof

The slice is complete when a clean-state user can discover an advertised task, create a project, understand what is required, reach representative supported outcomes through visible controls only, and receive truthful guidance for unavailable/configuration-required cases. Exact Draft and Review heads must pass all five permanent Ubuntu/Windows CI jobs.

## Entry gate

Begin only from idle `main` after `product-recovery-recipe-workspace-reconciliation` is reviewed, merged and lifecycle-closed. Installed Windows human acceptance remains a separate gate and must not be claimed by this CI-oriented cold-start slice.
