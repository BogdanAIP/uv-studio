# Next Task

<!-- uv-next-slice: studio-v2-model-registry -->

## Goal

After application transactions and durable undo/redo are reviewed, merged and lifecycle-closed, add a backend-owned **user-visible Model Registry** for Studio AI tools.

## Required direction

- expose semantic tool categories such as image generation/editing independently from provider transport;
- expose concrete installed/configured model choices to the user in the relevant Studio Inspector/AI tool;
- keep capability/provider/runtime configuration below the product interaction layer;
- map Model Registry choices onto existing Capability Registry / MCP / D-017 execution truth instead of replacing those security boundaries;
- keep model metadata secret-free, portable and backend-owned;
- do not create fake model availability from donor metadata or API-key presence;
- keep Settings for connection/runtime configuration, not ordinary per-action model choice;
- do not add a broad provider matrix in the first registry slice.

## Completion proof

The slice is complete when Studio can query one authoritative backend registry, show truthful model choices for at least the first planned AI tool category, preserve explicit model identity in the project/action request, and fail closed when no executable model is available.

## Following direction

After Model Registry, add a project-scoped Job Manager and then one real named Image AI vertical from Inspector request through execution to a registered project asset.

## Entry gate

Begin only from idle `main` after `studio-v2-application-transactions` is merged and lifecycle-closed.
