# Agent Instructions

These instructions apply to the entire UV Studio repository. Repository + GitHub are durable project memory; chat history is not.

## Start here

Before changing files, read in this order:

1. `project-context/ACTIVE_SLICE.json`
2. `project-context/PROJECT_STATE.md`
3. `project-context/NEXT_TASK.md`
4. `project-context/DECISIONS.md` and detailed decisions linked from current state — **D-064 is the current product-composition authority; D-063 remains the shared-Studio-core foundation it refines**
5. `docs/architecture/UV_STUDIO_V2_ARCHITECTURE_MAP.md` when present
6. `ARCHITECTURE_PRINCIPLES.md`
7. `ROADMAP.md` (historical stage detail is subordinate to later accepted decisions such as D-064)
8. `UPSTREAM.md`
9. the active PR if `lifecycle_state` is `draft` or `review`, including diff/checks/unresolved threads
10. recent commits on `main`

Run `python tools/validate_development_context.py` before implementation.

## Lifecycle is authoritative

`project-context/ACTIVE_SLICE.json` schema v2 is the machine-readable development-state authority.

- `idle`: there is no active branch/PR slice; `active_slice` must be null. Read `last_completed` and the one handoff, then initialize that handoff from current `main`.
- `draft`: exactly one active implementation slice exists and its PR must be draft.
- `review`: exactly one active slice is frozen for review and its PR must be non-draft.

Never continue work on a merged branch. A new slice starts only from an idle `main`. After a merge, close the merged context to idle before starting the next branch; see D-038 and `DEVELOPMENT_PROTOCOL.md`.

## Source-of-truth boundaries

- `ACTIVE_SLICE.json` owns lifecycle, active branch/PR identity when present, last completed merge identity, write scope, coordination policy, required checks and one handoff.
- `PROJECT_STATE.md` describes the product as it exists now, verified behavior and current risks.
- `NEXT_TASK.md` describes exactly one continuation target.
- `PROJECT_HISTORY.md`, decision records, merged/archived PRs and Git history hold completed detail.
- Exact active-head SHAs/check conclusions remain live GitHub facts.

## Production Directions over one Studio Core

D-064 is mandatory for new product work.

- A UV Studio **Project** is the canonical product object; a **Production Direction** describes how a distinct kind of production is organized above the shared Studio Core.
- Current first-class directions are micro-drama/story, commercial/product, music video, narrated video, dub battle/cinematic revoicing and free project.
- Directions may own domain documents, navigation, production policy and Agent context, but they MUST share Project Store, Studio shell, canonical Timeline, application commands, models/jobs and export infrastructure.
- Do not implement a new direction as a `RecipeDefinition`, Product-Orchestrator execution graph, numbered Stage or separate canonical project engine.
- Operation-level features such as targeted edit, ordinary dubbing/translation, slideshow, visualizer, action transfer, talking character and lip-sync remain contextual Studio tools unless a later decision proves a distinct production model.
- Existing recipe/Product-Orchestrator/Stage 8 code is compatibility/migration material unless a later accepted decision says otherwise.
- User-significant AI model choice must remain visible in the relevant tool. Capability abstraction is an execution boundary, not a reason to hide the model.
- Settings configure connections/runtimes/accounts; Studio tools own per-operation model and creative parameters.
- Agent automation uses the same Studio/Application Commands as manual UI. No Agent-only mutation authority.

## Reuse-first and programmable editing

`ARCHITECTURE_PRINCIPLES.md`, D-033, D-063 and D-064 are mandatory.

- Search/license-check/probe credible professional open-source components before building a general editor/media primitive.
- Record a concrete rejection before replacing a suitable mature component with custom infrastructure.
- Reuse a donor's **needed primitive behind a UV-owned boundary**; do not inherit the donor application's project/workflow model merely because its code is useful.
- MLT remains the selected timeline/editing engine behind the UV adapter; OpenCut Classic remains a selective editor-UX donor. Do not introduce a second canonical timeline engine without a superseding evidence-backed decision.
- Every meaningful editor or production mutation must converge on one UV-owned programmatic command/workflow contract used by GUI, scripts, AI and MCP.
- Automation must not mutate canonical project/timeline/production documents directly or bypass domain validation/D-017/review boundaries.

## Slice and Git ownership

- One meaningful slice uses one integration branch and one PR.
- The coordinator owns the integration branch, Git operations, context files and PR state.
- Writers use explicitly assigned non-overlapping paths; reviewers are read-only.
- Do not edit `vendor/videoclaw-app` during ordinary work; prefer UV-owned wrappers/adapters.
- Closed unmerged research/reference branches are donors only; do not continue implementation on them unless the lifecycle explicitly reactivates them.

## Completion gate

Before marking a PR ready:

1. synchronize implementation, `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, decisions and PR body;
2. set `lifecycle_state` to `review` and make the PR non-draft;
3. run focused tests plus `python tools/validate_development_context.py`;
4. require the exact review head to pass every declared check;
5. confirm no unresolved review threads.

After merge, perform the D-038 context-closure transition to `idle` using the exact merged PR number/merge commit. Only then start the declared handoff.
