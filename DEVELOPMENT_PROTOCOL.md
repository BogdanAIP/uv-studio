# Development Protocol

This file defines how UV Studio is developed from ChatGPT across multiple chats.

## 1. Repository is the memory

Chat history is not the source of truth. Durable state must live in GitHub.

At the start of every new development chat, read in this order:

1. `project-context/PROJECT_STATE.md`
2. `project-context/NEXT_TASK.md`
3. `project-context/DECISIONS.md`
4. `ROADMAP.md`
5. `UPSTREAM.md`
6. current open PRs and their diffs/comments
7. recent commits on `main`

Only after that should development continue.

## 2. One development slice = one branch/PR

Branch naming:

- `stage-N/<short-name>` for roadmap work;
- `fix/<short-name>` for defects;
- `chore/<short-name>` for repository maintenance;
- `research/<short-name>` only when executable validation is required before an architectural decision.

Do not accumulate unrelated work in one branch.

## 3. Required end-of-slice state

Before a development slice is considered complete:

- implementation is committed;
- relevant tests/checks are added or run;
- PR body states what changed, what was verified, and known limitations;
- `PROJECT_STATE.md` reflects actual repository state;
- `NEXT_TASK.md` names exactly one primary continuation target;
- durable architectural decisions are appended to `DECISIONS.md`;
- `UPSTREAM.md` is updated if the upstream pin/import strategy changed.

## 4. Context handoff format

`PROJECT_STATE.md` must always answer:

- What is the product now?
- Which roadmap stage is active?
- What works?
- What does not work yet?
- What branch/PR contains active work?
- What was last verified?
- What architectural risks remain?

`NEXT_TASK.md` must always answer:

- What should the next chat do first?
- Which files are expected to change?
- What acceptance criteria prove completion?
- What should explicitly not be expanded in that slice?

## 5. Decision discipline

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

## 6. Development style

- Prefer adapting existing permissively licensed code to inventing new infrastructure.
- Keep optional features optional: music, story, continuity, review, lip-sync, narration.
- Do not create a new subsystem when a recipe/capability adapter is sufficient.
- Do not add a provider-specific dependency to core domain logic.
- Do not silently add paid fallbacks.
- Keep Windows as a first-class development and release target.
- Do not optimize for an MVP by deleting the final product architecture; stages should progressively realize the full target.

## 7. Upstream discipline

UV Studio starts from the modern VideoClaw application, but the upstream relationship must remain explicit.

- Pin an exact upstream commit.
- Preserve MIT notices for imported code.
- Keep a machine-readable/source manifest of imported paths.
- Do not copy historical/demo directories unless required.
- Prefer clean adapters over editing upstream provider implementations everywhere.
- Track upstream changes deliberately; never auto-merge upstream into product code.

## 8. Pull requests

Every PR should include:

- **Goal**
- **Changes**
- **Verification**
- **Architecture impact**
- **Known limitations**
- **Next task**

PRs are the development journal. A future chat should be able to understand why code exists from the PR plus repository context files.

## 9. When a chat is about to end

Before stopping, update the repository first. A prose handoff in chat is secondary.

The minimum safe handoff is:

1. commit current working code;
2. update `PROJECT_STATE.md`;
3. update `NEXT_TASK.md`;
4. open/update PR;
5. state whether checks pass.

This protocol is itself part of the product development process and should be changed only through a reviewed repository change.