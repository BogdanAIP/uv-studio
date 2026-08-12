# Agent Instructions

These instructions apply to the entire UV Studio repository. The repository and GitHub are the durable project memory; chat history is not.

## Start here

Before changing files, read in this order:

1. `project-context/ACTIVE_SLICE.json`
2. `project-context/PROJECT_STATE.md`
3. `project-context/NEXT_TASK.md`
4. `project-context/DECISIONS.md` and any detailed decisions linked from the current state
5. `ARCHITECTURE_PRINCIPLES.md`
6. `ROADMAP.md`
7. `UPSTREAM.md`
8. the active pull request, including its diff, checks and unresolved review threads
9. recent commits on `main`

Run `python tools/validate_development_context.py` before implementation. If the declared pull request has already merged, use the single handoff target in `ACTIVE_SLICE.json`/`NEXT_TASK.md` to initialize the next slice from current `main`; do not continue on the merged branch.

## Source-of-truth boundaries

- `ACTIVE_SLICE.json` owns the current slice identity, branch, pull request, phase, write scope, coordination policy and required checks. Do not duplicate these live fields in prose files.
- `PROJECT_STATE.md` describes the product as it exists now: capabilities, gaps, last verified result and current risks.
- `NEXT_TASK.md` describes exactly one continuation target after the active slice.
- `PROJECT_HISTORY.md`, decisions, merged pull requests and Git history hold completed detail. Keep historical narration out of `PROJECT_STATE.md`.
- Exact head SHAs and check conclusions are live GitHub facts. Do not store a self-referential current head SHA in `ACTIVE_SLICE.json`.

## Reuse-first and programmable editing

`ARCHITECTURE_PRINCIPLES.md` is mandatory for product implementation.

- Do not build a custom general-purpose editor/media primitive merely because writing one is locally convenient. Search, license-check and technically probe credible open-source implementations first.
- Record a concrete rejection before replacing a suitable mature component with custom code.
- Every meaningful editor mutation must have one programmatic UV Studio command contract. GUI, scripts, AI and MCP call that same command model.
- AI/automation must not mutate canonical project/timeline files directly or bypass the command/domain validation layer.
- Prefer small adapters around mature components over forks or copied subsystems when that preserves upgradeability and license boundaries.

## Slice and Git ownership

- One meaningful slice uses one integration branch and one pull request.
- The coordinator is the only owner of the integration branch, Git index, commits, context files and pull-request state.
- Never switch branches, rebase, merge, cherry-pick, commit, push or modify the Git index unless the coordinator explicitly assigned that Git operation.
- Do not mix unrelated work into the active slice or write outside its declared scope.
- Do not edit `vendor/videoclaw-app` during ordinary product work. Prefer UV Studio-owned wrappers and adapters; a vendor modification requires an explicit durable decision.

## Parallel agents

The coordinator must assign each writer an explicit, non-overlapping file set before work begins.

When agents share one checkout:

- only the coordinator performs Git operations and edits `project-context/*`;
- writers edit only their assigned files and must not revert or reformat unrelated changes;
- writers report changed paths, checks run and unresolved risks;
- the coordinator inspects every diff and runs focused tests before accepting it.

When agents have isolated worktrees:

- each writer may use `work/<slice-id>/<role>` as a temporary branch;
- temporary worker branches do not open pull requests to `main`;
- the coordinator integrates reviewed worker commits into the single slice branch.

A reviewer is read-only: it audits the combined diff, tests, security boundaries, documentation and handoff state, but does not silently repair the files it is reviewing. Never assign two writers to the same file at the same time.

## Completion gate

Before marking a pull request ready:

1. update `ACTIVE_SLICE.json`, `PROJECT_STATE.md` and `NEXT_TASK.md`;
2. synchronize the PR markers and required sections with those files;
3. set the active phase to `review` and make the PR non-draft;
4. run focused tests plus `python tools/validate_development_context.py`;
5. require the exact final PR head to pass every check declared in `ACTIVE_SLICE.json`;
6. confirm there are no unresolved review threads or uncommitted changes.

Long-term decisions must be recorded under `project-context/decisions/` and linked from the decision index. See `DEVELOPMENT_PROTOCOL.md` for the full lifecycle and handoff contract.
