# Next Task

<!-- uv-next-slice: github-ready-review-fallback -->

## Target

Implement `github-ready-review-fallback` as the next bounded repository/process slice.

## Goal

Remove the official GitHub connector's `mark_pull_request_ready_for_review` operation as a single point of failure for UV Studio's review lifecycle without weakening draft/review authority or requiring a browser click.

## Scope

- add a trusted `pull_request_target` workflow on `main` that reacts only to the exact `uv:ready-for-review` label;
- require the triggering actor to be the repository owner and the PR head repository to equal this repository;
- do not checkout or execute PR code;
- grant only the permissions proven necessary for the mutation and cleanup: `contents: write`, `pull-requests: write`, and `issues: write`;
- call the normal GitHub ready-for-review mutation through `gh pr ready`;
- independently verify the PR reports `draft=false` before declaring success;
- remove the service label after success/verified already-ready state so a later deliberate draft cycle can be triggered again;
- document that the fallback is used only when the connector's native Ready operation is unavailable;
- preserve `project-identity-v2-compat-reader` as the following product/architecture slice.

## Required proof

- focused static tests/guards for exact event, actor, repository and permission boundaries;
- no PR-head checkout or execution path in the trusted workflow;
- physical GitHub proof on a draft same-repository test PR: connector adds `uv:ready-for-review`, Action changes it to non-draft, independent PR read reports `draft=false`, and the label is removed;
- negative proof that non-owner/fork/non-matching-label events cannot execute the mutation path;
- context validation and permanent Ubuntu/Windows CI;
- required exact-base/exact-head fresh ordinary-ChatGPT semantic review because this changes repository review/acceptance mechanics;
- zero unresolved findings and review threads before merge.

## Out of scope

Do not patch or vendor the server-side official ChatGPT GitHub connector. Do not mix `project-identity-v2-compat-reader` implementation into this process slice.
