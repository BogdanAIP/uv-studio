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

- Stage 3 is `Capability Registry & Adapters`;
- recipes depend on semantic capability IDs, not runtime-specific tool names;
- OpenClaw may be enabled but is not required;
- direct local and MCP execution remain possible;
- native VideoClaw paths are compatibility offers during migration.

---

## D-012 — Qwen-MM-Plugins is a workflow donor and optional capability package, not a paid dependency
Status: accepted  
Date: 2026-08-11

Decision: use/adapt professional production workflow ideas from Qwen-MM-Plugins where they improve UV Studio and support Qwen-MM as an optional MCP package. Do not make DashScope or another Qwen cloud API mandatory.

Research reference: `QwenLM/Qwen-MM-Plugins@7dfc08b7de8e621fc28bf9814e3d41a59b4595ae` (Apache-2.0).

Consequences:

- provider-neutral Qwen-inspired workflow discipline may be reused independently;
- local/free alternatives stay first-class;
- Qwen cloud generation/Omni operations remain explicit optional capabilities;
- WSL-only optional integrations cannot become a native-Windows prerequisite;
- Apache-2.0 obligations must be preserved for any copied/modified code.

---

## D-013 — Semantic capability is separate from adapter offer
Status: accepted  
Date: 2026-08-11

Decision: represent media ability as provider-neutral `CapabilityDefinition`, implementation family as `AdapterDefinition`, and one implementation proposal as `CapabilityOffer` with explicit readiness, locality and cost class.

Reason: an open-source integration may invoke a paid model, while a free operation may be local or remote.

Consequences: recipes stay provider-neutral; local/free and remote/paid offers can coexist; `configuration_required` is not `available`; registry ordering is metadata only. Full rationale: `project-context/decisions/D-013-capability-offers.md`.

---

## D-014 — Capability metadata is not execution permission
Status: accepted  
Date: 2026-08-11

Decision: registered offers pass through explicit `SelectionPolicy` before execution. `local_free_first` selects only `available + free + local`; it never widens to remote or paid-capable offers. Local media execution is project-scoped and command-bounded.

Reason: registry preference must never become implicit permission to invoke a provider or spend money.

Consequences: current local execution is fail-closed; raw FFmpeg flags are not exposed; paths cannot escape canonical projects; future MCP/Qwen/OpenClaw/provider adapters obey the same permission boundary. Full rationale: `project-context/decisions/D-014-execution-permission.md`.

---

## D-015 — Direct MCP discovery is generic, explicit and non-executing
Status: accepted  
Date: 2026-08-11

Decision: use official MCP Python SDK v2 for generic direct stdio discovery. MCP profiles are machine-global configuration with environment-variable references, not portable project state. Only explicit `MCPToolBinding` maps a discovered tool to an existing semantic capability and creates a `CapabilityOffer`.

Reason: MCP is a reusable transport seam, not another provider-specific orchestration layer. Discovery must not become implicit tool invocation, command execution, secret exposure or paid-provider consent.

Consequences: discovery calls `list_tools()` only; no arbitrary profile-command creation API exists; unbound tools never become offers; cost/locality are binding facts; real stdio discovery/timeout/cleanup is tested on Linux and Windows. Full rationale: `project-context/decisions/D-015-direct-mcp-discovery.md`.

---

## D-016 — Qwen-MM is an optional pinned profile/binding pack
Status: accepted  
Date: 2026-08-11

Decision: integrate `QwenLM/Qwen-MM-Plugins` as optional trusted MCP profile/binding templates pinned to verified commit `7dfc08b7de8e621fc28bf9814e3d41a59b4595ae`, not as a mandatory runtime or special orchestration layer.

Reason: current Qwen-MM combines genuinely local/free core operations with DashScope-backed remote operations, and the Apache-2.0 repository license does not determine execution cost.

Consequences:

- `core.media_info -> media.probe` is `local + free`;
- DashScope-backed understanding/ASR and Qwen/Wan generation bindings are `remote + potentially_paid`;
- provider-neutral `speech.transcribe` is added for ASR implementations;
- `wan_s2v -> video.digital_human` closes the supplied-audio semantic gap but remains non-executable until remote/paid consent and cost controls exist;
- mixed/mismatched tools such as current `happyhorse` and `segmentation` remain intentionally unbound;
- cloud profiles persist only `DASHSCOPE_API_KEY` references, never resolved values;
- current upstream WSL2-only Windows support is fail-closed for native-Windows Qwen configuration;
- Qwen profile templates pin an exact SHA and never fuzzy-remap tool drift.

Full rationale: `project-context/decisions/D-016-qwen-mm-pack.md`.

---

## D-017 — External execution consent is product-owned, exact and one-shot
Status: accepted  
Date: 2026-08-11

Decision: selection and external execution authorization are separate. UV Studio prepares the exact selected execution intent, reports locality/cost-estimate facts, requires semantic acknowledgements (`remote_execution`, `external_cost`, `unknown_cost`) when applicable, and issues only a short-lived one-shot runtime grant bound to the normalized input digest.

Reason: provider-specific consent would fragment safety behavior, while discovery/selection alone never proves permission to contact an external service or incur cost.

Consequences: local/free stays frictionless; remote/non-free execution fails closed without the required acknowledgement; unknown provider price remains explicitly unknown; grants are never portable project state. Full rationale: `project-context/decisions/D-017-execution-authorization.md`.

---

## D-018 — MCP invocation is exact, short-lived and provenance-recorded
Status: accepted  
Date: 2026-08-11

Decision: an MCP tool may execute only through an exact configured binding that still matches an unchanged READY configuration digest, after D-017 authorization. Each invocation uses a bounded short-lived official-SDK stdio session and writes durable non-secret running/success/failure provenance under project `tasks/`.

Reason: machine bindings can drift after discovery and external calls may have cost or side effects. Execution must therefore be identity-stable, bounded and auditable without persisting secrets or consent tokens.

Consequences: no fuzzy tool remapping; configuration changes require reconnect; request/response sizes and timeouts are bounded; raw stderr/tool errors are excluded from provenance; generic MCP execution rejects raw host paths until a binding explicitly owns safe Project Store file translation. Full rationale: `project-context/decisions/D-018-authorized-mcp-invocation.md`.

---

## D-019 — MCP project files are binding-owned portable references
Status: accepted  
Date: 2026-08-11

Decision: a real project file may be translated to an MCP host path only when the exact `MCPToolBinding` explicitly declares a versioned `MCPProjectFileInput` for that top-level argument and allowed canonical roots.

Reason: MCP tools often require absolute filesystem paths, while UV Studio must keep requests/projects portable and must never turn generic MCP execution into arbitrary host filesystem access.

Consequences: only `sources`, `assets`, `artifacts` and `exports` may be exposed by this contract; internal `tasks`, `timeline`, `reviews` stay unavailable; raw host paths still fail closed; authorization/provenance digest the original portable input; resolved paths exist only in the invocation payload; binding contract changes require reconnect. The freshly re-verified Qwen core `media_info(path, raw=False)` binding receives the first explicit project-file contract, while unverified Qwen cloud bindings do not. Full rationale: `project-context/decisions/D-019-mcp-project-file-inputs.md`.

---

## D-020 — Native VideoClaw compatibility execution is exact-offer only
Status: accepted  
Date: 2026-08-11

Decision: native VideoClaw compatibility may execute only product-whitelisted exact offers. The first executable native offer is `native_videoclaw.edge_tts -> speech.synthesize`; there is no generic Python module/function/command bridge into vendored code.

Reason: an `AVAILABLE` compatibility offer must have a real transport, but making VideoClaw a universal execution engine would violate the product-owned capability boundary. Edge TTS is remote/free, so D-017 `remote_execution` authorization still applies.

Consequences: semantic input is bounded to text/voice/speed; UV Studio owns the output artifact path; external provenance remains portable; `edge-tts` stays an optional dependency in `requirements-edge-tts.txt`; all other model-backed native offers stay configuration-required until exact provider/model/credential contracts exist. Full rationale: `project-context/decisions/D-020-native-videoclaw-edge-tts.md`.
