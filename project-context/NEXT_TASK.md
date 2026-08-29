# Next Task

<!-- uv-next-slice: actions-hardening -->

## Target

Harden the repository's GitHub Actions supply chain before resuming product architecture work.

This is a small repository security/process slice. It must not change UV Studio runtime, product behavior or canonical application authority.

## Required scope

1. Replace every first-party `actions/*@vN` reference in maintained workflows with an exact full 40-character commit SHA, using the exact action revisions already proven by current successful CI where practical so pinning does not accidentally become a version upgrade.
2. Keep explicit `permissions: contents: read` on read-only workflows.
3. Set `persist-credentials: false` on every `actions/checkout` step that does not need authenticated Git push.
4. Keep `contents: write` only on the narrowly bounded workflow that actually commits/pushes the pinned VideoClaw snapshot; do not widen permissions elsewhere.
5. Add a repository-level static guard/test that fails if a future workflow:
   - reintroduces floating `actions/*@vN` references;
   - grants `contents: write` outside the approved writer workflow;
   - leaves checkout credentials persisted in a read-only workflow.
6. Run the permanent Ubuntu/Windows CI on the exact final head.
7. Because this changes CI/security/acceptance mechanics, freeze exact BASE/HEAD and obtain the required fresh ordinary-ChatGPT semantic review before merge.

## Native Ready connector note

A live post-PR-#82 check showed that the official connector exposes `mark_pull_request_ready_for_review`, but the current connector call fails internally because its GraphQL selection queries nonexistent `Repository.fullDatabaseId`.

Treat this as an external connector implementation defect, not as proof that GitHub lacks the Ready mutation. Do not add a privileged `pull_request_target` fallback inside the hardening slice merely to work around this connector bug. Revisit a repository fallback only if a later separately justified process decision proves that the benefit outweighs the added privileged workflow surface.

## GitHub settings follow-up

After the hardening PR is merged and the repository workflows are compatible, enable GitHub's repository/organization policy requiring Actions to be pinned to a full-length commit SHA.

That UI setting is intentionally enabled only after repository workflows are already compliant so development is not interrupted by a policy/configuration ordering failure.

## Following product slice

After Actions hardening and its lifecycle closure, resume `project-identity-v2-compat-reader` from the accepted D-070 migration inventory.

That product slice must preserve schema-v1 project/archive readability while introducing the newer identity/compatibility boundary needed before modern projects can stop depending on `recipe_id` as canonical identity.

## Out of scope

- do not implement `project-identity-v2-compat-reader` in the Actions hardening PR;
- do not create a Ready-for-review fallback workflow in the same slice;
- do not upgrade unrelated dependencies or Actions majors merely because pinning is being introduced;
- do not change product/runtime behavior.
