# Next Task

<!-- uv-next-slice: github-ready-review-fallback -->

## Target

Re-evaluate whether `github-ready-review-fallback` is needed **before starting any new process slice**.

The current handoff ID is provisional so the post-merge lifecycle closure has one explicit decision point. It is not authorization to implement the fallback unconditionally.

## Entry gate

During the post-merge lifecycle closure for PR #82, resolve the live official GitHub connector capability again.

- If `mark_pull_request_ready_for_review` is available and works, **do not create or start** a `github-ready-review-fallback` branch/PR/workflow. Record that the fallback is unnecessary and advance the closed idle handoff directly to `project-identity-v2-compat-reader`.
- Only if the official connector mutation is unavailable as a capability may the closure preserve `github-ready-review-fallback` as the next bounded process slice.
- A transient failure must be classified before treating the native capability as unavailable; do not add privileged repository automation merely to work around an unrelated temporary error.

At the current PR #82 review head, the connected GitHub toolset exposes the native Ready mutation. That observation is evidence that the fallback is probably unnecessary, but the capability must be re-resolved after merge because connector capabilities are live external state.

## Conditional fallback scope

Only when the entry gate proves the native Ready mutation unavailable:

- add a trusted `pull_request_target` workflow on `main` that reacts only to the exact `uv:ready-for-review` label;
- require the triggering actor to be the repository owner and the PR head repository to equal this repository;
- do not checkout or execute PR code;
- grant only the permissions proven necessary for the mutation and cleanup;
- call the normal GitHub ready-for-review mutation through a trusted GitHub mechanism;
- independently verify the PR reports `draft=false` before declaring success;
- remove the service label after success/verified already-ready state so a later deliberate draft cycle can be triggered again;
- keep the fallback dormant unless the official connector mutation is unavailable.

## Required proof if fallback is needed

- focused static tests/guards for exact event, actor, repository and permission boundaries;
- no PR-head checkout or execution path in the trusted workflow;
- physical GitHub proof on a draft same-repository test PR that the fallback changes it to non-draft and cleans up its trigger;
- negative proof that non-owner/fork/non-matching-label events cannot execute the mutation path;
- context validation and permanent Ubuntu/Windows CI;
- required exact-base/exact-head fresh ordinary-ChatGPT semantic review because this changes repository review/acceptance mechanics;
- zero unresolved findings and review threads before merge.

## Following product slice

When the native Ready mutation is available, or after a separately justified fallback slice is completed, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.

That product slice must preserve schema-v1 project/archive readability while introducing the newer identity/compatibility boundary needed before modern projects can stop depending on `recipe_id` as canonical identity.

## Out of scope

Do not patch or vendor the server-side official ChatGPT GitHub connector. Do not mix `project-identity-v2-compat-reader` implementation into a fallback process slice if the fallback is actually required.
