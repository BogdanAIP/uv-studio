# D-023 — Agent development state is explicit, scoped and CI-checked

Status: accepted
Date: 2026-08-11

## Context

UV Studio is developed across independent Codex chats and may use several agents in one slice. Markdown handoffs made sequential work reliable, but branch, pull-request and phase facts were duplicated manually. PR #19 demonstrated the failure mode: implementation and CI were complete while the pull request remained draft with a stale body. The repository also lacked an automatic entrypoint for coding agents and rules for concurrent writers.

## Decision

Add a repository-owned agent workflow contract:

- `AGENTS.md` is the automatic entrypoint and canonical reading order;
- `project-context/ACTIVE_SLICE.json` is the machine-readable slice intent and coordination state;
- `PROJECT_STATE.md` and `NEXT_TASK.md` carry exact slice markers rather than duplicating branch/PR/phase fields;
- one coordinator owns Git, integration, context files and pull-request state;
- concurrent writers use disjoint paths in a shared checkout or isolated worktrees;
- reviewers remain read-only;
- a stdlib-only validator checks the JSON contract, handoff markers and live pull-request event;
- CI revalidates pull-request edits and draft/ready transitions, not only code pushes;
- pull requests use one required template with durable Goal, Changes, Verification, Architecture impact, Known limitations and Next task sections.

The JSON intentionally does not contain `head_sha`. A commit cannot stably contain its own SHA; exact head identity and check conclusions remain live GitHub facts verified immediately before merge.

## Consequences

- a new agent can discover the workflow without relying on chat history;
- multiple agents cannot silently claim the same files or mutate Git concurrently;
- stale PR metadata and mismatched handoff markers fail CI;
- current state remains compact while completed milestones move to `PROJECT_HISTORY.md`;
- no new runtime or CI dependency is introduced;
- the coordinator must update `pull_request` after PR creation and `phase` before ready-for-review;
- `write_scope` is a coordinator/reviewer ownership contract in schema v1; changed-path enforcement remains an explicit future hardening step;
- exact final-head CI and review state are still checked through GitHub immediately before merge.
