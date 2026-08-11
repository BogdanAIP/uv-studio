# UV Studio portable project archives

UV Studio project archives are product-owned, portable backups of one complete canonical project directory.

## Format

Default file name:

```text
<project-id>.uvproj.zip
```

Archive schema v1:

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

The archive can contain additional project-relative directories/files created by future recipes, but every regular file under `project/` must be declared in the manifest.

## Manifest

`.uv-project-archive.json` records:

- `archive_schema_version`;
- `project_id`;
- `project_schema_version`;
- archive `created_at`;
- every regular file path;
- uncompressed file size;
- SHA-256 digest.

This lets import verify the entire project before it becomes canonical state.

## Export contract

Export:

1. loads and validates the canonical `project.json`;
2. rejects symlinks/special filesystem entries;
3. hashes every regular project file;
4. writes the ZIP to a temporary sibling file;
5. atomically replaces the requested archive destination when complete.

The destination may not be inside the project being archived. That prevents a backup from recursively including itself.

## Import contract

Import is fail-closed:

1. open ZIP;
2. validate entry count and uncompressed-size limits;
3. reject encrypted entries;
4. reject absolute paths, `..`, Windows drive paths and case-colliding duplicates;
5. reject symlinks/special files represented by Unix ZIP metadata;
6. require all project files to be declared in the manifest;
7. validate manifest archive schema;
8. validate `project_id` before using it as a path component;
9. extract into a temporary directory beneath the canonical Project Store root;
10. verify every extracted size and SHA-256;
11. parse/migrate/validate staged `project.json`;
12. require manifest/project identity and schema to agree;
13. atomically rename the validated staged directory into the canonical store.

A duplicate `project_id` fails. Import never silently replaces an existing project.

If any validation/extraction/final commit fails, no partial canonical project is left behind.

## Safety limits

Current defaults are deliberately high enough for media projects while still bounding hostile archives:

- up to 100,000 ZIP entries;
- up to 100 GiB total uncompressed data;
- up to 50 GiB per file;
- up to 4 MiB manifest.

The HTTP import endpoint also enforces a maximum streamed request size rather than buffering a complete archive in memory.

## API

Export:

```http
GET /api/uv/projects/{project_id}/archive
```

Returns `application/zip` and removes the temporary server-side export after the response is sent.

Import:

```http
POST /api/uv/projects/import
Content-Type: application/zip

<raw archive bytes>
```

The request body is streamed to a temporary file before validation.

Typical responses:

- `201` imported;
- `400` empty request body;
- `409` duplicate project ID;
- `413` request exceeds configured archive upload limit;
- `422` invalid/unsafe/corrupt archive.

## UI

The Projects screen supports importing `.uvproj.zip`.

Each canonical project page exposes **Скачать архив проекта**.

## Backup helper

`uv_studio.projects.create_backup()` writes a uniquely named timestamped `.uvproj.zip` into an explicitly supplied backup directory and returns the exact path.

Automatic/scheduled backups are intentionally a separate future policy. The archive primitive itself has no hidden scheduling or cloud dependency.

## Recovery rule

A portable archive is a complete project-level recovery unit. Restore into a Project Store that does not already contain the same `project_id`.

Conflict/clone/replace policies, if later added, must be explicit operations rather than weakening this fail-closed import contract.
