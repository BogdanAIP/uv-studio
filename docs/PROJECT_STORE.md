# UV Studio Project Store

UV Studio owns canonical project state independently of chat sessions, VideoClaw sessions and editor-engine files.

## Current role

Project Store is the product authority for:

- versioned `project.json` metadata;
- project-owned source/media references;
- typed workflow state under `timeline/` and `reviews/`;
- project artifacts/exports;
- portable `.uvproj.zip` archive export/import;
- atomic local persistence and schema migration checks.

MLT project data, FFmpeg commands, provider credentials and host-specific runtime configuration are not canonical project state.

## Project layout

```text
projects/
└── prj_<id>/
    ├── project.json
    ├── sources/
    ├── assets/
    ├── tasks/
    ├── artifacts/
    ├── timeline/
    ├── reviews/
    └── exports/
```

The default development root is `data/projects/`; `UV_STUDIO_PROJECTS_DIR` can move it.

## `project.json`

The universal schema remains deliberately small. It holds project identity/title/recipe, timestamps, general settings, source/artifact references and namespaced extensions. Specialized edit/dubbing/review state uses dedicated typed/versioned documents instead of making every workflow field mandatory in one universal JSON object.

## References and paths

`ProjectReference.path` is canonical project-relative data using `/` separators. Absolute paths, parent traversal and path escape are rejected. File-consuming operations additionally restrict allowed top-level roots and resolved symlinks.

Source and prepared-audio APIs register project-owned files with media facts such as duration/size/hash. Current audit debt: critical Review/Accept/render boundaries must verify current file bytes where stored SHA identity is relied on; metadata hash alone must not become proof that a file was never externally changed.

## Atomicity and concurrency

Metadata/state writers use atomic replacement and a process-local re-entrant Project Store lock for coordinated updates. Atomic file replacement prevents partial JSON writes.

The current product assumes one backend process owns a Project Store. Multi-process concurrency is not yet a support claim; if introduced later it requires explicit inter-process locking/revision semantics rather than relying on the current in-process lock.

## Portable archives

Project archive export/import is implemented. See `docs/PROJECT_ARCHIVES.md` for manifest hashing, traversal/symlink checks, staged validation and atomic import behavior.

## Current APIs/UI

UV-owned project APIs support create/list/read/update plus archive import/export and project-owned media workflows. The canonical frontend exposes `/projects` and `/projects/[projectId]`.

The complete legacy VideoClaw FastAPI application is not the Project Store runtime authority and is not mounted by default.

## Remaining general hardening

`settings`, `extensions` and generic reference `metadata` intentionally remain flexible JSON-like mappings. Durable feature-specific state should continue to use explicit typed/versioned models. A future hardening slice should recursively reject non-finite/non-JSON/non-portable values before persistence without turning the small universal schema into one giant media ontology.
