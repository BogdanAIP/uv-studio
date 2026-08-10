# Next Task

**Primary target:** finish the durable-storage portion of Stage 1 with safe project archive export/import and explicit backup/recovery primitives before introducing Recipe Registry.

## Why this comes next

Canonical projects now exist in the local Project Store, are available over HTTP, and are visible in the UV Studio frontend. Before workflows begin attaching more state to projects, the project directory must be safely movable and recoverable.

Portability/recovery should be implemented while the project format is still small rather than after media-specific recipes make recovery behavior harder to define.

## Do first

1. Add a UV Studio-owned archive module around `ProjectStore`.
2. Define archive format/version metadata without changing `project.json` schema v1 unnecessarily.
3. Export one complete project directory to ZIP while preserving project-relative paths.
4. Import an archive through a temporary staging directory and validate canonical `project.json` before committing it into the Project Store.
5. Reject archive path traversal, absolute paths, symlinks/hardlinks or other entries that could escape the destination.
6. Reject duplicate project IDs by default; do not silently overwrite an existing project.
7. Add an explicit backup helper that creates a timestamped project archive in a configured backup directory.
8. Ensure an interrupted/failed import leaves no partial canonical project directory.
9. Add tests for round-trip export/import, nested files, duplicate ID, malformed project metadata, malicious ZIP paths and simulated commit failure.
10. Document the archive/recovery contract.

## Suggested files

- `uv_studio/projects/archive.py`
- updates to `uv_studio/projects/__init__.py`
- `tests/test_project_archive.py`
- `docs/PROJECT_ARCHIVES.md`
- optional small API/tool wrapper only if it remains thin and does not enlarge this slice unnecessarily.

## Proposed archive shape

```text
<project-id>.uvproj.zip
├── .uv-project-archive.json
└── project/
    ├── project.json
    ├── sources/
    ├── assets/
    ├── tasks/
    ├── artifacts/
    ├── timeline/
    ├── reviews/
    └── exports/
```

Archive manifest should at minimum record:

```text
archive_schema_version
project_id
project_schema_version
created_at
```

## Acceptance criteria

- a project containing nested files exports and imports with identical canonical metadata and file contents;
- import validates the project before replacing/moving anything into the canonical project root;
- malicious ZIP entries cannot escape staging/project root;
- duplicate project IDs fail explicitly unless a future separate conflict policy is deliberately added;
- failed import leaves existing projects and unrelated files untouched;
- backup creation is deterministic in behavior and explicit about its output path;
- no SQLite/cloud service is introduced;
- no files under `vendor/videoclaw-app` are modified;
- tests pass on Windows and Linux.

## Explicitly out of scope for this slice

- Recipe Registry;
- project delete/rename;
- automatic scheduled backups;
- cloud sync;
- frontend archive buttons unless the core archive contract is already complete and adding thin UI does not broaden the slice;
- media upload management;
- OpenClaw integration;
- music/dubbing/range-edit workflows.

After this slice, Stage 1 can move to its final UI/source-management details or be closed if the remaining items are better owned by later recipes. Stage 2 then begins with Recipe Registry.