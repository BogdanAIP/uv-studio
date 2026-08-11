# Development Protocol

This file defines how UV Studio is developed across chats and by multiple coding agents. `AGENTS.md` is the concise repository entrypoint; this file is the canonical lifecycle specification.

## 1. Repository is the memory

Chat history is not the source of truth. Durable state must live in the repository and GitHub.

At the start of every new development chat, read in this order:

1. `AGENTS.md`
2. `project-context/ACTIVE_SLICE.json`
3. `project-context/PROJECT_STATE.md`
4. `project-context/NEXT_TASK.md`
5. `project-context/DECISIONS.md` and detailed decisions linked from the current state
6. `ROADMAP.md`
7. `UPSTREAM.md`
8. the declared pull request, including its diff, checks and unresolved review threads
9. recent commits on `main`

Then run:

```text
python tools/validate_development_context.py
```

Only after that should development continue. If GitHub shows that the declared pull request has merged, start the one declared handoff target from current `main`; do not continue on the merged branch.

## 2. One development slice = one branch/PR

Branch naming:

- `stage-N/<short-name>` for roadmap work;
- `fix/<short-name>` for defects;
- `chore/<short-name>` for repository maintenance;
- `research/<short-name>` only when executable validation is required before an architectural decision.

Do not accumulate unrelated work in one branch.

Temporary branches used by agents in isolated worktrees may use `work/<slice-id>/<role>`. They are subordinate to the integration branch and do not open separate pull requests to `main`.

## 3. Machine-readable active state

`project-context/ACTIVE_SLICE.json` is authoritative for:

- active slice ID, kind, goal and roadmap stage;
- integration branch, base branch and pull-request number;
- `draft` or `review` phase;
- allowed write scope and coordination policy;
- the required GitHub check names;
- exactly one next-slice handoff ID and its `NEXT_TASK.md` file.

The file intentionally does not contain the current head SHA or check results. A commit cannot contain its own final SHA, and check conclusions are live GitHub state.

The first branch commit may use a null pull-request number while the draft PR does not yet exist. Once the PR is opened, update the number and synchronize the PR body. Before review, change the phase to `review` and make the PR non-draft.

The stdlib-only validator checks the local schema and context markers. During a GitHub pull-request event it also checks the live head/base branches, PR number, draft state, body markers and required sections. Do not bypass a validation failure by weakening the declared state.

## 4. Required end-of-slice state

Before a development slice is considered complete:

- implementation is committed;
- relevant tests/checks are added or run;
- PR body states what changed, what was verified, and known limitations;
- `ACTIVE_SLICE.json` matches the branch, PR, phase and handoff;
- `PROJECT_STATE.md` reflects actual repository state;
- `NEXT_TASK.md` names exactly one primary continuation target;
- durable architectural decisions are recorded and linked from `DECISIONS.md`;
- `UPSTREAM.md` is updated if the upstream pin/import strategy changed.

The exact final PR head must pass every check named in `ACTIVE_SLICE.json`, with no unresolved review thread.

## 5. Context handoff format

Keep each kind of state in one place:

- `ACTIVE_SLICE.json` answers which branch/PR is active, who owns integration, what may change and what gates apply.
- `PROJECT_STATE.md` answers what the product is now, what works, what does not, what was last verified and which architectural risks remain.
- `NEXT_TASK.md` answers what happens after the active slice, which files are expected to change, what proves completion and what is out of scope.
- `PROJECT_HISTORY.md`, decisions, merged PRs and Git history preserve completed detail.

`PROJECT_STATE.md` must not repeat live branch, pull-request, phase or current-head fields owned by `ACTIVE_SLICE.json`. It contains an `uv-active-slice` marker matching the JSON ID. `NEXT_TASK.md` contains an `uv-next-slice` marker matching the JSON handoff ID.

## 6. Decision discipline

Never leave a long-term decision only in chat.

Record decisions using:

```text
D-XXX — title
Status: accepted | superseded | provisional
Date: YYYY-MM-DD
Decision:
Reason:
Consequences:
Supersedes: optional
```

If a later decision changes it, do not erase history. Mark the old decision superseded.

## 7. Multi-agent coordination

One coordinator owns the integration branch, Git index, commits, context files and PR state. Before parallel work begins, it assigns every writer a non-overlapping set of files.

In a shared checkout:

- writers do not switch branches or perform Git mutations;
- only the coordinator edits `project-context/*`;
- writers preserve unrelated changes and report paths, checks and risks;
- the coordinator reviews each diff and executes focused checks before integration.

With isolated worktrees, writers may commit to subordinate `work/<slice-id>/<role>` branches. The coordinator reviews and integrates those commits into the one slice branch. Worker branches never replace the slice PR.

Review agents remain read-only. No two writers may own the same file concurrently. If scopes begin to overlap, stop one writer and reassign the boundary before further edits.

## 8. Development style

- Prefer adapting existing permissively licensed code to inventing new infrastructure.
- Keep optional features optional: music, story, continuity, review, lip-sync, narration.
- Do not create a new subsystem when a recipe/capability adapter is sufficient.
- Do not add a provider-specific dependency to core domain logic.
- Do not silently add paid fallbacks.
- Keep Windows as a first-class development and release target.
- Do not optimize for an MVP by deleting the final product architecture; stages should progressively realize the full target.

## 9. Upstream discipline

UV Studio starts from the modern VideoClaw application, but the upstream relationship must remain explicit.

- Pin an exact upstream commit.
- Preserve MIT notices for imported code.
- Keep a machine-readable/source manifest of imported paths.
- Do not copy historical/demo directories unless required.
- Prefer clean adapters over editing upstream provider implementations everywhere.
- Track upstream changes deliberately; never auto-merge upstream into product code.

## 10. Pull requests

Every PR should include:

- **Goal**
- **Changes**
- **Verification**
- **Architecture impact**
- **Known limitations**
- **Next task**

PRs are the development journal. A future chat should be able to understand why code exists from the PR plus repository context files.

The body must also contain exact machine-readable markers:

```text
<!-- uv-active-slice: <active-slice-id> -->
<!-- uv-next-slice: <next-slice-id> -->
```

In review phase, remove placeholders such as `TODO`, `TBD`, `Still to do` and the exact `replace-with-*` marker values from the PR template. Ordinary domain language such as `replace_range` is valid. Editing the PR body or changing draft state must trigger the development-context check again.

## 11. When a chat is about to end

Before stopping, update the repository first. A prose handoff in chat is secondary.

The minimum safe handoff is:

1. the coordinator collects and reviews all writer diffs;
2. update `ACTIVE_SLICE.json`, `PROJECT_STATE.md` and `NEXT_TASK.md`;
3. commit the current working code on the integration branch;
4. synchronize the PR body and phase;
5. run the context validator and relevant tests;
6. state which exact checks pass on which GitHub head.

This protocol is itself part of the product development process and should be changed only through a reviewed repository change.
