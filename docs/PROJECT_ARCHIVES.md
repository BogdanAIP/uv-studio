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

Export creates one stable project snapshot under the same shared cross-runtime project mutation fence used by canonical Project transactions. The fence freezes canonical Project metadata and every participating publisher while export recovers any crash-left prepared ProjectUnitOfWork state, derives validated Redo authority, samples the raw schema and enumerates the project filesystem.

The live fence is a concurrency boundary, not a crash transaction. Current publication recovery therefore adds fail-closed durable evidence for states that can survive process loss.

Long-running Generation, source upload, WebVTT, FFconcat and `timeline.assemble` work uses transient staging at the Project Store root, outside every canonical project directory and therefore outside the archive payload. Current writers pair each reserved staging name with a sidecar lease whose one-byte OS lock is held for the staging lifetime. Application startup performs a root-only, non-recursive lease recovery before project-scoped publication/Generation recovery: only exact current UV staging names whose lease can be acquired non-blockingly are reclaimed. A locked lease identifies a live concurrent writer and is preserved. Unknown/malformed files, project directories, symlinks/non-files, quarantine evidence and exact-looking legacy staging without a lease are not guessed stale or deleted. These root staging paths and leases are runtime coordination state, not Project/Production/Generation authority.

Historical UV-owned media names remain a compatibility fallback. A regular file in a managed media root (`sources/`, `assets/`, `artifacts/` or `exports/`) whose UV-owned name starts with `src_`, `art_` or `aud_` must already be represented by the frozen Project `sources`/`artifacts` references or by a full validated ProjectReference reachable through the current durable Redo suffix. Current self-identifying WebVTT `sub_<uuid>` and Generation `generated_attempt_<uuid>` outputs follow the same fail-closed archive rule. Ordinary unregistered project files with unrelated names remain portable and are not reclassified as transient content.

Redo reachability is not pathname authority and not merely the presence of committed historical `after` snapshots. `ProjectUnitOfWork` simulates the complete Redo suffix from the current cursor across every changed canonical document, requires each recorded `before` snapshot to equal the simulated current state, then applies the corresponding `after` state. An otherwise well-formed but unreachable journal chain therefore cannot become archive/startup preservation authority.

`ProjectUnitOfWork` snapshots canonical JSON rather than binary media, so an undone `generation.register_output` intentionally leaves its already-published bytes in place while the transaction remains reachable through `history.entries[history.cursor:]`. Export reconstructs full historical ProjectReferences from that exact reachable Redo chain. Metadata on one stable reference may legitimately evolve through later canonical commands such as `production.accept_take`; archive/recovery accepts those variants only when reference ID, path and kind remain stable and every Generation variant resolves to the same immutable durable Job/Attempt/size/SHA materialization authority. Path reuse by another reference, path/kind drift, source/artifact role drift, Generation/non-Generation classification drift or Generation provenance drift fails closed. Archive applies the stricter successful-attempt/output-reference/Take authority before accepting a Generation payload as portable. A later canonical commit truncates the Redo suffix and removes this protection automatically.

Generation metadata is a reserved ProjectReference authority namespace, including before a Job attempt is durably succeeded. If `metadata.generation` is present it must be a JSON object with safe Job/Attempt identifiers, a Generation contract and continuation lineage that exactly matches `continuation_source_reference_id`. Generation references remain under `Project.artifacts`, never `Project.sources`. An artifacts-root Generation path must be the direct canonical `artifacts/generated_<attempt>...` shape rather than a nested artifacts path. While the same Generation reference ID remains present, generic canonical mutation may add unrelated metadata such as Production acceptance bindings but may not change its path/kind or strip/rebind `metadata.generation`; complete removal through Undo remains allowed, and later Redo re-addition is independently validated against durable Job/Attempt and exact bytes.

`timeline.assemble` needs a separate mechanism because its public contract permits an arbitrary caller-selected output name. Rendering remains staged at the Project Store root. Inside the final shared project fence, immediately before the canonical `os.replace`, the publisher writes a durable `tasks/pub_<uuid>.json` managed-publication marker containing the exact canonical output path and expected reference identity. Normal completion removes the marker only after the matching ProjectReference is durable. If export acquires the project fence and any validated publication marker remains, export fails closed instead of snapshotting the project. Startup reconciliation clears a stale marker only when a registered ProjectReference matches both the marker path and its expected `reference_id`. A dangling or historical reference that merely reuses the same path cannot claim crash-left bytes for a different publication identity; those bytes are moved outside the canonical project tree before the marker is cleared.

WebVTT subtitle export renders to staging outside the project tree and publishes `artifacts/sub_<uuid>.vtt` under the shared fence. If ordinary exception cleanup can prove metadata did not commit, canonical bytes are removed immediately. If the process dies after the final move, startup reconciliation identifies an unregistered `sub_<uuid>` output, moves it to a quarantine file at the Project Store root and leaves the canonical project free of orphan subtitle bytes. Export also rejects such an unreconciled self-identifying orphan.

Named Generation stages provider output outside every canonical project directory. The executor receives the staging `Path`, not `artifacts/generated_<attempt>.*`. After a non-empty regular output is validated, Generation acquires the shared project fence, revalidates the durable Job state and final path, then publishes bytes, Project artifact metadata, Take state and Job success through their existing authorities. Generation Job start/succeed/fail/cancel transitions use this same cross-runtime fence, so another runtime cannot cancel/fail the Job inside the consequence-bearing publication critical section.

Generation restart recovery explicitly handles durable intermediate and historical states that can remain after process loss or an older accepted runtime:

- bytes without ProjectReference: the self-identifying generated output is moved out of the project tree and the running Job is failed/retryable; no provider work is replayed;
- durable artifact ProjectReference with no committed Take history: recovery validates exact persisted bytes/provenance, creates the missing Take through the normal Production command and records success for the artifact-owning attempt;
- durable artifact + matching live Take before Job success: recovery validates and reuses that exact Take, then records success without provider replay;
- durable artifact + a historically committed Take that was later explicitly removed by a committed user Undo: recovery preserves the original historical `take_id`, does not recreate a current Take, and records success for the artifact-owning attempt while leaving Production Semantics in the user's undone state;
- durable Take registration history with no matching current Take and no authoritative latest Undo is inconsistent and fails closed rather than inventing a replacement Take;
- a legacy `FAILED` or `CANCELLED` attempt that already has a durable artifact: recovery may repair that exact attempt to `SUCCEEDED` after strict byte/provenance validation;
- a legacy older-attempt artifact followed by a newer retry: the artifact remains owned by its historical attempt. Recovery repairs the older attempt in place and does not rewrite identity to make the artifact belong to `attempts[-1]`; the newer attempt and the Job's current overall status remain authoritative for current execution state;
- an artifact absent from current Project state only because `generation.register_output` is currently undone: startup derives its full historical ProjectReference from the validated Redo suffix and verifies immutable durable Generation materialization provenance plus exact size/SHA-256 before preserving the bytes for future Redo. If the owning legacy attempt is still `RUNNING`, `FAILED` or `CANCELLED`, startup preserves the user's Undo and does not claim completed Generation authority or recreate the Take. Explicit retry remains blocked while that validated redo-owned materialization is reachable. An explicit user Redo may restore the exact reference after binary validation, after which ordinary recovery can complete the local materialization without provider replay; changed/truncated/replaced bytes fail closed before publication/quarantine recovery mutates the project;
- already succeeded attempt: materialization is not replayed.

Retry/fail/cancel is rejected while any attempt of that Job owns a durable artifact that has not yet been reconciled as that attempt's success. Retry detection includes a validated artifact reachable only through the current durable Redo suffix, so an explicit Undo cannot accidentally authorize a duplicate provider run while the historical output remains recoverable. This prevents current code from creating new versions of the historical split state.

Recovery does not treat a merely non-empty file as success evidence. It checks the ProjectReference's persisted `size_bytes` and SHA-256 against the canonical file and verifies durable generation identity/provenance against the Job: Job ID, the artifact's own Attempt ID, model, capability/offer/adapter execution mapping, request digest and generation contract must agree before a Take can be created/reused or that attempt can be recorded as successful. Pending attempts are also subject to the ProjectReference reserved-namespace, safe-ID, direct-artifacts-path and lineage boundary before reconciliation can run. When Take registration history exists, the same durable ProjectUnitOfWork transaction/operation journals decide whether the historical Take should still exist or was intentionally undone.

Generation Job records intentionally remain outside user Undo/Redo history. A successful attempt's `take_id` is therefore immutable historical provenance, not proof that the Take still exists in current Production Semantics. Archive export resolves the current Production document for each Generation artifact, including an artifact reconstructed only from the Redo suffix. If the named Take exists, it must belong to the Job's Shot and point to the exact artifact. If it does not exist, export accepts that absence only when durable ProjectUnitOfWork journals prove that a `production.register_take` transaction created the exact Take and a committed Undo later removed it. That proof survives stale redo-branch truncation by later user work. Out-of-band Take deletion, wrong Shot/reference, ambiguous history, or a later Redo fails closed.

Archive export independently validates every Generation ProjectReference against the exact durable attempt named by its provenance rather than requiring all artifacts to match the Job's final attempt. The artifact-owning attempt must itself be `succeeded`, point back to that artifact and carry the historical Take identity. This allows a recoverable historical attempt artifact to remain portable even when a later retry is current or failed, without weakening current Job status semantics. A redo-only incomplete legacy materialization is protected for recovery and explicit Redo but remains non-exportable until completed Generation authority is established.

Archive also validates the same Job/request provenance and compares each Generation artifact's persisted size/SHA-256 with the size/SHA-256 computed while streaming the exact bytes into the ZIP. A file changed after successful generation therefore causes export to fail; the archive's own manifest hash cannot silently replace the Generation artifact's original digest authority. This check applies equally to live and redo-only Generation references.

Direct `ProjectUnitOfWork.redo()` uses the binary materialization authority boundary. Before **every** Redo completes, it determines the Project state that will remain live after that operation and validates every live Generation ProjectReference against durable Job/Attempt/provenance and the currently stored output size/SHA-256. A Redo may therefore restore an exact recovery-compatible legacy materialization whose attempt is not yet marked successful, but that does not manufacture success or Take authority; local recovery establishes those stricter fields after the reference is live. This validation also applies when the Redo itself changes only Production Semantics or Timeline state. Therefore a valid artifact Redo followed by media-byte substitution cannot be followed by a Production-only Redo that restores a historical Take around altered bytes.

Before publication reconciliation, application startup invokes ProjectUnitOfWork history recovery. A crash during an artifact/Take transaction is therefore resolved to its exact durable UOW state before Generation decides whether to complete locally or fail the abandoned Job. Archive export performs the same recovery while already holding the project fence and before sampling Project state, raw schema or filesystem membership.

Source-media upload keeps its existing proactive boundary. Request bytes stream first into an exclusive staging file at the Project Store root, outside every canonical project directory. Only after upload completion does source publication acquire the shared project fence; final move, FFprobe validation, portable metadata derivation, source registration and ordinary failure cleanup remain inside that fence. Hard process loss can bypass the ordinary exception handler after the final move, so startup reconciliation also scans `sources/` for unregistered self-identifying `src_<uuid>.*` outputs and moves them to quarantine outside the project tree. Registered source references are preserved. The `src_` archive fallback stays fail-closed before reconciliation.

For every accepted portable file, export computes size and SHA-256 while streaming that exact byte sequence directly into the ZIP. It does not hash one live read and later perform a second live read for ZIP capture. A concurrent non-authoritative file change can therefore either cause export to fail while opening/capturing the file or produce a manifest record for exactly the bytes stored in the ZIP; it cannot produce a two-read hash/ZIP mismatch. For Generation outputs, that exact streamed size/hash must additionally equal the persisted Generation artifact size/digest.

Export:

1. checks the lexical technical lock path and fails closed if it is a symlink;
2. acquires the shared project mutation fence;
3. recovers any crash-left prepared ProjectUnitOfWork state and validates the exact reachable current Redo suffix before sampling archive state;
4. reconstructs full redo-owned source/artifact ProjectReferences, accepting canonical metadata evolution only when stable identity/path/kind and immutable Generation materialization authority agree and otherwise failing closed;
5. loads and validates canonical `project.json` and samples its raw schema;
6. enumerates project entries and rejects symlinks/special filesystem entries;
7. rejects any validated pending `pub_<uuid>` managed-publication marker;
8. excludes only the ordinary technical `tasks/.uv-task-records.lock` coordination file from the portable snapshot;
9. rejects an unregistered self-identifying UV publication (`src_`, `art_`, `aud_`, `sub_`, `generated_attempt_`) unless current or validated redo reference authority owns that exact path;
10. requires every live or redo-only Generation artifact to resolve to its own durable successful attempt, exact output-reference/Take authority or exact durable Take-Undo evidence, matching Job/request/provenance/lineage and persisted size/SHA-256;
11. streams every accepted portable regular file once into the ZIP while computing the manifest size and SHA-256 from those exact bytes and, for Generation artifacts, requires the streamed size/hash to equal persisted Generation artifact authority;
12. writes the manifest describing those captured bytes;
13. atomically replaces the requested archive destination when complete.

The destination may not be inside the project being archived. That prevents a backup from recursively including itself.

An export rejected because publication/recovery is incomplete is not a corrupt backup: no destination archive is committed. Restart/reconciliation resolves current source-upload, `timeline.assemble`, WebVTT and live Generation crash states without replaying renderer/provider work; redo-only incomplete Generation state remains protected until explicit Redo makes it current or later canonical work intentionally truncates its Redo branch. If Generation bytes or provenance disagree with durable authority, recovery/export/Redo fail closed rather than promoting, archiving or restoring altered media.

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
12. parse/migrate/validate staged `project.json` and require project identity and reserved Generation reference invariants to agree;
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

A portable archive is a complete project-level recovery unit for canonical recoverable project state. Runtime coordination artifacts such as the ordinary technical lock file are recreated by the Project Store and are not part of the portable recovery payload. Pending publication markers are not valid archive state: export refuses them until restart reconciliation has produced either an exact matching registered canonical identity or quarantined non-canonical evidence. Redo-owned binary payload is portable only while the exact reachable durable Redo suffix still carries full stable owning reference authority; Generation payload additionally must match reserved Generation ProjectReference shape, durable successful Job/Attempt/output-reference/Take/provenance/lineage and exact size/SHA-256.

Conflict/clone/replace policies, if later added, must be explicit operations rather than weakening this fail-closed import contract.
