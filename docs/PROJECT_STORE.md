# UV Studio Project Store v1

UV Studio project state is owned by UV Studio and is independent from the pinned VideoClaw session/chat storage.

## Goals

- local-first;
- durable across process restarts and ChatGPT chat changes;
- human-readable canonical metadata;
- atomic metadata updates;
- explicit schema versioning;
- portable project-relative media references;
- no mandatory database or cloud service.

## Default conceptual layout

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

`ProjectStore` accepts an explicit project root. During development the default is `data/projects/` under the repository root. It can be overridden with `UV_STUDIO_PROJECTS_DIR`; tests use temporary roots.

## `project.json` schema v1

Example:

```json
{
  "schema_version": 1,
  "project_id": "prj_0123456789abcdef",
  "title": "Example video",
  "recipe_id": "general_video",
  "created_at": "2026-08-10T12:00:00Z",
  "updated_at": "2026-08-10T12:00:00Z",
  "settings": {
    "aspect_ratio": "16:9"
  },
  "sources": [
    {
      "id": "src_main",
      "kind": "source",
      "path": "sources/input.mp4",
      "metadata": {}
    }
  ],
  "artifacts": [],
  "extensions": {}
}
```

## Why the schema is deliberately small

Fields such as song structure, character state, continuity, dubbing, advertising rules, or take review are not mandatory project fields.

Specialized modules can use `extensions` for small namespaced metadata or store larger versioned documents in dedicated files/directories and reference them from project metadata.

This prevents the universal project format from becoming a film/music ontology.

## References

`ProjectReference.path` is project-relative and canonicalized with `/` separators.

Rejected examples:

```text
../outside.mp4
C:\outside.mp4
/absolute/path.mp4
```

External-original paths, URLs or provider identifiers should be recorded as metadata when needed; project-managed paths remain relative so project export/import can be implemented later.

## Atomic writes

`project.json` updates use:

```text
serialize
 ↓
write temporary file in same directory
 ↓
flush + fsync
 ↓
os.replace(temp, project.json)
```

If replacement fails, the previous canonical file remains unchanged and the temporary file is removed.

Atomic replacement protects against partial metadata writes; it is not a substitute for future revision/conflict handling if concurrent multi-process editing is added.

## Corruption visibility

Directories without `project.json` are not treated as projects and may be ignored during listing.

A directory that does contain `project.json` but has malformed or invalid canonical metadata is **not silently skipped**. `ProjectStore` surfaces the error so API/UI layers can tell the user the project requires recovery instead of making it appear to disappear.

## Schema migrations

All reads pass through `migrate_project_data()` before `ProjectDocument` construction.

Version 1 currently has no migration function because it is the first schema. A project created by a newer unsupported UV Studio version fails explicitly instead of being silently interpreted with an older schema.

## HTTP API

UV Studio's server mounts a product-owned router on top of the pinned upstream FastAPI application:

```text
GET   /api/uv/projects
POST  /api/uv/projects
GET   /api/uv/projects/{project_id}
PATCH /api/uv/projects/{project_id}
```

The router is intentionally thin. Validation/persistence remains in `ProjectStore`; handlers translate store errors into HTTP status codes instead of duplicating filesystem rules.

Current responses use canonical schema-v1 metadata. Create/update APIs expose only universal metadata in this slice; source/artifact mutation gets separate operations later rather than allowing arbitrary replacement of the whole project document.

The existing upstream routes, including `/api/health`, remain mounted through the UV Studio server wrapper.

## Not included yet

Current Stage 1 work still does not implement:

- Projects frontend UI;
- source/artifact upload/mutation API;
- ZIP import/export;
- backup rotation;
- SQLite;
- multi-user concurrency;
- existing VideoClaw session migration;
- Recipe Registry.
