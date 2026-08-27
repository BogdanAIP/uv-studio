# Development Protocol

This is the canonical lifecycle specification for development across chats/agents. `AGENTS.md` is the concise entrypoint.

## 1. Repository is the memory

At the start of every development chat read `AGENTS.md`, `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, decision index/details, architecture principles, roadmap/upstream, then the active PR when one exists and recent `main` commits. Run `python tools/validate_development_context.py` before implementation.

## 2. Lifecycle v2

Development state is:

```text
idle -> draft -> review -> idle
```

`ACTIVE_SLICE.json` owns `lifecycle_state`.

### idle

- `active_slice` is `null`;
- `last_completed` contains exact slice ID, PR number and merge commit;
- one handoff remains in `NEXT_TASK.md`;
- no feature branch is considered active.

A new slice may start only from an idle `main`.

### draft

- create one branch from current idle `main`;
- populate one `active_slice` with branch/base/PR/write scope;
- open one draft PR with exact `uv-active-slice` and `uv-next-slice` markers;
- implementation may evolve.

The first branch commit may temporarily use a null PR number only until the draft PR exists. Update it immediately after PR creation.

### review

- implementation is complete enough for review;
- context/PR body describe actual behavior and limitations;
- `lifecycle_state=review`;
- PR is non-draft;
- exact-head CI and unresolved review state are authoritative.

### post-merge closure

A merge copies the review-state files into `main`, so merge itself is not the final lifecycle state. Before another feature slice begins, the coordinator performs a mechanical closure from the exact merge commit.

When `main` is protected, closure is carried through a dedicated non-draft `chore/*` pull request rather than a direct push to `main`:

1. create `chore/<completed-slice>-lifecycle-closure` from the exact merge commit;
2. on that branch run:

```text
python tools/close_development_context.py \
  --pull-request <merged-pr-number> \
  --merge-commit <40-char-merge-sha>
```

3. keep the closure PR limited to lifecycle/context/protocol corrections required to make protected-main closure executable; it must not contain product implementation changes;
4. use the exact closure marker for the completed slice and keep the current handoff marker:

```text
<!-- uv-lifecycle-closure: <completed-slice-id> -->
<!-- uv-next-slice: <next-slice-id> -->
```

5. keep the closure PR non-draft, target `main`, and use the normal ordered PR sections: Goal, Changes, Verification, Architecture impact, Known limitations, Next task;
6. merge only after the permanent required checks pass and review conversations are resolved.

The helper changes `review -> idle`, sets `active_slice=null`, records `last_completed`, rewrites the `PROJECT_STATE.md` context markers and revalidates the repository. The coordinator also adds the completed slice to `PROJECT_HISTORY.md` when needed.

The idle-state PR exception in `validate_development_context.py` is deliberately narrow: only a non-draft canonical `chore/* -> main` PR with the exact `uv-lifecycle-closure` marker matching `last_completed.id` is accepted. An ordinary feature/change PR cannot use idle state to bypass the normal `idle -> draft -> review` lifecycle.

## 3. One slice = one branch/PR

Prefixes:

- `stage-N/<name>` roadmap work;
- `fix/<name>` defects;
- `chore/<name>` repository/process maintenance;
- `research/<name>` executable evaluation before a durable decision.

Do not mix unrelated implementation into one slice. Temporary worker branches remain subordinate to the single integration PR.

## 4. Context responsibilities

- `ACTIVE_SLICE.json`: lifecycle, active identity, last completed merge, scope, coordination, required checks, one handoff.
- `PROJECT_STATE.md`: as-built product state, verified behavior, risks/gaps. No stale “after PR X merges” future tense.
- `NEXT_TASK.md`: exactly one next target and its completion evidence.
- `PROJECT_HISTORY.md`: compact completed-slice record only.
- `DECISIONS.md`: compact index; durable rationale lives in detailed decision records.
- `ENGINEERING_BACKLOG.md`: only still-open work. Remove/mark completed items instead of letting old future work survive indefinitely.

## 5. Markers

`PROJECT_STATE.md` always contains exactly one:

```text
<!-- uv-context-state: idle|draft|review -->
```

When active it also contains exactly one `uv-active-slice`; when idle it contains exactly one `uv-last-completed`. `NEXT_TASK.md` contains exactly one `uv-next-slice`.

Normal draft/review PR bodies contain:

```text
<!-- uv-active-slice: <id> -->
<!-- uv-next-slice: <id> -->
```

A protected-main post-merge closure PR instead contains:

```text
<!-- uv-lifecycle-closure: <completed-slice-id> -->
<!-- uv-next-slice: <id> -->
```

A closure PR must not contain `uv-active-slice`; a normal active-slice PR must not contain `uv-lifecycle-closure`.

All PR bodies contain exactly these ordered sections: Goal, Changes, Verification, Architecture impact, Known limitations, Next task.

## 6. Review/merge discipline

Before Ready for review:

- code/tests/docs/context agree;
- focused tests pass;
- context validator passes;
- lifecycle is review and PR non-draft;
- exact review head passes every required check;
- unresolved review threads are empty.

Merge using an expected head SHA where tooling supports it. After merge, close context to idle through the protected-main closure procedure before handoff promotion.

## 7. Multi-agent discipline

One coordinator owns Git, integration, context and PR state. Writers receive disjoint paths. Reviewers are read-only. No two writers own the same file concurrently.

## 8. Engineering style

Reuse professional open-source components first; keep provider-specific dependencies behind semantic adapters; keep optional features optional; never silently add paid/remote fallbacks; preserve Windows as a first-class target; do not trade the final architecture for a toy MVP.
