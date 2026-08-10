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
Status: accepted  
Date: 2026-08-10

Decision: preserve existing VideoClaw providers during baseline, but future capability growth should be behind a semantic bridge; OpenClaw is the preferred replaceable runtime candidate.

Reason: maintaining many fast-changing media APIs inside product domain code would recreate infrastructure already available elsewhere.

Consequences: do not add new provider-specific branches to unrelated domain modules.

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