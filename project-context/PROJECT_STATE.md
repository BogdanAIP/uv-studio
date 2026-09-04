# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: execution-plan-retirement -->

**Updated:** 2026-09-04

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

Lifecycle-closed `main` is `af9ff888145661381caaacdec78244637058bce2` after `recipe-entrypoint-retirement` PR #91 and D-038 closure PR #92. The accepted D-070 handoff is now opened as bounded Draft PR #93, `execution-plan-retirement`, on branch `chore/execution-plan-retirement` from that exact base.

## Accepted baseline

Modern project creation is Production Direction -> Studio Project. Public recipe catalog/creation/rebinding entrypoints are retired. Old/imported recipe projects remain readable through explicit compatibility identity, and the internal Recipe Registry remains temporarily available to compatibility consumers that have not yet been retired.

`/api/uv/projects/{id}/execution-plan` is still a legacy recipe-derived projection implemented in `uv_studio/api/execution.py`; `frontend/lib/projectsApi.ts` still exposes `getProjectExecutionPlan()`. D-070 classifies these as the next bounded retirement target, with supported readiness moving to direct canonical Production / Generation / Capability authorities rather than another recipe-like plan.

## Active slice gate

No runtime/frontend/test behavior has been changed for this slice yet. Fresh bootstrap was reconstructed from exact lifecycle-closed `main`, including current AGENTS.md, repository skill discovery, D-064/D-065/D-067/D-070, current architecture/map, roadmap and upstream authority.

The repository skill set contains only `.agents/skills/code-review/SKILL.md` v1.0, whose trigger is the later independent review phase; it does not govern Draft implementation.

Before implementation, this Draft must first pass `development-context`. Then the slice must exact-scan every runtime/frontend/test caller of the execution-plan endpoint/client, classify which callers are supported versus compatibility-only, and widen `write_scope` only for proven affected paths.

## Handoff

Finish only `execution-plan-retirement` in this PR. Preserve Product Orchestrator, broad legacy `/projects/{id}` migration, Stage8 retirement and unrelated compatibility surfaces for their separately accepted D-070 slices.

After a fully green implementation head, refreeze lifecycle/context to `review`, mark the PR Ready, obtain a genuinely fresh ordinary-ChatGPT semantic review under `.agents/skills/code-review/SKILL.md` v1.0, require final exact-head CI, merge exact reviewed HEAD, then perform D-038 closure to `idle` before the next slice.
