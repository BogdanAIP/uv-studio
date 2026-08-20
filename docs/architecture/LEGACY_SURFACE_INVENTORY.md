# Legacy VideoClaw Surface Inventory

> Audit snapshot: the shell findings below describe the D-062 baseline. The
> Product Orchestrator foundation replaces the normal shell with a UV-owned
> projects shell; legacy route/component source remains isolated migration debt.

## Purpose

Stage 3.5 intentionally stopped mounting the complete VideoClaw FastAPI application. This inventory distinguishes the current UV-owned product architecture from legacy VideoClaw surfaces that still remain **inside the live frontend**, not only under `vendor/`.

## Classification rules

- `current_product` — current UV-owned surface backed by mounted UV-owned routes;
- `live_legacy_broken` — compiled/routable live frontend surface that calls backend routes the UV server no longer mounts;
- `compatibility_only` — explicitly retained adapter/migration/test boundary;
- `vendor_donor` — pinned upstream provenance under `vendor/`;
- `stale_contract` — metadata says an execution target is available although it is not mounted;
- `unknown` — requires more reachability/dependency evidence.

## Corrected live-frontend finding

The Stage 8 `main` frontend contains **both architectures at once**.

### UV-owned product layer

Examples:

- `frontend/app/projects/**`;
- `projectsApi.ts`, `recipesApi.ts`;
- `editorApi.ts`, `renderApi.ts`;
- dubbing, sequence, music and Stage 8 API modules;
- Project Store-backed project/editor/task surfaces.

### Live legacy VideoClaw layer

Also present and compiled in the same `frontend/` tree:

- `frontend/lib/workflowApi.ts`;
- `frontend/components/HomePage.tsx`;
- `frontend/components/WorkflowPanel.tsx`;
- `frontend/components/pipelines/PipelinePage.tsx`;
- `/pipelines/standard`;
- `/pipelines/action-transfer`;
- `/pipelines/digital-human`;
- old sandbox/model/session/task UI helpers.

The root layout wraps the application in `AppShell`, and the Stage 8 `AppShell` itself imports `workflowApi` task/session helpers and places the three legacy pipeline routes plus `/sandbox` in the **main sidebar**. Therefore these are not merely orphan source files: the old workflow architecture is part of the normal live shell.

The three pipeline pages render `PipelinePage`, which calls the legacy API client. Their UI also carries separate Video-Claw branding and light `bg-white` controls inside the otherwise UV Studio product, producing a visible second design system.

A pinned donor copy also remains under `vendor/videoclaw-app`, but the problem is not limited to that donor tree.

## Confirmed legacy route families

| Route family | Mounted by current UV server? | Live frontend evidence | Classification | Recovery action |
|---|---:|---|---|---|
| `/api/pipelines/standard/tasks` | No | `workflowApi.startStandardPipeline`, `/pipelines/standard`; baseline recipe plan also advertised it | `live_legacy_broken` + `stale_contract` | recipe plan now fails closed; retire/isolate legacy page rather than remount backend |
| `/api/pipelines/action_transfer/tasks` | No | `workflowApi.startActionTransferPipeline`, `/pipelines/action-transfer`; baseline recipe plan advertised it | `live_legacy_broken` + `stale_contract` | fail closed; later bind current semantic capability workflow if implemented |
| `/api/pipelines/digital_human/tasks` | No | `workflowApi.startDigitalHumanPipeline`, `/pipelines/digital-human` | `live_legacy_broken` | isolate/retire legacy page; current recipe remains partial/capability-gated |
| `/api/tasks*` | No | `workflowApi` task history/status/events/delete; `AppShell` task panels | `live_legacy_broken` | replace product task visibility with UV capability/job state or remove legacy task UI |
| `/api/sessions*` | No | `workflowApi.fetchSessions/deleteSession`; `AppShell` session task panels | `live_legacy_broken` | Project Store remains canonical; remove legacy session authority from shell |
| `/api/models*` | No | `workflowApi.fetchApiModels`; legacy `PipelinePage` model selectors | `live_legacy_broken` | Capability Registry/runtime config remain current authority |
| `/api/pipelines/standard/templates` | No | legacy standard pipeline page | `live_legacy_broken` | do not remount solely for old UI |
| `/api/upload_media` | No | legacy `PipelinePage` media upload | `live_legacy_broken` | current project source APIs remain authority |
| `/api/project/*` | Mostly No | `WorkflowPanel` old start/status/execute/intervene/artifact lifecycle | `live_legacy_broken` | retire/isolate old whole-workflow controller; do not recreate a second project store |
| `/api/sandbox/*` | No | `workflowApi` sandbox task listing; sidebar `/sandbox` | `live_legacy_broken` / security boundary | remove from normal product shell unless rebuilt behind current capability authorization |

`/api/stages` is a special compatibility endpoint still mounted by `uv_studio/server.py`, but its existence does not restore the old project/pipeline runtime.

## Main-shell evidence

Stage 8 `AppShell` defines primary navigation entries for:

```text
/
/sandbox
/pipelines/standard
/pipelines/action-transfer
/pipelines/digital-human
```

It also polls old sessions, pipeline tasks and sandbox tasks through `workflowApi` and constructs links back into those legacy routes.

`frontend/app/layout.tsx` wraps **all pages** in this AppShell. Consequently the new `/projects` product surface was added inside a shell whose navigation/task model still belongs to VideoClaw.

This coexistence is a central Product Truth Recovery finding.

## Current authority replacements

| Concern | UV-owned authority to preserve |
|---|---|
| project identity/persistence | Project Store + `/api/uv/projects*` |
| recipe definitions | Recipe Registry + recipe API |
| execution availability | Capability Registry/selection/authorization + current UV workflow/domain APIs |
| media inputs | project-owned source registration/media APIs |
| deterministic edit/render | editor commands + bounded FFmpeg/MLT adapters |
| dubbing | UV dubbing/editor/prepared-audio/review/render state |
| music video | UV Music Map/Direction/Assembly/Review state |
| provider/runtime choices | Capability Registry + runtime configuration |
| jobs/progress | UV capability/job execution, not historical `/api/tasks` |

## Safety rule

A live broken frontend caller is **not** justification to remount the complete legacy backend. Reintroduction must be an explicit UV-owned adapter/workflow preserving D-017 authorization, secret safety, project path boundaries and provider-neutral canonical state.

## Retirement/isolation procedure

1. enumerate each live legacy route/component/API call;
2. identify whether a current UV-owned replacement already exists;
3. remove it from normal AppShell/navigation first when it cannot execute safely;
4. replace any still-needed user outcome with Product Orchestrator + current domain/capability actions;
5. delete live legacy components only after import/build/tests prove no supported path depends on them;
6. leave the pinned `vendor/` tree as provenance unless a separate dependency decision removes it.

The next Product Orchestrator/UI-isolation work must treat the live legacy shell as an explicit migration target, not as harmless donor residue.
