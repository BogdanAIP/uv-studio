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

Export creates one stable project snapshot under the same shared cross-runtime project mutation fence used by canonical Project transactions. The fence freezes canonical Project metadata and every participating publisher while export samples the raw schema and enumerates the project filesystem.

The live fence is a concurrency boundary, not a crash transaction. Current publication recovery therefore adds fail-closed durable evidence for states that can survive process loss.

Historical UV-owned media names remain a compatibility fallback. A regular file in a managed media root (`sources/`, `assets/`, `artifacts/` or `exports/`) whose UV-owned name starts with `src_`, `art_` or `aud_` must already be represented by the frozen Project `sources`/`artifacts` references. Current self-identifying WebVTT `sub_<uuid>` and Generation `generated_attempt_<uuid>` outputs follow the same fail-closed archive rule when they exist without a ProjectReference. Ordinary unregistered project files with unrelated names remain portable and are not reclassified as transient content.

`timeline.assemble` needs a separate mechanism because its public contract permits an arbitrary caller-selected output name. Rendering remains staged at the Project Store root. Inside the final shared project fence, immediately before the canonical `os.replace`, the publisher writes a durable `tasks/pub_<uuid>.json` managed-publication marker containing the exact canonical output path and expected reference identity. Normal completion removes the marker only after the matching ProjectReference is durable. If export acquires the project fence and any validated publication marker remains, export fails closed instead of snapshotting the project. Startup reconciliation clears a stale marker for an already registered output or moves an unregistered interrupted output outside the canonical project tree before clearing the marker.

WebVTT subtitle export renders to staging outside the project tree and publishes `artifacts/sub_<uuid>.vtt` under the shared fence. If ordinary exception cleanup can prove metadata did not commit, canonical bytes are removed immediately. If the process dies after the final move, startup reconciliation identifies an unregistered `sub_<uuid>` output, moves it to a quarantine file at the Project Store root and leaves the canonical project free of orphan subtitle bytes. Export also rejects such an unreconciled self-identifying orphan.

Named Generation stages provider output outside every canonical project directory. The executor receives the staging `Path`, not `artifacts/generated_<attempt>.*`. After a non-empty regular output is validated, Generation acquires the shared project fence, revalidates the durable Job state and final path, then publishes bytes, Project artifact metadata, Take state and Job success through their existing authorities.

Generation restart recovery explicitly handles the durable intermediate states that can remain if the process dies inside that final sequence:

- bytes without ProjectReference: the self-identifying generated output is moved out of the project tree and the running Job is failed/retryable; no provider work is replayed;
- durable artifact ProjectReference but no Take: recovery validates the exact artifact provenance/bytes, creates the missing Take through the normal Production command and marks the same Job/Attempt succeeded;
- durable artifact + matching Take while Job is still running: recovery reuses that Take and marks the same Job/Attempt succeeded;
- already succeeded Job: no materialization is replayed.

Archive export rejects generation artifact provenance unless the matching durable Job is already `succeeded` with the same attempt, output reference and Take identity. This prevents an artifact or visible Take from being silently archived while its Job still claims `RUNNING`/failed outcome.

Before publication reconciliation, startup invokes ProjectUnitOfWork history recovery. A crash during an artifact/Take transaction is therefore resolved to its exact durable UOW state before Generation decides whether to complete locally or fail the abandoned Job.

Source-media upload keeps its existing proactive boundary. Request bytes stream first into an exclusive staging file at the Project Store root, outside every canonical project directory. Only after upload completion does source publication acquire the shared project fence; final move, FFprobe validation, portable metadata derivation, source registration and ordinary failure cleanup remain inside that fence. The historical `src_` archive fallback stays fail-closed for a source file that survives without its ProjectReference.

For every accepted portable file, export computes size and SHA-256 while streaming that exact byte sequence directly into the ZIP. It does not hash one live read and later perform a second live read for ZIP capture. A concurrent non-authoritative file change can therefore either cause export to fail while opening/capturing the file or produce a manifest record for exactly the bytes stored in the ZIP; it cannot produce a two-read hash/ZIP mismatch.

Export:

1. checks the lexical technical lock path and fails closed if it is a symlink;
2. acquires the shared project mutation fence;
3. loads and validates canonical `project.json` and samples its raw schema;
4. enumerates project entries and rejects symlinks/special filesystem entries;
5. rejects any validated pending `pub_<uuid>` managed-publication marker;
6. excludes only the ordinary technical `tasks/.uv-task-records.lock` coordination file from the portable snapshot;
7. rejects an unregistered self-identifying UV publication (`src_`, `art_`, `aud_`, `sub_`, `generated_attempt_`);
8. rejects a Generation artifact whose durable Job does not match a completed success outcome;
9. streams every accepted portable regular file once into the ZIP while computing the manifest size and SHA-256 from those exact bytes;
10. writes the manifest describing those captured bytes;
11. atomically replaces the requested archive destination when complete.

The destination may not be inside the project being archived. That prevents a backup from recursively including itself.

An export rejected because publication/recovery is incomplete is not a corrupt backup: no destination archive is committed. Restart/reconciliation resolves current `timeline.assemble`, WebVTT and Generation crash states without replaying renderer/provider work; the caller can retry export after reconciliation completes.

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
11. compare manifest `project_schema_version` with the raw staged `project.json` schema before migration;
12. parse/migrate/validate staged `project.json` and require project identity to agree;
13. atomically rename the validated staged directory into the canonical store.

A duplicate `project_id` fails. Import never silently replaces an existing project. Historical schema-v1 project bytes remain exact archive authority on import/re-export while the in-memory Project view migrates to the current schema.

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

A portable archive is a complete project-level recovery unit for canonical recoverable project state. Runtime coordination artifacts such as the ordinary technical lock file are recreated by the Project Store and are not part of the portable recovery payload. Pending publication markers are not valid archive state: export refuses them until restart reconciliation has produced either registered canonical state or quarantined non-canonical evidence.

Conflict/clone/replace policies, if later added, must be explicit operations rather than weakening this fail-closed import contract.
