# Project State

**Updated:** 2026-08-11  
**Repository:** `BogdanAIP/uv-studio`  
**Active roadmap stage:** Stage 1 — Universal Project Store (final portability slice)  
**Active branch:** `stage-1/project-archives`  
**Main baseline before this branch:** `9570658d18553b5a3cae5a53264376ab00a3ee3a`  
**Branch status:** portable project archive core/API/UI + Qwen-MM-informed architecture revision implemented; final branch CI must be green before merge.

## Product definition

UV Studio is a universal video production and editing studio. It uses task-specific recipes rather than forcing every project through a film, music-video or micro-drama pipeline.

Music, narration, story, characters, continuity, lip-sync and automated review are optional capabilities.

Paid AI APIs are optional capabilities, not hidden baseline dependencies.

## Current architecture

- pinned upstream runtime: `HITsz-TMG/VideoClaw@5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`;
- immutable comparison/runtime snapshot: `vendor/videoclaw-app`;
- UV Studio-owned backend entrypoint: `uv_studio.server`;
- existing upstream FastAPI routes remain mounted through that server;
- canonical project state: UV Studio file-first Project Store (`project.json` v1), not upstream session JSON;
- canonical project API: `/api/uv/projects`;
- UV Studio-owned product frontend: top-level `frontend/`, derived once from the pinned MIT frontend baseline;
- untouched upstream frontend snapshot remains at `vendor/videoclaw-app/frontend`;
- provider growth is behind a future product-owned Capability Registry;
- direct MCP, local tools, native VideoClaw, OpenClaw and Qwen-MM-Plugins will be peer adapters rather than one mandatory runtime chain;
- professional production policy is separate from provider/model choice;
- specialized continuity/review state remains optional.

## Merged milestones in main before this branch

- `af24ed11d899ee1f459571c5d774b7ac9ad6d1ca` — reproducible VideoClaw baseline;
- `8d175c2535806841c712582532efea403a2f8599` — UV Studio root runtime/HTTP smoke boundary;
- `2276a854c4109f0039ae1aeb55304650840e1652` — canonical local Project Store v1;
- `21016061be2a2aedd59e7ed7b0424467d82bfd2f` — UV Studio server wrapper + canonical Projects API;
- `9570658d18553b5a3cae5a53264376ab00a3ee3a` — UV Studio-owned frontend + canonical Projects list/create/open UI.

## Stage 1 portability implemented on current branch

### Portable archive format

Added `uv_studio/projects/archive.py` and public package exports.

Archive shape:

```text
<project-id>.uvproj.zip
├── .uv-project-archive.json
└── project/
    └── complete canonical project directory
```

Manifest records archive/project schema versions, project ID, timestamp, regular file paths, sizes and SHA-256 digests.

### Import safety

Import is staged and fail-closed.

Implemented validation for:

- ZIP path traversal;
- absolute/Windows-drive paths;
- case-colliding/duplicate paths;
- encrypted entries;
- symlinks/special Unix ZIP entries;
- undeclared project files;
- file-size/total-size/entry-count/manifest limits;
- every file size and SHA-256;
- archive schema;
- project ID before it is used as a filesystem component;
- staged `project.json` and project schema/identity agreement;
- duplicate canonical project IDs.

Final introduction into Project Store uses `ProjectStore.commit_staged_project()` and an atomic same-filesystem directory rename. Failed final commit leaves no partial canonical project.

### Backup primitive

`create_backup()` creates a unique timestamped portable project archive in an explicitly supplied backup directory.

No hidden scheduling/cloud synchronization is part of the primitive.

### Archive API

Added:

```text
POST /api/uv/projects/import
GET  /api/uv/projects/{project_id}/archive
```

Import streams raw archive bytes to disk instead of buffering the complete media project in RAM. Export temporary files are removed after response delivery.

### Archive UI

Projects UI now supports:

- import `.uvproj.zip` from `/projects`;
- download a complete archive from `/projects/{project_id}`.

### Tests

Added archive unit tests for:

- round-trip metadata/files;
- nested source/artifact files;
- backup archives;
- duplicate project ID;
- tampered checksum;
- undeclared files;
- ZIP traversal;
- malicious manifest project ID;
- future archive schema;
- archive resource limits;
- simulated final atomic commit failure.

API integration tests cover HTTP archive export/import, nested file preservation, duplicate import, invalid ZIP and empty upload.

Documentation: `docs/PROJECT_ARCHIVES.md`.

## Qwen-MM-Plugins architecture review incorporated

Reviewed `QwenLM/Qwen-MM-Plugins@7dfc08b7de8e621fc28bf9814e3d41a59b4595ae` (Apache-2.0).

Durable conclusion:

- Qwen-MM-Plugins does not replace UV Studio;
- its strong `video-edit` production methodology is a useful donor: actual source review, pacing/audio-first/beat-sync planning, Scene Ledger, sample-first generation, plan/scene/review gates and evidence-based final review;
- its Qwen/Wan/Omni/embedding cloud operations require configured API access and must remain optional;
- DashScope must not become a baseline UV Studio dependency where adequate local/free execution exists;
- OpenClaw is no longer a mandatory/preferred hop for every capability;
- Stage 3 is now Capability Registry & Adapters with direct MCP/local/native/OpenClaw/Qwen adapters as peers;
- Qwen-MM-Plugins currently requiring WSL2 for its supported Windows path prevents it from being required on UV Studio's native-Windows startup path.

See `docs/architecture/QWEN_MM_PLUGINS_EVALUATION.md` and decisions D-011/D-012.

## Verification status

Latest fully observed head before the final documentation commits:

- branch head `7cf295f5f14fb37f37678ea053a9037e62d305d5`;
- CI run `31462965723`;
- Ubuntu bootstrap: success;
- Ubuntu app baseline including API integration tests, HTTP smoke and production frontend build: success;
- Windows bootstrap/unit tests: success;
- Windows app baseline was still completing when this handoff text was written.

Final branch merge requires the CI run for the actual final head to pass on both operating systems.

## What works now

- reproducible pinned backend/runtime baseline;
- durable cross-chat repository handoff;
- UV Studio-owned backend entrypoint;
- canonical local Project Store;
- canonical project HTTP API;
- UV Studio-owned user-facing frontend;
- canonical Projects list/create/open flow;
- portable checksummed project export/import;
- explicit project backup primitive;
- import/download archive UI;
- existing upstream production UI retained during migration;
- cross-platform build/backend smoke coverage;
- provider-neutral architecture plan updated after Qwen-MM research.

## Deferred intentionally

- project delete/rename/conflict-clone policies;
- scheduled automatic backups;
- cloud sync;
- recipe-specific source/artifact mutation UI/API;
- Recipe Registry itself;
- Capability Registry implementation;
- direct MCP/OpenClaw/Qwen adapters;
- media-specific UV Studio recipes;
- localization/replacement of remaining upstream production screens.

Recipe-specific media/source management is intentionally deferred so Stage 1 does not invent generic media behavior before Recipe Registry defines task requirements.

## Current risks / invariants

1. Never conflate canonical `project_id` with legacy upstream session IDs.
2. Do not run forced frontend reset during normal development.
3. Keep Project Store schema universal and small.
4. Keep product filesystem/archive rules inside Project Store/archive modules; API/UI must not duplicate them.
5. Keep the large upstream film orchestrator specialized rather than central.
6. No paid provider becomes a hidden prerequisite for a workflow with a viable local/free implementation.
7. Professional editing/review policy must remain provider-neutral.
8. Optional Qwen-MM/OpenClaw integrations may not weaken native-Windows baseline support.

## Development invariant

Before any chat ends, update this file to actual repository state. Do not describe future work here as completed.
