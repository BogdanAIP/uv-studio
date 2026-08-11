# Architecture Decisions

## D-001 — Repository is the durable development memory
Status: accepted  
Date: 2026-08-10

Decision: all durable implementation state, next-step context and architectural decisions live in GitHub, not only in ChatGPT history.

Reason: development will span multiple chats and old chats may become unavailable or too large.

Consequences: every development slice updates `PROJECT_STATE.md`, `NEXT_TASK.md` and PR history before it is considered complete.

---

## D-002 — VideoClaw modern application is the initial base
Status: accepted  
Date: 2026-08-10

Decision: Stage 0 starts from the modern `video-claw/video-claw` application in `HITsz-TMG/VideoClaw`, not from LocalMiniDrama, ViMax or Jellyfish.

Reason: its current architecture already exposes independent pipelines, task/artifact storage, FastAPI + Next.js, Windows setup, model capability metadata and existing-video-oriented provider inputs.

Consequences: preserve VideoClaw MIT attribution; isolate its large film orchestration instead of making it the universal UV Studio core.

---

## D-003 — Pin upstream before modification
Status: accepted  
Date: 2026-08-10

Decision: imported upstream code must come from an exact commit SHA and be reproducibly vendored.

Initial pin: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`.

Reason: reproducibility and future upstream diffing are impossible if source is copied from moving `main`.

Consequences: maintain an upstream lock file and provenance documentation.

---

## D-004 — No universal mandatory media pipeline
Status: accepted  
Date: 2026-08-10

Decision: UV Studio uses task recipes. Music, narration, story, characters, continuity, lip-sync and automatic review remain optional.

Reason: the target product must create/edit many kinds of video, not only clips or micro-dramas.

Consequences: future features should compose capabilities rather than add one bigger mandatory orchestration chain.

---

## D-005 — Continuity and VLM review are optional policies
Status: accepted  
Date: 2026-08-10

Decision: sequence state and automatic take review are enabled only where linked generated shots require them.

Reason: dubbing, simple range edits and standalone clips do not justify the complexity/cost.

Consequences: no future Project Store schema may require continuity data for all projects.

---

## D-006 — Provider-specific growth must be contained
Status: superseded by D-011  
Date: 2026-08-10

Decision at the time: preserve existing VideoClaw providers during baseline, but future capability growth should be behind a semantic bridge; OpenClaw was the preferred replaceable runtime candidate.

Reason: maintaining many fast-changing media APIs inside product domain code would recreate infrastructure already available elsewhere.

Superseded detail: the semantic boundary remains accepted, but OpenClaw is no longer the preferred mandatory path. D-011 makes all runtimes/adapters peers behind a Capability Registry.

---

## D-007 — Windows is a first-class target
Status: accepted  
Date: 2026-08-10

Decision: development and CI must continuously preserve Windows compatibility.

Reason: the intended local usage environment includes Windows desktop.

Consequences: baseline tooling and tests should run on Windows and Linux; packaging is a planned final-stage deliverable.

---

## D-008 — Vendored upstream is a compatibility boundary
Status: accepted  
Date: 2026-08-10

Decision: ordinary UV Studio features should be implemented outside `vendor/videoclaw-app` and interact with the pinned runtime through wrappers, APIs or adapters whenever practical.

Reason: direct product development inside vendored source makes upstream provenance, comparison and future pin updates increasingly difficult.

Consequences: Stage 0 adds a root-owned launcher above the vendor tree. A direct vendored-code modification requires an explicit reason and should be isolated/documented rather than becoming the default development style.

---

## D-009 — Project Store is file-first and product-owned
Status: accepted  
Date: 2026-08-10

Decision: canonical UV Studio project metadata uses a versioned local `project.json` stored by UV Studio-owned code. SQLite, cloud databases and upstream VideoClaw session files are not canonical project state.

Reason: the initial product is single-user/local-first, projects must survive runtime/chat changes, and a small atomic file format is easier to inspect, migrate, export and recover than an unnecessary database layer.

Consequences: schema v1 stays small and general; specialized workflow state remains optional through extensions/dedicated files. SQLite may be introduced only after a measured need such as indexing scale or multi-process coordination.

---

## D-010 — User-facing frontend becomes UV Studio-owned derived code
Status: accepted  
Date: 2026-08-10

Decision: the pinned VideoClaw frontend is used as the starting UI implementation, but substantial UV Studio frontend development will occur in a top-level UV Studio-owned derived frontend rather than by continuously patching `vendor/videoclaw-app/frontend`.

Reason: the user-facing product surface requires extensive navigation, terminology and workflow changes. Treating that evolving surface as immutable vendor code would either block product development or create an unmaintainable patch set inside the upstream compatibility snapshot.

Consequences: preserve VideoClaw MIT attribution and record the exact source baseline used to promote the frontend. Keep the untouched vendored snapshot for upstream comparison while the product frontend evolves independently. Existing useful screens should be retained/migrated rather than rebuilt from scratch.

---

## D-011 — Capability Registry has peer adapters; OpenClaw is optional
Status: accepted  
Date: 2026-08-11

Decision: UV Studio will expose semantic media capabilities through a product-owned Capability Registry. Direct MCP, local tools, existing native VideoClaw integrations, OpenClaw and Qwen-MM-Plugins are peer adapters. No third-party runtime sits unconditionally between recipes and tools.

Reason: research of `QwenLM/Qwen-MM-Plugins` showed that high-quality MCP capability packages can be consumed directly, while OpenClaw remains useful when its broader runtime features are actually needed. A mandatory OpenClaw hop would add coupling without improving every workflow.

Consequences:

- Stage 3 is renamed from `Capability Bridge` to `Capability Registry & Adapters`;
- recipes depend on semantic capability IDs, not OpenClaw-specific tool names;
- OpenClaw may be enabled for a project/user but is not required to run UV Studio;
- direct local and MCP execution must remain possible;
- existing VideoClaw provider paths remain temporary/native adapters during migration.

---

## D-012 — Qwen-MM-Plugins is a workflow donor and optional capability package, not a paid dependency
Status: accepted  
Date: 2026-08-11

Decision: use/adapt the professional production workflow ideas from Qwen-MM-Plugins where they improve UV Studio, and support Qwen-MM-Plugins as an optional MCP package. Do not make DashScope or another Qwen cloud API mandatory for baseline UV Studio functionality.

Research reference: `QwenLM/Qwen-MM-Plugins@7dfc08b7de8e621fc28bf9814e3d41a59b4595ae` (Apache-2.0). At this revision the project explicitly separates local file capabilities from cloud API tools; its video-edit skill contains strong source-review, pacing, beat-sync, Scene Ledger, plan/sample/review gates and evidence-based review practices, while cloud Qwen/Wan/Omni/embedding operations require configured paid API access.

Reason: the workflow discipline is valuable independently of the provider. Requiring DashScope would violate UV Studio's local/free-first goal and duplicate the user's cost across multiple providers.

Consequences:

- Stage 2 gains provider-neutral production policy/gates inspired by suitable Qwen-MM-Plugins video-edit practices;
- Stage 4 existing-video work uses source review, planned edit direction, sample-first generated assets and evidence-based review where appropriate;
- local/free alternatives remain first-class for ASR, deterministic media work and other operations with adequate open-source implementations;
- Qwen cloud generation, Omni analysis and video-memory build are explicit optional capabilities;
- Qwen-MM-Plugins' current WSL2-only Windows support cannot become a prerequisite for the native Windows application;
- Apache-2.0 attribution/NOTICE requirements must be preserved for any code actually copied or modified, while architectural ideas alone do not create a runtime dependency.

---

## D-013 — Semantic capability is separate from adapter offer
Status: accepted  
Date: 2026-08-11

Decision: represent media ability as provider-neutral `CapabilityDefinition`, implementation family as `AdapterDefinition`, and one implementation proposal as `CapabilityOffer` with explicit readiness, locality and cost class.

Reason: an open-source integration may invoke a paid model, while a free operation may be local or remote. Provider identity alone is not sufficient to express execution economics or readiness safely.

Consequences: recipes stay provider-neutral; local/free and remote/paid offers can coexist; `configuration_required` is not `available`; registry ordering is metadata only. Full rationale: `project-context/decisions/D-013-capability-offers.md`.

---

## D-014 — Capability metadata is not execution permission
Status: accepted  
Date: 2026-08-11

Decision: discovered/registered offers pass through an explicit `SelectionPolicy` before any adapter may execute. `local_free_first` selects only `available + free + local`; it never widens to remote or paid-capable offers. Local media execution is project-scoped and command-bounded.

Reason: deterministic registry preference must never become implicit permission to invoke a provider or spend money. Generic media tools must also not become arbitrary filesystem/shell access.

Consequences: current execution permits only explicit free/local FFmpeg offers; raw FFmpeg flags are not exposed; paths cannot escape the canonical project; failed generation does not create a successful artifact; future MCP/Qwen/OpenClaw/provider adapters must obey the same permission boundary. Full rationale: `project-context/decisions/D-014-execution-permission.md`.
