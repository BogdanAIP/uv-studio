# UV Studio Product Surface Audit

> Audit snapshot: shell/navigation findings describe the D-062 baseline. The
> Product Orchestrator foundation removes legacy pipeline/session/task/sandbox
> entries and polling from the normal UV Studio shell.

## Scope

This audit records Stage 8 `main` user-visible behavior that explains why a technically substantial backend can feel non-functional. It covers both the newer UV Project Store/product UI and the still-live VideoClaw shell/pipeline UI.

## 1. The global shell exposes a second, broken product architecture

`frontend/app/layout.tsx` wraps all pages with `AppShell`.

The Stage 8 `AppShell` imports legacy session/task/sandbox functions from `workflowApi` and places these entries in its primary sidebar:

```text
Video-Claw -> /
临时工作台 -> /sandbox
文艺短视频 -> /pipelines/standard
动作迁移 -> /pipelines/action-transfer
数字人口播 -> /pipelines/digital-human
```

The three pipeline routes are real Next pages. Each renders `PipelinePage`, which calls the live `workflowApi.ts` functions for old `/api/pipelines/*`, `/api/tasks`, `/api/models`, `/api/upload_media` and related endpoints.

The current UV-owned FastAPI server does not mount those pipeline/task/model/upload routes.

Classification: **main-navigation entry points into removed backend runtime**.

This is not harmless donor code. A normal user can enter it through the sidebar.

Required recovery: remove/isolate these old entries from the normal shell unless the intended outcome is reimplemented through current UV semantic capabilities/domain actions. Do not remount the complete old backend.

## 2. Two branding/theme systems coexist

The newer project UI is branded UV Studio and uses its own dark product styling.

Legacy pipeline pages render `BrandHeader` with `Video-Claw` branding and `PipelinePage` controls using `bg-white`, gray light borders and light form styling.

Thus the same root application can visibly switch between two products/design systems.

Classification: **live visual/runtime architecture split**.

This gives a second concrete source for the reported “white fields in a dark app” class of experience, separate from the Stage 9 `uv-input` CSS bug found during installed-app review.

Required recovery: one product shell/theme and one product architecture. Legacy pages are not merely restyled; their backend contracts must first be replaced or retired.

## 3. The Projects entry screen promises workflow isolation but does not deliver it

`frontend/app/projects/page.tsx` tells the user:

> Выберите задачу — студия подключит только нужные этапы.

But `/projects/{projectId}` always mounts:

- `ProjectEditor`;
- `SequenceContinuityPanel`;
- `DubbingWorkflowPanel`;
- `DubbingPrecisionPanel`;
- `DubbingSubtitleExportPanel`;
- execution-plan diagnostics;
- archive/recovery controls.

Recipe-specific panels are appended **in addition**.

Consequences:

- Photo -> Video still shows targeted edit, continuity and dubbing concepts.
- Visualizer does too.
- Story/Commercial/Free get preparation UI plus unrelated specialist workflows.
- Music Video gets music panels plus generic edit/continuity/dubbing.

Classification: **cross-workflow leakage / product promise violation**.

Required recovery: Product Orchestrator determines relevant workspaces/next actions. Recipe selection must not merely append more panels to a universal page.

## 4. Recipe selection does not expose readiness

Project creation renders recipes as similar selectable cards without product-level readiness.

Actual truth differs:

- Photo -> Video: real local path;
- Visualizer: real local path;
- Performance/Lip-sync: optional runtime setup required;
- General Video: incomplete current journey;
- Narrated Video: baseline recipe plan advertised an unmounted legacy pipeline;
- Action Transfer: same;
- Digital Human: partial;
- Story/Commercial: preparation state, not complete production.

Classification: **readiness-blind mode selection**.

Required recovery: product catalog/orchestrator visibly distinguishes `ready`, `setup_required`, `partial`, `unavailable` before project creation.

## 5. Project creation has a non-outcome hidden prerequisite

Stage 8 disables `Создать проект` unless:

- title is non-empty;
- a recipe is selected;
- creation is not busy.

A required title is not a production prerequisite yet it manifests mainly as a dead primary button. This was separately exposed by Stage 9 human testing.

Classification: **unexplained primary-action gating**.

Recovery: safe default project identity; visible prerequisites only when they matter to the selected outcome.

## 6. `Производственный интерфейс` is a navigation loop

On `/projects`:

```text
Производственный интерфейс -> /
```

But `frontend/app/page.tsx` redirects `/` to `/projects`.

So the control claims another interface but returns to the current area.

At the same time AppShell itself labels `/` as `Video-Claw`, creating contradictory expectations: the sidebar says `/` is the old product, while the route redirects to the new projects surface.

Classification: **dead-end / split-navigation semantics**.

## 7. Historical native-execution CTA also loops instead of executing

The Stage 8 project page conditionally showed:

```text
Открыть существующие производственные инструменты -> /
```

For baseline `narrated_video` and `action_transfer`, execution plans claimed `AVAILABLE`, but this CTA neither invoked the advertised `/api/pipelines/*` target nor navigated to the actual `/pipelines/*` legacy page; it simply redirected to projects.

Recovery already removes the false base `AVAILABLE` state for those recipes.

Classification: **advertised execution without a valid UI action**.

## 8. The directly linked legacy pipeline pages are broken for a different reason

Unlike the CTA above, AppShell’s `/pipelines/*` links do reach real pipeline pages. But those pages call APIs that current `uv_studio/server.py` does not provide.

So Stage 8 simultaneously has:

```text
UV recipe metadata -> claims legacy target available
project CTA        -> loops to /projects
AppShell pipeline  -> reaches legacy page
legacy page        -> calls removed backend API
```

This is a complete product-truth split across metadata, navigation, frontend and backend.

## 9. Targeted edit is real but exposes internal state machine

`ProjectEditor` genuinely supports source import, preview, timeline/range selection and a semantic range command.

The main change action is disabled until:

1. a source exists;
2. a valid range is selected;
3. change text is non-empty.

Then the UI exposes durable domain sequence:

```text
Brief -> Plan -> Candidate -> Review -> Accepted -> Render
```

Those states are valuable for safe/reviewable production, but the default user journey should read more like:

```text
Choose fragment -> Describe change -> Prepare result -> Preview -> Accept -> Export
```

Classification: **real backend workflow with frontend-owned prerequisite/state-machine interpretation**.

Recovery: preserve domain model; project it through Product Orchestrator prerequisites/next actions.

## 10. Execution-plan status is not product readiness

`/execution-plan` combines:

- recipe compatibility target planning;
- Stage 8 capability readiness projection for Photo/Visualizer/Performance.

Capability-driven modes can be `available` with `target=null`, which is valid lower-level semantics. Therefore `compatibility` cannot be the main product readiness concept.

Recovery: Product Orchestrator separates:

- readiness;
- prerequisites;
- relevant workspaces;
- next actions;
- capability/runtime diagnostics.

## 11. Current surface/backend ownership summary

| Surface | Backend truth | Main problem |
|---|---|---|
| global AppShell legacy sidebar/tasks | old session/task/pipeline APIs mostly absent | normal navigation into dead runtime |
| `/pipelines/*` | pages exist; required old backend routes absent | broken execution + second design system |
| `/projects` | strong Project Store | readiness-blind recipe selection |
| targeted edit | strong edit/replacement/render domain | internal state machine exposed |
| dubbing | substantial real domain/capability path | globally mounted + setup burden |
| continuity | real optional policy | globally mounted when irrelevant |
| Music Video | substantial real workflow | low-level manual authoring + unrelated panels |
| Photo -> Video | real local capability | good flow polluted by global shell/panels |
| Visualizer | real local capability | good flow polluted by global shell/panels |
| Performance Lip-sync | real optional verified path | setup should be shown before entry |
| Story/Commercial | real brief/script/material prep | promise exceeds complete journey |
| Narrated/Action Transfer | baseline plans claimed unmounted pipeline targets | false readiness repaired fail-closed |

## Recovery acceptance rules

1. Main navigation must not expose runtime surfaces whose backend contracts are absent.
2. Do not restore the old backend merely to satisfy old frontend callers.
3. Mode selection must expose truthful readiness before project creation.
4. Selected recipe/orchestrator state controls relevant workspace visibility.
5. Disabled primary actions must have visible structured prerequisites.
6. Domain state names are progressive/advanced detail, not the default mental model.
7. A visible execution action must call a current UV semantic/domain action or mounted API.
8. One product shell/branding/theme must own the normal experience.
9. Photo -> Video and Visualizer remain reference flows for intent -> inputs -> action -> artifact.
10. Cold-start tests must exercise navigation/readiness and fail on dead legacy entry points rather than only testing known successful domain paths.
