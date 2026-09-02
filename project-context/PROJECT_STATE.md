# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-02

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is reopened in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

Fresh ordinary-ChatGPT review of frozen head `a8b9844ccc93a91512f96bf0edc0338070bb694e` returned `CURRENT FINDINGS` with one P2: archive export may call recovery-capable `ProjectUnitOfWork.history()` only after `document`, raw schema version and inventory have already been sampled. A crash-left prepared UOW operation can therefore roll canonical state back mid-export and leave stale sampled archive authority.

## Eighth Draft repair in progress

Repair target: complete UOW prepared-operation recovery under the shared project fence before any archive sampling, then load `project.json`, raw schema version and inventory only from the recovered canonical state. Add deterministic regression for a historical schema-v1 project's first v1→v2 transaction interrupted after after-snapshots/history are written but before the committed marker, proving export rolls back first and produces an importable exact schema-v1 archive.

All previous Stage-19 repairs remain in force, including redo-owned media preservation across restart/archive, prepared-audio and legacy-art orphan recovery, Generation reconciliation/digest authority, explicit Take Undo preservation, publication marker identity, publication fencing and Product Truth behavior.

## Required sequence

1. implement and test the eighth repair while PR #89 remains Draft;
2. require exact-head Draft CI 5/5 on Ubuntu/Windows;
3. synchronize PR body and repository context and resolve the P2 only with concrete CI evidence;
4. refreeze context-only to `review`, mark Ready without changing code, require post-Ready exact-head CI 5/5;
5. run another completely fresh ordinary-ChatGPT semantic review under governing BASE `.agents/skills/code-review/SKILL.md` v1.0;
6. merge only on `CURRENT PASS` with zero findings and clean live base/head/CI/thread identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
