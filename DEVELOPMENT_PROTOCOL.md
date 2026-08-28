# Development Protocol

This is the canonical lifecycle specification for development across chats/agents. `AGENTS.md` is the concise entrypoint.

## 1. Repository is the memory

At the start of every development or independent-review chat, first resolve live GitHub state and enumerate `.agents/skills/*/SKILL.md` from the applicable repository ref. Read the frontmatter/triggers and load every applicable skill before planning. Never rely on remembered skill names/text; repeat discovery after `main` advances, a branch is rebased, a new slice starts or task scope materially changes.

For development, then read `AGENTS.md`, `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, decision index/details, architecture principles, roadmap/upstream, the active PR when one exists and recent `main` commits. Run `python tools/validate_development_context.py` before implementation.

For independent semantic review, follow `.agents/skills/code-review/SKILL.md`: the accepted review policy comes from the exact requested `BASE_SHA`, while the review target is the exact `HEAD_SHA`.

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
- applicable independent semantic review is current for the exact base/head after adoption of the review policy;
- exact-head CI and unresolved review/finding state are authoritative.

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

A mechanical lifecycle-closure PR does not require a fresh semantic review merely because it changes lifecycle/context prose. If the closure also materially changes merge/review policy, security/authority semantics or another review-significant guarantee, the normal semantic-review rule applies.

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

For material production/runtime/frontend/security/recovery/concurrency/identity/authority/acceptance changes, independent semantic review is mandatory after this policy is adopted. Material changes to the repository's own merge/review policy are also review-significant after adoption.

The primary review mechanism is a **fresh ordinary-ChatGPT context** using `.agents/skills/code-review/SKILL.md`. ChatGPT Work, Workspace Agents, Codex automation and Codex Review do not substitute for it.

Codex Review remains an optional additional reviewer when quota is available. Codex quota exhaustion is recorded explicitly but is not a merge blocker when the mandatory ordinary-ChatGPT review and all other gates pass.

### Review identity

Freeze the intended review identity before requesting semantic review:

```text
REVIEW_REQUEST_V1
repository=<owner/repo>
pr_number=<number>
base_sha=<40-hex SHA>
head_sha=<40-hex SHA>
review_skill=code-review
review_skill_version=<expected version>
```

The reviewer verifies the live PR still has exactly that base/head and reviews `BASE_SHA..HEAD_SHA`. Review policy comes from `BASE_SHA`; target code/docs/tests and applicable target-specific skills come from `HEAD_SHA`.

A one-time ordinary ChatGPT Scheduled Task may only be a launcher when it can truthfully establish the fresh-context contract defined by the skill. Otherwise use a manually opened fresh ordinary-ChatGPT conversation.

### Required sequence

For an applicable PR:

```text
implementation
 -> focused tests
 -> preliminary required hosted CI on intended head
 -> freeze BASE_SHA + HEAD_SHA
 -> fresh ordinary ChatGPT semantic review
 -> optional @codex review when available
 -> validate findings as CONFIRMED / REJECTED / SUPERSEDED
 -> fix confirmed findings
 -> material HEAD change => previous review stale
 -> fresh ordinary ChatGPT review on new exact head
 -> optional fresh @codex review when useful/available
 -> final exact-head CI / required physical gates
 -> verify reviewed base/head still match
 -> verify unresolved findings and GitHub review threads are empty
 -> expected-head merge
```

A reviewer finding is not automatically project truth. The development context must verify the claimed path/evidence before changing code. `REJECTED` findings require concrete contrary evidence; `SUPERSEDED` means a later change removed/changed the path and normally requires fresh review.

The independent reviewer is read-only and must not collapse `review -> self-fix -> self-approve` into one context.

### Review invalidation

A previous semantic review becomes stale after a material post-review change to runtime/frontend behavior, security/authorization, persistence/recovery/retry, concurrency/identity/ownership/provenance, canonical authority, verification/acceptance semantics, Product Truth readiness, acceptance tests/CI/physical gates or merge/review policy.

A base-branch advance that changes the merge base also invalidates the review. Clearly non-material spelling/formatting-only deltas may preserve validity only after the exact delta is inspected and explicitly classified non-material; when uncertain, review again.

### Documentation/process scope

Documentation-only changes that do not materially alter process/security/acceptance/runtime semantics do not need independent semantic review. Process changes that materially change merge/review semantics do require it **after this policy is accepted**.

**Adoption exception:** the PR that first introduces `.agents/skills/code-review/SKILL.md` and this mandatory-review discipline is itself evaluated under the previously accepted merge policy. The new rule governs subsequent applicable PRs after the adoption PR merges.

### Ready/merge gate

Before Ready for review:

- code/tests/docs/context agree;
- focused tests pass;
- context validator passes;
- lifecycle is review and PR non-draft.

Before merge:

- when semantic review is required, a fresh `REVIEW_RESULT_V1` is current for the exact live `BASE_SHA..HEAD_SHA` and every reported finding is resolved/classified;
- optional Codex findings, when available, are likewise validated rather than blindly accepted;
- exact final head passes every required check and required physical gate;
- unresolved GitHub review threads are empty;
- live PR base/head still match the reviewed identity;
- merge uses an expected head SHA where tooling supports it.

After merge, close context to idle through the protected-main closure procedure before handoff promotion.

## 7. Multi-agent discipline

One coordinator owns Git, integration, context and PR state. Writers receive disjoint paths. Reviewers are read-only. No two writers own the same file concurrently.

## 8. Engineering style

Reuse professional open-source components first; keep provider-specific dependencies behind semantic adapters; keep optional features optional; never silently add paid/remote fallbacks; preserve Windows as a first-class target; do not trade the final architecture for a toy MVP.
