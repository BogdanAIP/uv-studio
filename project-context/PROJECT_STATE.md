# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: product-architecture-intent-first-creation -->

**Updated:** 2026-08-24

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

PR #59 remains the single active **Draft**. Its original installed-Windows acceptance goal was deliberately pivoted after real human review rejected the recipe-card-first product concept.

The exact Windows candidate `95f96d3ecde159a1957e8ed56ad8da73d96458f6` remains valuable automated infrastructure evidence only. CI and Stage 9 Release #395 were green, but that build is **not product-accepted**.

## Product decision

The product-facing authority starts from **user intent**, not a technical recipe catalogue.

Primary journey:

1. user describes what they want to create;
2. UV Studio stores that intent as canonical project state;
3. an application service projects a production plan from intent, selected project materials and Capability Registry;
4. each step exposes truthful routes such as manual work, own materials, real generation capability, or local assembly;
5. provider/model/recipe details remain execution concerns behind capabilities;
6. deterministic assembly, review and export remain canonical UV Studio operations;
7. unavailable generation is shown as missing execution, never as a fake completed feature.

Existing recipes, Stage 8 workspace files and legacy panels remain temporarily as execution/compatibility primitives for preserved projects. They no longer define the default new-project UX.

## First intent-first vertical slice now implemented

### Application state

- added `uv_studio.application.CreativeProjectService`;
- new creative projects store `goal`, editable `script`, selected `material_source_ids`, `local_free_first` policy and paid-remote denial under `ProjectDocument.extensions["creative_project"]`;
- the existing `general_video` recipe is retained only as an internal local-assembly primitive;
- one creative preparation save validates exact project-owned source bytes, derives the bounded assembly workspace and commits creative state + execution projection in one `ProjectStore.update_project` write;
- Stage 8 workspace validation was split from persistence so the application layer can coordinate that one write instead of frontend chaining two independent stores/APIs.

### Product plan

`GET /api/uv/projects/{id}/creative-plan` projects one sequence:

- Замысел;
- Сценарий и план;
- Визуальные материалы;
- Голос, музыка и звук;
- Черновая сборка;
- Просмотр и правки.

Routes are derived from Capability Registry locality/cost/availability. Own-material and manual routes are real immediately. Local assembly is the existing verified FFmpeg path. Provider-specific generation is not hard-coded into the product.

### Capability truth

Pinned VideoClaw `text.generate`, `image.generate`, `video.generate` and action-transfer compatibility offers are now `unavailable`, not `configuration_required`, because the current UV Studio build has no authoritative execution transport for them. Edge TTS remains separate because it is actually executable when installed. A real `mcp.*` AVAILABLE offer automatically changes the creative-plan route without provider-specific product code.

### Frontend

- `/projects` no longer displays a recipe catalogue for new projects;
- the user enters one free-form goal and optional project name, then goes directly to `/projects/{id}/studio`;
- new Studio presents one project sequence instead of separate product modes;
- own image/video/audio upload is a route inside the materials step rather than a prerequisite for project creation;
- selected source IDs and order are canonical creative-project state;
- local assembly is surfaced simply as `Собрать ролик`, while `general_video` remains internal;
- old projects continue to open in the compatibility interface without silent migration.

### Browser proof updated

Class C cold-start now proves:

`/ -> /projects -> describe goal -> start project -> /studio -> add material -> save preparation -> local render -> open result`

It explicitly proves no recipe choice, Stage 8 or Product Orchestrator terminology in the clean-state journey. General-video E2E now proves the same Studio reaches the existing verified local master while the internal recipe remains an implementation detail.

## Known incomplete part

A semantic generation capability can be registered and selected, including via MCP and D-017 authorization, but the Studio does not yet invent a generic `prompt -> artifact` payload contract. Therefore an AVAILABLE external generator is reported truthfully, but no fake “Generate” button is wired until its standardized semantic input/output contract is defined and tested.

This is the next product-architecture problem after the current vertical slice passes permanent CI.

## Verification status

- PR #58 Class C remains the last completed lifecycle slice.
- PR #59 remains Draft and unaccepted.
- Release #395 on the pre-pivot head is infrastructure evidence only.
- Current post-pivot commits require fresh permanent CI before any new Stage 9 candidate is built.

Missing `main` branch protection remains intentionally deferred per project direction.

## Next authorized slice

After the intent-first product architecture is reviewed, merged and lifecycle-closed, continue with `architecture-hardening-execution-truth` to remove the remaining independently maintained legacy `/execution-plan` truth and other compatibility tails.
