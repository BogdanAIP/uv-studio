# Qwen-MM-Plugins evaluation for UV Studio

**Status:** HISTORICAL COMPONENT EVALUATION — not current product architecture  
**Reviewed:** 2026-08-11  
**Reference repository:** `QwenLM/Qwen-MM-Plugins`  
**Reference commit:** `7dfc08b7de8e621fc28bf9814e3d41a59b4595ae`  
**Upstream license:** Apache-2.0  
**Current authority:** [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md) / D-064

## Durable result

Qwen-MM-Plugins is not a replacement for UV Studio and is not a mandatory runtime. It remains useful as:

1. an engineering/workflow donor for source review, pacing/audio-first editing, Scene Ledger ideas, sample-first generation and evidence-based review;
2. an optional MCP capability source for explicitly configured users.

Those ideas belong in Production Direction policies, Studio tools and shared review/command infrastructure — not in a Qwen-specific project model.

## Provider/cost boundary

The open-source package does not imply free cloud execution. Qwen/Wan/Omni/DashScope operations may require configured remote APIs and can never become hidden baseline dependencies. When adequate local/free paths exist, canonical baseline journeys must not require a Qwen cloud key.

Provider-independent/local ideas such as FFmpeg preprocessing, media budgeting, deterministic routing, workflow gates, project ledgers and retrieval patterns may be reused behind UV-owned boundaries with applicable Apache-2.0 attribution obligations.

## Windows boundary

At the reviewed revision, Windows support was documented through WSL2 rather than proven native Windows operation. Therefore this package cannot sit on UV Studio's required native-Windows startup path; it may remain optional.

## Current architecture mapping

The recipe-era diagram from the original evaluation is superseded. Under D-064 the relevant mapping is:

```text
Production Direction / Studio Tool
  -> Studio/Application Command or Tool Service
  -> visible Model selection when significant
  -> Capability Registry
       -> local adapters
       -> direct MCP (optional Qwen-MM package)
       -> other local/remote adapters
```

Production state, provider choice and execution transport remain separate concerns. Git history preserves the full original evaluation text.
