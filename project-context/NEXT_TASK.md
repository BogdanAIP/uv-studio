# Next Task

**Primary target:** begin Stage 1 with a minimal, versioned UV Studio Project Store schema and atomic local persistence.

## Do first

1. Create UV Studio-owned project models outside `vendor/`.
2. Define `project.json` schema version 1 with stable project ID, title, recipe ID, timestamps, settings, source references, artifact references and extension namespace.
3. Implement atomic create/read/update operations using a temporary file + replace strategy.
4. Reject invalid project IDs and path traversal.
5. Add explicit schema-version validation and a migration boundary even though only version 1 exists initially.
6. Add unit tests for create/read/update, atomic replacement behavior, malformed JSON, unsupported schema versions and path safety.
7. Do not add SQLite unless file-based persistence proves insufficient.

## Expected files

Suggested:

- `uv_studio/__init__.py`
- `uv_studio/projects/__init__.py`
- `uv_studio/projects/models.py`
- `uv_studio/projects/store.py`
- `uv_studio/projects/migrations.py`
- `tests/test_project_store.py`
- `docs/PROJECT_STORE.md`

## Initial on-disk shape

```text
projects/
└── <project-id>/
    ├── project.json
    ├── sources/
    ├── assets/
    ├── tasks/
    ├── artifacts/
    ├── timeline/
    ├── reviews/
    └── exports/
```

Directories may be created lazily where that reduces empty scaffolding, but `project.json` is canonical project metadata.

## Acceptance criteria

- project creation generates a stable ID and valid `project.json`;
- project data can be loaded after process restart;
- updates are atomic and do not rewrite vendored upstream state;
- invalid IDs/path traversal cannot escape the configured project root;
- unsupported schema versions fail explicitly rather than being silently interpreted;
- tests pass on Linux and Windows;
- no VideoClaw session JSON is used as canonical UV Studio project state;
- no cloud/database service is required.

## Explicitly out of scope for this slice

- Projects frontend UI;
- ZIP import/export;
- backup rotation;
- Recipe Registry implementation;
- OpenClaw integration;
- video/music/dubbing features;
- migration of existing VideoClaw sessions;
- SQLite or multi-user storage.

Keep the first Stage 1 slice deliberately small and durable: establish the canonical local project file and safe persistence boundary first.