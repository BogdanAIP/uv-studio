# Qwen-MM-Plugins evaluation for UV Studio

**Reviewed:** 2026-08-11  
**Reference repository:** `QwenLM/Qwen-MM-Plugins`  
**Reference commit:** `7dfc08b7de8e621fc28bf9814e3d41a59b4595ae`  
**Upstream license:** Apache-2.0

## Decision

Qwen-MM-Plugins is **not** a replacement for UV Studio and is **not** a mandatory runtime dependency.

Use it in two ways:

1. as a source of strong provider-neutral media-production workflow practices;
2. as an optional MCP capability package for users who explicitly configure the required services.

UV Studio remains responsible for the durable project, recipes, UI, task/artifact history, provider choice, existing-video range workflows, music-specific production logic and final assembly/export.

## Why it is relevant

The upstream project has a mature media-oriented skill/MCP architecture. The most relevant part for UV Studio is its `video-edit` workflow discipline:

- source material is actually reviewed before content decisions;
- editing direction/taste is planned before assembly;
- pacing and audio-first cutting are explicit concerns;
- beat-sync has a dedicated workflow;
- multi-scene work can use a Scene Ledger;
- generated assets follow sample-first rather than blind batch generation;
- plan, scene and final-review gates are mechanically checked;
- final review uses evidence such as timestamps/frame references;
- sound/mix/grading are treated as production work, not afterthoughts;
- approved workflows should not silently downgrade when a tool fails.

These practices should become reusable UV Studio production policies rather than a hard dependency on Qwen models.

## Paid API boundary

The open-source plugin repository does not imply free execution of all AI operations.

At the reviewed revision, cloud model capabilities are separated from local file handling, and paid/configured APIs remain required for major Qwen/Wan/Omni generation/understanding paths.

Examples observed during review include:

- Qwen image generation/editing through DashScope;
- Wan video generation through DashScope;
- Qwen Omni/VL/ASR/segmentation cloud API capability packages;
- dense video-memory embeddings through Qwen/DashScope;
- graph-memory build steps using configured model APIs.

Therefore:

> no baseline UV Studio scenario may require `DASHSCOPE_API_KEY` or another Qwen cloud key when an adequate local/free path exists.

Qwen cloud features may be offered as explicit optional capabilities.

## Local/free parts worth reusing or matching

Relevant provider-independent/local patterns include:

- FFmpeg/ffprobe media probing and preprocessing;
- local file reading/preparation infrastructure;
- media size/FPS/resolution budgeting before model calls;
- deterministic edit routing;
- workflow gates/scripts;
- project-log/ledger patterns;
- BM25 fallback ideas for long-video retrieval;
- MCP packaging and tool schema patterns where useful.

Any copied Apache-2.0 code must retain required attribution/NOTICE obligations.

## Video memory

The hierarchical long-video memory design is technically useful but should not become mandatory Project Store infrastructure.

Potential future optional use:

```text
long source video
  -> temporal/event memory
  -> searchable event hierarchy
  -> retrieve relevant ranges
  -> feed only needed ranges into edit/review workflow
```

UV Studio should keep the interface provider-neutral so local embeddings/VLMs or other services can replace Qwen/DashScope.

## Windows constraint

Qwen-MM-Plugins currently documents WSL2 as the supported Windows path rather than validated native Windows operation.

UV Studio is native-Windows-first, so Qwen-MM-Plugins cannot sit on the required startup path. It can be detected and enabled as an optional WSL/MCP capability.

## Resulting UV Studio architecture

```text
Recipe
  |
  +-- Production Policy
  |     source review / pacing / sample-first / gates / review
  |
  +-- Capability Registry
        |
        +-- local tools
        +-- direct MCP
        |     +-- Qwen-MM-Plugins (optional)
        +-- native VideoClaw adapter
        +-- OpenClaw adapter (optional)
        +-- other provider adapters
```

The recipe and production policy never depend on a specific paid provider.
