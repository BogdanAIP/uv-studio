# D-038 — Development context has an explicit idle lifecycle

Status: accepted  
Date: 2026-08-13

## Context

D-023 made active PR state machine-readable, but schema v1 could represent only `draft` and `review`. A squash/merge therefore copied a `review` document onto `main`, leaving an already-merged pull request looking active until the next slice rewrote context. After PR #32 this produced contradictory durable memory: `ACTIVE_SLICE` said Stage 5 review, `NEXT_TASK` said Stage 6, and older backlog/docs still described Stage 4 work.

## Decision

`project-context/ACTIVE_SLICE.json` schema v2 has three lifecycle states:

```text
idle -> draft -> review -> idle
```

Rules:

- `idle`: `active_slice` is `null`; `last_completed` identifies the exact completed slice, pull request and merge commit; one `handoff` remains declared.
- `draft`: one active branch/PR slice is being implemented; PR is draft.
- `review`: implementation/context is frozen for review; PR is non-draft and exact-head checks are authoritative.
- a new slice may start only from an idle `main`;
- after merge, a coordinator performs a mechanical context-closure commit based on the exact merge commit before starting the next slice;
- the closure commit may change only development-memory/history markers required to represent the merge; it is not a feature-development bypass around the one-slice/one-PR rule;
- `tools/close_development_context.py` performs the structured JSON/marker transition and re-runs the repository validator.

`PROJECT_STATE.md` uses an explicit `uv-context-state` marker plus `uv-active-slice` while active or `uv-last-completed` while idle. `NEXT_TASK.md` continues to own exactly one `uv-next-slice` marker.

## Consequences

- `main` no longer needs to pretend an already-merged PR remains active;
- new chats can distinguish current work from the last completed work without consulting old chat history;
- merge identity is durable without trying to store a self-referential current branch head SHA;
- post-merge closure is an explicit required lifecycle operation before the handoff is promoted;
- live diff-vs-write-scope enforcement remains separate future hardening.
