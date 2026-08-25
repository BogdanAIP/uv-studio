# Upstream Sources

## VideoClaw

Repository: `HITsz-TMG/VideoClaw`  
License: MIT  
Pinned commit: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`  
Observed commit date: 2026-07-17  
Imported application subtree: `video-claw/video-claw`

UV Studio intentionally does **not** treat the whole upstream repository as product source. The target baseline is the modern application subtree containing the FastAPI backend, Next.js frontend, current pipelines, model configuration and Windows installer.

## JarvisHub

Repository: `LYL1015/JarvisHub`  
License: Apache-2.0  
Pinned research commit: `6c0f123119d9ffe1a6bae5140721f0b84ea3bbaa`  
Observed commit date: 2026-08-03  
Role in UV Studio: **architecture/method donor for the Agent Harness**, not a vendored application dependency or canonical project-state provider.

The pinned implementation is used as the concrete reference for agent runtime/turn-loop structure, Planner/Tasks, Skills, context/memory compaction, functional subagents, policy/effects, trace, background work, long-running/cost-bearing idempotency and provider-neutral generation constraints. D-066 owns the UV adaptation boundary.

Do not import JarvisHub's Canvas-as-source-of-truth, generic node project model, PostgreSQL/Hono deployment shape or other application-level authority into UV Studio merely because the agent runtime is useful. UV adapts needed patterns behind Project Store, Production Semantic Core, Studio/Application Commands, ProjectUnitOfWork, Model Registry, Job Manager and Capability/Adapter boundaries.

Prefer UV-native reimplementation of the relevant architecture/contracts. If future work directly copies or substantially derives JarvisHub source, preserve the applicable Apache-2.0 license/copyright/NOTICE obligations for that reused material.

## Import policy

- never import from moving `main` without updating the pin through a reviewed change;
- preserve upstream license/attribution obligations for directly reused code;
- use deterministic vendoring tooling for vendored source;
- import only an explicitly configured subtree when vendoring is actually chosen;
- do not silently merge upstream changes;
- compare a candidate new upstream pin against the current pin before updating;
- baseline imported code before cleanup/refactoring.

## Upstream update procedure

For vendored dependencies such as VideoClaw:

1. inspect upstream commits since the current pin;
2. identify changes inside the imported subtree;
3. run baseline/regression tests on a temporary import;
4. document compatibility or required migrations;
5. update the applicable lock/pin and this file;
6. import the new revision in a dedicated PR;
7. never mix an upstream-pin update with unrelated feature work.

For architecture/method donors such as JarvisHub, a pin records the version actually studied. Updating the research pin requires reviewing whether the borrowed contracts/patterns materially changed; it does not imply vendoring or automatic code synchronization.

## Other projects

LocalMiniDrama, ViMax, Jellyfish, DirectorSKILL, `Emily2040/seedance-2.0`, OpenClaw and other researched repositories are not automatically vendored dependencies. They may be used as external runtimes, adapters, or architecture/method donors only after license and integration review.
