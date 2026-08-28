# Agent Instructions

These instructions apply to the entire UV Studio repository. Repository + GitHub are durable project memory; chat history is not.

## Mandatory session bootstrap — resolve repository skills before planning

Every fresh development invocation, and every materially changed task within an existing session, must resolve repository skills **before proposing an implementation plan or editing production code**.

1. Resolve live `main`, the current branch/PR and their exact heads.
2. Enumerate `.agents/skills/*/SKILL.md` from the current repository ref instead of relying on remembered skill names.
3. Read the frontmatter/trigger of every plausibly applicable skill and select every skill whose trigger matches the actual task phase or subsystem.
4. Load the selected skill(s) before planning implementation or performing the governed review/evidence step.
5. Never rely on remembered or cached skill text. Bind the decision to the skill path and the current source ref/head so an updated skill is picked up automatically after merge/rebase.
6. Re-run this bootstrap when `main` advances, the working branch is rebased, a new lifecycle slice starts, the task materially changes scope, or the work enters a governed review phase.
7. For release-critical work, fail closed if an applicable mandatory skill cannot be read or its required output/evidence is missing or stale.

A merge does **not** autonomously start the next slice or launch background work. The next development invocation reruns this bootstrap against the new repository state. Do not create a daemon, generic workflow engine, runtime `SkillGate`, new public tool or product authority merely to perform repository-skill discovery.

## Start here

Before changing files, read in this order:

1. `project-context/ACTIVE_SLICE.json`
2. `project-context/PROJECT_STATE.md`
3. `project-context/NEXT_TASK.md`
4. `docs/architecture/CURRENT_ARCHITECTURE.md`
5. `docs/architecture/README.md` — use its authority classification before reading older architecture files
6. `project-context/DECISIONS.md` and detailed decisions linked from current state — **D-064 owns Production Direction composition, D-065 owns shared production semantics, D-066 owns the JarvisHub Agent Harness donor/factoring boundary, D-067 owns Product Truth/current-doc consistency, D-068 owns desktop in-place updates, D-033 owns the editor foundation**
7. `docs/architecture/UV_STUDIO_V2_ARCHITECTURE_MAP.md`
8. `ARCHITECTURE_PRINCIPLES.md`
9. `ROADMAP.md` — historical Stage detail is subordinate to current architecture/accepted decisions
10. `UPSTREAM.md`
11. the active PR if `lifecycle_state` is `draft` or `review`, including diff/checks/unresolved threads
12. recent commits on `main`

Documents classified as `HISTORICAL`, `HISTORICAL SNAPSHOT` or `COMPATIBILITY` in `docs/architecture/README.md` are evidence/migration references only. Do not turn their old recipe/Product Orchestrator/Stage recommendations back into forward architecture unless a new accepted decision explicitly does so.

Run `python tools/validate_development_context.py` before implementation.

## Lifecycle is authoritative

`project-context/ACTIVE_SLICE.json` schema v2 is the machine-readable development-state authority.

- `idle`: there is no active branch/PR slice; `active_slice` must be null. Read `last_completed` and the one handoff, then initialize that handoff from current `main`.
- `draft`: exactly one active implementation/process slice exists and its PR must be draft.
- `review`: exactly one active slice is frozen for review and its PR must be non-draft.

Never continue work on a merged branch. A new slice starts only from an idle `main`. After a merge, close the merged context to idle before starting the next branch; see D-038 and `DEVELOPMENT_PROTOCOL.md`.

## Source-of-truth boundaries

- `ACTIVE_SLICE.json` owns lifecycle, active branch/PR identity when present, last completed merge identity, write scope, coordination policy, required checks and one handoff.
- `PROJECT_STATE.md` describes the product/process as it exists now, verified behavior and current risks.
- `docs/architecture/CURRENT_ARCHITECTURE.md` owns the compact current architecture shape.
- `docs/architecture/README.md` classifies architecture documents as current, foundational, compatibility or historical.
- `NEXT_TASK.md` describes exactly one continuation target.
- `PROJECT_HISTORY.md`, superseded decision records, archived PRs and Git history hold completed/historical detail.
- Exact active-head SHAs/check conclusions remain live GitHub facts.

## Production Directions + shared Production Semantic Core

D-064 and D-065 are mandatory for new product work.

- A UV Studio **Project** is the canonical product object; a **Production Direction** describes how a distinct kind of production is organized above the shared application core.
- Current first-class directions are micro-drama/story, commercial/product, music video, narrated video, dub battle/cinematic revoicing and free project.
- Directions may add domain documents, navigation, production policy and Agent context, but they MUST share Project Store, Studio shell, canonical Timeline, application commands, models/jobs and export infrastructure.
- Common semantic concepts such as **Scene / Shot / Take / accepted take / semantic bindings / continuity links** belong to the shared Production Semantic Core when multiple directions need them. Do not create parallel direction-specific versions of a genuinely common concept.
- Not every direction/project must instantiate every shared semantic entity. Share contracts without forcing one giant universal film schema.
- Direction-specific extensions (for example commercial brief/product/brand or Music Map) reference shared semantic identities where appropriate instead of forking them.
- A Shot is not a Timeline Clip: production semantics describe intent/context/accepted material; Timeline owns final time assembly.
- Do not implement a new direction as a `RecipeDefinition`, Product-Orchestrator execution graph, numbered Stage or separate canonical project engine.
- Operation-level features such as targeted edit, ordinary dubbing/translation, slideshow, visualizer, action transfer, talking character and lip-sync remain contextual Studio tools unless a later decision proves a distinct production model.
- Existing recipe/Product-Orchestrator/Stage 8 code is compatibility/migration material unless a later accepted decision says otherwise.
- User-significant AI model choice must remain visible in the relevant tool. Capability abstraction is an execution boundary, not a reason to hide the model.
- Settings configure connections/runtimes/accounts; Studio tools own per-operation model and creative parameters.
- Agent automation uses the same Studio/Application Commands as manual UI. No Agent-only mutation authority.
- Modern Production Direction identity must be typed/validated. Legacy recipe projects may remain explicit compatibility projects without being assigned a fake direction.

## JarvisHub Agent Harness donor boundary

D-066 is mandatory when designing Jobs, generation orchestration or Agent runtime work.

- JarvisHub is the reference architecture/method donor for the missing autonomous Agent Harness, **not** a replacement UV project/application foundation.
- Adapt useful patterns for persistent agent loop, Planner/Tasks, Skills, context/memory compaction, functional subagents (`explore` / `plan` / `media` / `critic`), effects/policy, trace, background execution and evaluate/repair loops.
- Carry JarvisHub-derived reliability patterns into the Job/generation foundation now: idempotency for long-running/cost-bearing/external execution, provider-neutral `GenerationContract`, durable attempts/provenance and effects visibility.
- Do not introduce JarvisHub Canvas-as-source-of-truth, its generic node project model, PostgreSQL/Hono application authority or a parallel Protocol Bridge/tool registry.
- Future Agent trace/evaluations/repair records reference canonical Project/Scene/Shot/Take/asset/Timeline identities; they do not become a second source of truth.
- Agent, GUI, scripts and MCP converge on the same commands/models/jobs/capabilities and authorization boundaries.

## Product Truth + current documentation

D-067 is mandatory for user-visible product work and current project/architecture documentation.

- A user-visible feature is complete only when canonical application/backend behavior, the required frontend surface and user-outcome evidence agree.
- Do not count backend-only implementation as a finished desktop feature merely because its unit/API tests are green.
- Do not expose a frontend control as ready when its canonical backend/application path is missing, stubbed or semantically incompatible.
- Internal infrastructure may intentionally have no UI, but it must be explicitly non-user-visible/not-ready rather than counted as product functionality.
- New user-visible features should acquire a machine-readable Product Truth Contract binding feature identity, command/query, backend/API surface, frontend entry, relevant canonical state/dependencies and E2E proof.
- `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, `CURRENT_ARCHITECTURE.md`, authority indexes and declared Product Truth Contracts must agree on narrow machine-checkable facts.
- Prefer explicit markers/registries/reference checks over heuristic CI that attempts to understand arbitrary prose.
- Current documentation must distinguish as-built behavior from target/future behavior.

See `docs/architecture/PRODUCT_TRUTH_CONTRACT.md`.

## Desktop updates

D-068 is mandatory for maintained desktop release/productization work.

- Stable UV Studio releases default to one maintained installation identity and in-place updates, not one side-by-side installation per version.
- Update UI must expose current version, check-for-updates, available version/release notes, progress and controlled update/restart state.
- Update installation is an explicit user action initially; automatic checking may be configurable.
- Update artifacts/metadata must be bounded and verified; fail closed on digest/signature/identity mismatch.
- Application/runtime files are replaceable; Project Store data, user media and intended persistent settings are protected separately.
- Use an out-of-process updater/installer handoff or another proven safe replacement mechanism; do not overwrite the running application unsafely.
- Stage-9 release evidence must include clean install **and** supported N-1 -> N in-place upgrade with representative real project/settings state.

See `docs/architecture/DESKTOP_UPDATES.md`.

## Reuse-first and programmable editing

`ARCHITECTURE_PRINCIPLES.md`, D-033, D-064, D-065, D-066, D-067 and D-068 are mandatory. D-063 is supporting/partially superseded history, not independent product-composition authority.

- Search/license-check/probe credible professional open-source components before building a general editor/media/agent primitive.
- Record a concrete rejection before replacing a suitable mature component with custom infrastructure.
- Reuse a donor's **needed primitive behind a UV-owned boundary**; do not inherit the donor application's project/workflow model merely because its code is useful.
- MLT remains the selected timeline/editing engine behind the UV adapter; OpenCut Classic remains a selective editor-UX donor. Do not introduce a second canonical timeline engine without a superseding evidence-backed decision.
- Every meaningful editor or production mutation must converge on one UV-owned programmatic command/workflow contract used by GUI, scripts, AI and MCP.
- Automation must not mutate canonical project/timeline/production documents directly or bypass domain validation/D-017/review boundaries.

## Slice and Git ownership

- One meaningful slice uses one integration branch and one PR.
- The coordinator owns the integration branch, Git operations, context files and PR state.
- Writers use explicitly assigned non-overlapping paths; independent semantic reviewers are read-only.
- Do not edit `vendor/videoclaw-app` during ordinary work; prefer UV-owned wrappers/adapters.
- Closed unmerged research/reference branches are donors only; do not continue implementation on them unless the lifecycle explicitly reactivates them.

## Independent semantic review

For material production/runtime/security/recovery/authority/acceptance changes, **independent semantic review is required before merge**. Material changes to the repository's own merge/review policy are review-significant once this policy is accepted.

The primary review is a fresh ordinary ChatGPT context using `.agents/skills/code-review/SKILL.md`, bound to the exact `BASE_SHA..HEAD_SHA`. It is an assurance layer, not another implementation/planning workspace.

Use this order:

```text
implementation / required research
 -> focused tests
 -> preliminary hosted CI when useful
 -> freeze BASE_SHA + HEAD_SHA
 -> required fresh ordinary ChatGPT semantic review via code-review skill
 -> optional @codex review when available
 -> validate every reported finding as CONFIRMED / REJECTED / SUPERSEDED
 -> fix confirmed findings
 -> any material post-review change makes the prior review stale
 -> fresh required ChatGPT review on the new exact head
 -> optional fresh @codex review when available
 -> final exact-head CI / browser / real-media / physical acceptance as applicable
 -> verify reviewed BASE_SHA + HEAD_SHA still match the PR
 -> merge
```

The mandatory primary reviewer must run in a separate fresh ordinary-ChatGPT conversation/context and reconstruct evidence from the repository. Do not use ChatGPT Work, Workspace Agents, Codex automation or Codex Review as a substitute for this required review. A one-time ChatGPT Scheduled Task may launch the review only when it can truthfully satisfy the fresh ordinary-ChatGPT context contract in `code-review`; otherwise use a manually opened fresh ordinary-ChatGPT conversation.

Codex Review is an optional additional reviewer. Use it when quota is available because independent findings remain valuable, but Codex quota exhaustion does not block merge when the required fresh ChatGPT review, finding validation and all other applicable gates pass. State Codex unavailability explicitly; never represent an unavailable Codex review as completed.

A reported finding is a review result, not automatically project truth. Validate it against code/tests/evidence before fixing. Do not merge with unresolved reported findings.

The review result is valid only for the exact reviewed identity. A material post-review change to runtime, security, recovery/retry, concurrency/identity, canonical authority, verification/acceptance semantics, acceptance tests/gates or merge/review policy invalidates the old review. A base change likewise requires a fresh exact-base review. Clearly non-material spelling/formatting-only deltas may preserve review validity only after explicit inspection; when uncertain, review again.

Documentation-only PRs that do not materially alter process/security/acceptance/runtime semantics should not be forced through independent semantic review or physical gates beyond repository requirements. Process PRs that materially change merge/review semantics are review-significant, but the PR that first introduces this policy is adopted under the previously accepted merge policy; the new policy governs subsequent PRs after merge.

## Completion gate

Before marking a PR ready:

1. synchronize implementation, `ACTIVE_SLICE.json`, `PROJECT_STATE.md`, `NEXT_TASK.md`, current architecture/decision indexes and PR body;
2. for user-visible work, ensure the Product Truth Contract/evidence is synchronized and no backend/frontend readiness gap remains;
3. set `lifecycle_state` to `review` and make the PR non-draft;
4. run focused tests plus `python tools/validate_development_context.py` and applicable architecture/product-truth consistency checks;
5. for review-significant work after adoption of this policy, freeze exact base/head and obtain a fresh ordinary-ChatGPT semantic review through `.agents/skills/code-review/SKILL.md`; classify every reported finding and repeat review after material fixes;
6. require the exact final head to pass every declared check and applicable browser/real-media/physical gate;
7. verify the PR base/head still match the exact identity covered by the required review when review is required;
8. confirm no unresolved review threads or unresolved semantic-review findings.

After merge, perform the D-038 context-closure transition to `idle` using the exact merged PR number/merge commit. Only then start the declared handoff.
