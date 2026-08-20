# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: stage-9-desktop-productization-release-hardening -->

**Updated:** 2026-08-20

## Current lifecycle

Stage 9 Desktop Productization & Release Hardening remains the single active Draft slice in PR #38 on `stage-9/desktop-productization-release-hardening`, based on green idle `main@d57bc315c27ed21f26c9050d661c792f95ab8aa3` after Stage 8 merged as PR #37.

The branch is now explicitly **paused from merge readiness by D-062 Product Truth Recovery Gate**.

The last product-code head audited before this context correction was `9defd097b140d1b1c9837bddd30d43768cb8e408`. Subsequent documentation-only commits record the recovery decision and do not claim new product behavior.

Stage 9 packaging, installer, update/rollback, integrity, native-shell and release-hardening work remains valuable and must be preserved. However, the first human Windows 10 installed-app review and a broader repository/history audit showed that green engineering/release automation does not prove a coherent user-facing product.

## Product-recovery finding

The release blocker is no longer primarily signing or publication polish.

Human review first exposed first-run usability failures: project creation could be left disabled, native controls were unreadable, prerequisite-dependent controls looked broken, and launch diagnostics remained too visible. The subsequent audit found deeper pre-Stage-9 causes:

- Stage 3.5 correctly stopped mounting the complete legacy VideoClaw FastAPI application for authorization/secret safety;
- some legacy frontend clients and recipe execution plans still reference historical `/api/pipelines/*`, `/api/tasks`, `/api/sessions`, `/api/models`, `/api/sandbox/*` surfaces that are not mounted by the current UV-owned server;
- `narrated_video` and `action_transfer` execution metadata can advertise legacy pipeline targets despite those targets not being current mounted product routes;
- `general_video` is presented as a product recipe although its own execution layer states that a true general-video execution path is not implemented;
- some visible recipes provide preparation/state forms rather than a complete intent-to-result workflow;
- the frontend directly reconstructs several feature-specific state machines and prerequisites instead of receiving one product-level workflow/next-action projection;
- D-033 selected a reuse-first MLT/OpenCut foundation, but implementation has drifted toward more UV-owned editor/timeline UI while MLT is largely a derived projection/render boundary;
- current browser E2E can exercise informed paths and seeded intermediate state without proving cold-start discoverability or setup truth.

These findings explain why the application can be technically healthy while a normal user experiences apparently dead controls and unclear workflows.

## D-062 Product Truth Recovery Gate

D-062 is accepted and `docs/architecture/PRODUCT_RECOVERY_PLAN.md` is the recovery authority.

Stage 9 may not merge until all of the following are true:

1. every visible recipe/action has a truthful readiness state backed by a mounted executable path;
2. there are zero execution-plan targets pointing at unmounted endpoints;
3. stale donor/legacy frontend clients are either retired or explicitly isolated as compatibility code;
4. a Product Orchestrator projects workflow readiness, prerequisites and semantic next actions for GUI/AI/MCP/scripts;
5. D-033 editor ownership/reuse ambiguity is explicitly re-resolved before generic NLE growth;
6. permanent scenarios A-E complete through the UI without manual API calls or hidden test-only state seeding;
7. clean-state browser evidence passes;
8. human Windows installed-app review passes;
9. the existing Stage 9 security/integrity/release checks remain green.

## Recovery order

The next implementation work is deliberately ordered around product truth rather than more visual polish:

1. Product Truth Inventory for every visible mode/action;
2. recipe/execution contract repair, including stale launch paths and false readiness;
3. Product Orchestrator contract and incremental common semantic command envelope;
4. editor-foundation re-resolution under reuse-first constraints;
5. simplified permanent journeys: targeted edit, dubbing, music video, narrated video, general video;
6. rationalization of additional recipes and optional ML setup;
7. cold-start UI-only product regressions;
8. resume Stage 9 package/release work and only then finish trusted signing/publication.

## Foundation to preserve

The recovery is **not** a rewrite. The following are considered valuable proven foundations unless later evidence explicitly supersedes them:

- Project Store, portable archives, migrations and path/traversal boundaries;
- D-017 authorization and provider-neutral Capability Registry;
- provenance, cancellation and capability-job ownership;
- deterministic FFmpeg range/edit/render/preview/dubbing/music/photo/visualizer operations;
- portable accepted edit, dubbing and music state;
- MLT runtime/adapter where it provides demonstrated engine value;
- D-044 immutable release inventory and deep tamper verification;
- D-045 mutable user-data separation under `%LOCALAPPDATA%/UV Studio`;
- exact packaged Python/Node/media toolchain resolution;
- per-user versioned NSIS install/update/rollback/uninstall model;
- Rust/WebView2 native Windows host and bounded backend/frontend lifecycle;
- Stage 9 legal/security/dependency hardening already proven.

## Stage 9 engineering foundation already delivered

The branch contains substantial release engineering that should be retained for later reconciliation:

- D-044 immutable release manifest;
- D-045 packaged mutable-state boundary;
- D-046 exact supported release runtimes;
- D-047 manifest-owned packaged toolchain resolution;
- D-048 official Next standalone frontend packaging;
- D-049 desktop launcher/supervision foundation, later complemented by D-061 Rust/WebView2 native host;
- D-050 per-user versioned Windows installation;
- D-051 fail-closed Project Store migration preparation/recovery;
- D-052 curated media payload policy;
- D-053 installer-carried update/rollback;
- D-054 secret-safe diagnostics/recovery health;
- D-055 installed clean-machine runtime independence proof;
- D-056 cancellable local capability jobs;
- D-057 constrained-host/long-project evidence;
- D-058 redistributable Windows media runtime boundary;
- D-059 public signing boundary definition;
- D-060 product UX surface boundary;
- D-061 Rust WebView2 desktop host.

D-059 trusted public signing remains necessary for public release, but it is **not the current highest-priority blocker**. Signing a product whose core user journeys are misleading would not satisfy the roadmap completion gate.

## Architecture invariants during recovery

- Project Store and UV-owned domain state remain canonical.
- Provider/model/runtime identities remain adapter/runtime concerns rather than canonical project semantics.
- Paid/remote execution stays optional and explicit under D-017.
- No legacy VideoClaw route is remounted merely to make a button work if that would bypass the UV-owned authorization/security boundary.
- User-visible readiness must be derived from actual executable product truth.
- Internal plan/candidate/review/runtime structures remain durable where useful but must not dominate ordinary UX when no user decision is required.
- GUI, scripts, AI and MCP converge on UV-owned semantic actions/commands rather than independent workflow implementations.
- Reuse-first remains mandatory: do not expand a custom generic NLE until editor ownership is explicitly re-decided.
- Windows and Linux remain continuous engineering targets; Windows installed-app human review remains a release gate.

## Current limitations requiring recovery

- Recipe metadata, mounted routes and frontend behavior are not yet guaranteed to agree.
- Legacy donor API/client code remains in the repository and needs call-site evidence before retirement.
- General/narrated/action-transfer/digital-human product readiness is not yet a truthful end-to-end matrix.
- Music Video exposes too much internal Music Map/shot schema as ordinary authoring work.
- Dubbing can depend on separately configured local ASR/runtime prerequisites that are not yet presented as a coherent first-run setup path.
- Targeted editing exposes internal production gates more directly than necessary for the common user journey.
- Story/Commercial composition workspaces do not yet constitute complete production flows.
- Current E2E does not provide a separate cold-start, no-hidden-seeding product proof.

## Next handoff

The next implementation target is `product-recovery-truth-inventory`, defined in `project-context/NEXT_TASK.md`.

Because the repository protocol permits only one active slice, that recovery slice must not begin concurrently with active Stage 9 implementation. PR #38 remains Draft/paused while the recovery transition is coordinated; its branch is preserved as the Stage 9 engineering/package reference for later reconciliation.
