# UV Studio Product Surface Audit

## Scope

This audit records user-visible Stage 8 `main` behavior that explains why a technically functional backend can feel non-functional to a first-time user. It complements `PRODUCT_TRUTH_MATRIX.md`: the matrix classifies execution truth, while this file records concrete navigation, workflow-isolation and prerequisite-presentation defects.

## 1. The entry screen promises workflow isolation but does not deliver it

`frontend/app/projects/page.tsx` tells the user:

> Выберите задачу — студия подключит только нужные этапы.

The actual project page always mounts:

- `ProjectEditor` (targeted existing-video edit);
- `SequenceContinuityPanel`;
- `DubbingWorkflowPanel`;
- `DubbingPrecisionPanel`;
- `DubbingSubtitleExportPanel`;
- execution-plan diagnostics;
- archive/recovery controls.

Recipe-specific panels are added **in addition** to that universal set.

Consequences:

- Photo -> Video still shows targeted-edit, continuity and dubbing concepts.
- Visualizer still shows targeted-edit, continuity and dubbing concepts.
- Story/Commercial/Free projects get their preparation workspace plus unrelated specialist workflows.
- Music Video receives its three music panels plus the same generic editor/continuity/dubbing stack.

Classification: **cross-workflow leakage / product promise violation**.

Required recovery: Product Orchestrator determines relevant workspaces/next actions from recipe + canonical state. A recipe must not merely append panels to a universal project page.

## 2. Recipe selection does not expose readiness

The project creation screen renders every recipe as the same selectable card using recipe title/description/UI metadata. It does not query project-level execution readiness before allowing selection.

Therefore these can look equally ready to the user even though their actual product truth differs materially:

- Photo -> Video: working local path;
- Visualizer: working local path;
- Performance/Lip-sync: optional runtime setup required;
- General Video: incomplete product journey;
- Narrated Video: Stage 8 baseline advertised an unmounted legacy pipeline;
- Action Transfer: Stage 8 baseline advertised an unmounted legacy pipeline;
- Digital Human: partial;
- Story/Commercial: preparation state rather than complete production path.

Classification: **readiness-blind mode selection**.

Required recovery: recipe cards consume Product Orchestrator/catalog readiness and visibly distinguish `ready`, `setup_required`, `partial`, `unavailable` before project creation.

## 3. Project creation has a hidden prerequisite unrelated to the chosen task

Stage 8 `main` disables `Создать проект` unless all of these are true:

- title is non-empty;
- a recipe is selected;
- creation is not already in progress.

The required title is represented only by disabled-button state; it is not a product outcome prerequisite. This was one of the first defects exposed by installed-app human testing on the archived Stage 9 branch.

Classification: **unexplained primary-action gating**.

Recovery direction: project identity can receive a safe default title; important blocking prerequisites should be explicit and task-relevant.

## 4. `Производственный интерфейс` is a navigation loop

On the projects page:

```text
Производственный интерфейс -> href="/"
```

But `frontend/app/page.tsx` contains only:

```text
redirect('/projects')
```

Therefore the control returns the user to the same projects surface instead of opening another production interface.

Classification: **dead-end / misleading navigation**.

Recovery direction: remove the control unless a real destination exists. Do not preserve historical product vocabulary with a loop.

## 5. Historical native-execution CTA also leads to the same loop

The Stage 8 project page conditionally renders this when `executionPlan.can_prepare_native_execution` is true:

```text
Открыть существующие производственные инструменты -> href="/"
```

Again, `/` redirects to `/projects`.

On the Stage 8 baseline this was especially misleading for `narrated_video` and `action_transfer`: their execution plans reported an `AVAILABLE` compatibility target, yet the visible CTA did not call that target and merely returned to the projects page.

The recovery branch already removes the false `AVAILABLE` state for those recipes, so this CTA disappears for them. The underlying UI pattern must still be retired or replaced by Product Orchestrator actions.

Classification: **advertised execution without executable UI action**.

## 6. Targeted edit is real but exposes its internal state machine

`ProjectEditor` provides real source import, video preview, timeline/range selection and a semantic range-selection command. It then mounts replacement and render panels.

The primary `Подготовить изменение` action is disabled until the user has simultaneously supplied:

1. a source video;
2. a valid timeline selection;
3. a non-empty change request.

After that, UI copy exposes implementation/domain sequence:

```text
Brief -> Plan -> Candidate -> Review -> Accepted -> Render
```

Those domain objects are valuable for durable/reviewable production state, but a normal user should primarily see outcome-oriented steps such as:

```text
Choose fragment -> Describe change -> Prepare result -> Preview -> Accept -> Export
```

Classification: **real backend workflow with frontend-owned prerequisite/state-machine interpretation**.

Recovery direction: keep the domain model; project it through Product Orchestrator `prerequisites` and `next_actions`.

## 7. Execution-plan status is not a sufficient product readiness model

`/execution-plan` currently serves two different concepts:

- recipe compatibility target planning;
- Stage 8 capability readiness projection for Photo -> Video, Visualizer and Performance/Lip-sync.

For capability-driven Stage 8 modes, the API can report `compatibility=available` with `target=null`, because the execution path is a semantic capability rather than a legacy/native pipeline target.

That is valid lower-level behavior but makes `compatibility` unsuitable as the primary product readiness concept.

Classification: **semantic overload**.

Recovery direction: Product Orchestrator exposes separate:

- product readiness;
- prerequisites;
- next actions;
- capability/runtime diagnostics.

## 8. Current UI/backend ownership summary

| Product area | Frontend behavior | Backend truth | Main product problem |
|---|---|---|---|
| Projects | creates/opens canonical projects | strong Project Store | readiness-blind recipe selection |
| Targeted edit | interactive source/range/change workflow | strong edit/replacement/render domain | state machine exposed directly |
| Dubbing | multiple specialist panels | substantial real domain/capability path | globally mounted + setup/prerequisite burden |
| Continuity | specialist panel | real optional policy | globally mounted when irrelevant |
| Music Video | map/direction/assembly/review panels | substantial real workflow | manual internal authoring burden + unrelated global panels |
| Photo -> Video | small dedicated panel | real local capability | good reference flow, polluted by global panels |
| Visualizer | small dedicated panel | real local capability | good reference flow, polluted by global panels |
| Performance Lip-sync | dedicated panel | real optional verified runtime path | setup should be projected before entry |
| Story/Commercial | brief/script/material binding | real preparation state | promise exceeds complete user journey |
| Narrated/Action Transfer | recipe selection suggested a mode | Stage 8 baseline execution metadata pointed at unmounted routes | false readiness; fixed fail-closed in recovery branch |

## Recovery acceptance rules derived from this audit

1. No navigation control may point to a route that only redirects back to the current product surface while claiming a different tool/workspace.
2. Mode selection must expose truthful readiness before project creation.
3. A selected recipe must control relevant workspace/action visibility.
4. A disabled primary action must have visible, structured prerequisites.
5. Domain state names are not the default user journey; expose them progressively when review/debugging requires them.
6. A visible execution action must call a current UV-owned semantic action or current mounted API, not historical intent metadata.
7. Photo -> Video and Visualizer remain reference flows for simple intent -> inputs -> action -> artifact behavior.
