# UV Studio portable project archives

UV Studio project archives are product-owned, portable backups of one complete recoverable canonical project state. They include the canonical project files needed for recovery, but intentionally exclude explicitly non-portable coordination artifacts such as the ordinary technical task-record lock file described below.

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

The archive can contain additional project-relative directories/files created by future recipes. Every portable regular file under `project/` must be declared in the manifest.

`tasks/.uv-task-records.lock` is a technical cross-runtime coordination file, not recoverable project content. When that exact lexical path is an ordinary file, export omits it from the ZIP and manifest; a restored Project Store recreates coordination state as needed. If that lexical path is a symlink, export fails closed rather than treating it as the technical exception.

## Manifest

`.uv-project-archive.json` records:

- `archive_schema_version`;
- `project_id`;
- `project_schema_version`;
- archive `created_at`;
- every portable regular file path;
- uncompressed file size;
- SHA-256 digest.

This lets import verify the entire portable recovery snapshot before it becomes canonical state.

## Export contract

Export creates one stable project snapshot under the same shared cross-runtime project mutation fence used by canonical Project transactions. The fence spans raw Project-schema sampling, filesystem enumeration, hashing and ZIP capture, so a concurrent canonical mutation cannot make the manifest and archived bytes describe different project states.

Source-media upload follows the same snapshot boundary. Request bytes stream first into an exclusive staging file at the Project Store root, outside every canonical project directory. Only after the upload is complete does source publication acquire the shared project fence; the final move into `sources/`, media probe, canonical source-reference registration and failure cleanup remain inside that fence. Export therefore observes either the complete pre-publication project or the complete registered source state, never an in-progress `.upload` file or a final source file whose `project.json` reference is still waiting to commit.

Export:

1. checks the lexical technical lock path and fails closed if it is a symlink;
2. acquires the shared project mutation fence;
3. loads and validates the canonical `project.json`;
4. rejects symlinks/special filesystem entries during project enumeration;
5. excludes only the ordinary technical `tasks/.uv-task-records.lock` coordination file from the portable snapshot;
6. hashes every remaining portable regular project file;
7. writes the ZIP to a temporary sibling file;
8. atomically replaces the requested archive destination when complete.

The destination may not be inside the project being archived. That prevents a backup from recursively including itself.

The project fence is a snapshot-consistency boundary, not archive payload. Export never relies on the lock file as recoverable state and never weakens the general symlink rejection rule to omit it.

## Import contract

Import is fail-closed:

1. open ZIP;
2. validate entry count and uncompressed-size limits;
3. reject encrypted entries;
4. reject absolute paths, `..`, Windows drive paths and case-colliding duplicates;
5. reject symlinks/special files represented by Unix ZIP metadata;
6. require all archived portable project files to be declared in the manifest;
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

A portable archive is a complete project-level recovery unit for canonical recoverable project state. Runtime coordination artifacts such as the ordinary technical task-record lock file are recreated by the Project Store and are not part of the portable recovery payload. Restore into a Project Store that does not already contain the same `project_id`.

Conflict/clone/replace policies, if later added, must be explicit operations rather than weakening this fail-closed import contract.
