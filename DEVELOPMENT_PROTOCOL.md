# Development Protocol

This is the canonical lifecycle specification for development across chats/agents. `AGENTS.md` is the concise entrypoint.

## 1. Repository is the memory

At the start of every development chat:

1. resolve live `main`, the current branch/PR and exact refs;
2. enumerate `.agents/skills/*/SKILL.md` from the current source ref;
3. load every skill whose frontmatter/trigger applies to the current task phase before planning or editing governed work;
4. read `AGENTS.md`, `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, decision index/details, architecture principles, roadmap/upstream, then the active PR when one exists and recent `main` commits;
5. run `python tools/validate_development_context.py` before implementation.

Never rely on remembered skill names or cached skill contents. Repeat skill resolution after `main` advances, a rebase, a new slice, a material scope change or entry into a governed review phase.

A merge does not autonomously start the next slice. The next development invocation resolves repository state and skills again from the new accepted source.

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
- no feature/process branch is considered active.

A new slice may start only from an idle `main`.

### draft

- create one branch from current idle `main`;
- populate one `active_slice` with branch/base/PR/write scope;
- open one draft PR with exact `uv-active-slice` and `uv-next-slice` markers;
- implementation/process work may evolve.

The first branch commit may temporarily use a null PR number only until the draft PR exists. Update it immediately after PR creation.

### review

- implementation/process change is complete enough for review;
- context/PR body describe actual behavior and limitations;
- `lifecycle_state=review`;
- PR is non-draft;
- exact-head CI, required semantic review when applicable, and unresolved review state are authoritative.

### post-merge closure

A merge copies the review-state files into `main`, so merge itself is not the final lifecycle state. Before another product/process slice begins, the coordinator performs a mechanical closure from the exact merge commit.

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
- `PROJECT_STATE.md`: as-built product/process state, verified behavior, risks/gaps. No stale “after PR X merges” future tense.
- `NEXT_TASK.md`: exactly one next target and its completion evidence.
- `PROJECT_HISTORY.md`: compact completed-slice record only.
- `DECISIONS.md`: compact index; durable rationale lives in detailed decision records.
- `ENGINEERING_BACKLOG.md`: only still-open work. Remove/mark completed items instead of letting old future work survive indefinitely.

Keep current operating docs compact. Detailed accepted migration tables belong in their dedicated architecture/inventory owner rather than being duplicated into `PROJECT_STATE.md`.

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

## 6. Independent semantic review and merge discipline

### 6.1 When review is required

After adoption of `.agents/skills/code-review/SKILL.md`, independent semantic review is required for material changes to:

- production/runtime behavior;
- security, authorization, trust or D-017 semantics;
- persistence, recovery, retry or reconciliation;
- concurrency, identity, ownership or provenance;
- canonical Project/Production/Timeline/Generation/Capability authority;
- Agent/GUI/script/MCP mutation boundaries;
- user-visible Product Truth / acceptance behavior;
- tests or CI/physical gates whose semantics define acceptance;
- repository merge/review policy itself.

Documentation-only changes that do not materially alter process/security/acceptance/runtime semantics are not forced through this semantic-review layer beyond normal GitHub review/CI requirements.

The PR that first introduces this policy is governed by the previously accepted merge policy. The new semantic-review requirement governs subsequent review-significant PRs after this policy is merged.

### 6.2 Primary reviewer

The mandatory primary review runs in a separate **fresh ordinary ChatGPT** conversation/context using `.agents/skills/code-review/SKILL.md`.

It must:

- receive only the exact `REVIEW_REQUEST_V1` identity plus neutral task/gate metadata;
- bind review to exact `BASE_SHA..HEAD_SHA`;
- use the accepted review policy/skill from `BASE_SHA` and the review target from `HEAD_SHA`;
- independently fetch diff/code/tests/evidence instead of trusting developer summaries;
- remain read-only;
- build candidate findings and explicitly try to falsify them before reporting;
- return `REVIEW_RESULT_V1` with `PASS | FINDINGS | ABSTAIN | STALE`.

Do not use ChatGPT Work, Workspace Agents, Codex automation or Codex Review as a substitute for the mandatory primary review. A one-time Scheduled Task may launch the review only when the eventual execution can truthfully satisfy `review_context=ordinary_chat_fresh`; otherwise use a manually opened fresh ordinary-ChatGPT conversation.

### 6.3 Codex is optional additional evidence

`@codex review` remains useful when quota is available, but it is not the mandatory review dependency.

Codex quota exhaustion does not block merge when:

- the required fresh ordinary-ChatGPT review is current and valid;
- all reported findings are resolved/validated;
- exact-head required CI/physical gates pass;
- ordinary GitHub review threads are resolved.

Never represent unavailable Codex review as completed.

### 6.4 Finding validation

A reported semantic-review finding is not automatically project truth. The development context classifies every reported finding as:

```text
CONFIRMED
REJECTED
SUPERSEDED
```

- `CONFIRMED`: fix it or keep merge blocked with an explicit disposition;
- `REJECTED`: provide concrete contrary code/test/evidence, not preference;
- `SUPERSEDED`: a later change removed/changed the path; that material change normally makes the old review stale.

Do not merge with unresolved reported findings.

### 6.5 Review invalidation

A semantic review is valid only for the exact reviewed identity.

Any material post-review change to runtime/security/recovery/concurrency/identity/canonical authority/verification/acceptance tests/gates/merge policy invalidates the prior review. A changed merge base likewise requires a fresh exact-base review.

Clearly non-material spelling/formatting-only changes may preserve review validity only after the exact post-review delta is inspected and explicitly classified non-material. When uncertain, review again.

### 6.6 Required order

For review-significant changes use:

```text
required research/design authority when applicable
 -> implementation
 -> focused tests
 -> preliminary hosted CI when useful
 -> freeze BASE_SHA + HEAD_SHA
 -> required fresh ordinary ChatGPT semantic review via code-review skill
 -> optional @codex review when available
 -> validate findings
 -> fix confirmed findings
 -> material fix => prior semantic review stale
 -> fresh required review on new exact head
 -> optional fresh @codex review
 -> final exact-head permanent CI / browser / real-media / physical gate as applicable
 -> verify reviewed BASE_SHA + HEAD_SHA still match PR
 -> unresolved semantic findings = 0
 -> unresolved GitHub review threads = 0
 -> merge with expected head SHA
```

Do not auto-merge while active hardening/review changes are still being made.

## 7. Ready-for-review / merge gate

Before Ready for review:

- code/tests/docs/context agree;
- focused tests pass;
- context validator passes;
- lifecycle is `review` and PR non-draft;
- Product Truth evidence is synchronized for user-visible changes.

Before merge:

- required semantic review is current for the exact base/head when the change class requires it;
- every reported semantic finding is resolved/validated;
- exact final head passes every required check and applicable browser/real-media/physical gate;
- reviewed base/head still match the PR when semantic review is required;
- unresolved GitHub review threads are empty.

Merge using an expected head SHA where tooling supports it. After merge, close context to idle through the protected-main closure procedure before handoff promotion.

## 8. Multi-agent discipline

One coordinator owns Git, integration, context and PR state. Writers receive disjoint paths. Independent semantic reviewers are read-only. No two writers own the same file concurrently.

## 9. Engineering style

Reuse professional open-source components first; keep provider-specific dependencies behind semantic adapters; keep optional features optional; never silently add paid/remote fallbacks; preserve Windows as a first-class target; do not trade the final architecture for a toy MVP.
