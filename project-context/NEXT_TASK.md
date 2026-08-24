# Next Task

<!-- uv-next-slice: product-usability-installed-windows-human-acceptance -->

## Goal

Validate the packaged UV Studio application on an installed Windows environment as a real human-facing product gate after Product Truth recovery and Class C clean-state CI evidence.

## Required direction

- use the packaged/installed Windows application rather than the repository development server;
- start from a clean or user-equivalent local application state and launch through the installed product entry point;
- verify first-run startup, project discovery/creation, media import, visible prerequisite guidance, workspace routing and representative supported outcomes;
- confirm that missing optional runtimes/providers are reported as configuration/runtime requirements rather than generic product failures;
- verify recovery/import behavior for a portable project archive without direct Project Store manipulation;
- exercise Windows-specific host, filesystem, path, media-toolchain and desktop-launch behavior that CI browser tests cannot prove;
- collect durable human-acceptance evidence tied to the exact packaged build under test;
- do not reopen unsupported Action Transfer, Digital Human or Performance/lip-sync creation merely to satisfy the acceptance script;
- do not treat this gate as a substitute for later Stage 9 packaging/release hardening.

## Completion proof

The gate is complete when the exact installed Windows build starts cleanly, a user can discover and create supported projects, complete representative local outcomes through visible controls, recover/import a portable project where applicable, and receive truthful guidance for unavailable/configuration-required capabilities. Evidence must identify the exact build/commit and Windows environment used.

## Entry gate

Begin only from idle `main` after `product-usability-class-c-cold-start` is reviewed, merged and lifecycle-closed. This is a human acceptance gate and cannot be completed solely by CI or repository-level browser automation.
