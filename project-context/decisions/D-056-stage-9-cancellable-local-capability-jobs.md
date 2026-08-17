# D-056 — Cancellable local capability jobs

- **Status:** Proposed
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The canonical capability execution endpoint is synchronous. Local FFmpeg work is dispatched to a thread pool, but the adapter ultimately blocks in `subprocess.run`. Closing the browser request therefore does not stop a live FFmpeg process. For long renders this is a product-hardening gap: an apparent cancellation must stop actual work and must not publish a partial artifact.

Cancellation cannot be advertised generically. Some adapters are in-process Python runtimes, some are remote, and some FFmpeg compositions currently have multi-artifact side effects. A single universal "cancel" flag would overstate guarantees.

## Proposed decision

Add an explicit, process-local capability job contract beside the existing synchronous `/execute` compatibility endpoint.

The first contract is limited to free/local `local_ffmpeg` offers whose operation has a proven rollback-safe process boundary. The adapter owns an explicit allowlist; unsupported operations fail closed with `capability_job_cancellation_not_supported`.

Initial proven operations are:

- `media.probe`;
- `video.extract_range`;
- `video.replace_range`;
- `video.render_edits`;
- `video.render_music_video`;
- `video.preview_artifact`;
- `audio.measure_loudness`;
- `video.compose_photos`;
- `audio.visualize`.

`timeline.assemble` is initially excluded because its current synchronous failure path does not remove a partially opened output file. `video.render_dubbing` is initially excluded because it may materialize and register a visual master before the final dubbing render; cancellation of the later process is not yet a transaction over that earlier side effect. They may enter the allowlist only after their rollback semantics are strengthened and tested.

## Process boundary

A `CancellationToken` is shared between the job and adapter. For cancellable execution the request-local `LocalFFmpegAdapter` temporarily replaces its delegate runner with a `Popen`-backed `CancellableProcessRunner` and restores the previous runner in `finally`.

The process runner:

1. starts argv directly with `shell=False`;
2. polls the cancellation token while preserving the existing operation timeout;
3. on cancellation calls `terminate()` on the launched tool;
4. waits for a bounded grace interval and escalates to `kill()` if necessary;
5. reaps the child before raising `CapabilityExecutionCancelled`.

This decision proves the launched tool process boundary. It does not claim recursive termination of arbitrary descendant process trees.

## Job API

- `POST /api/uv/projects/{project_id}/capabilities/{capability_id}/jobs` starts a proven cancellable job and returns `202`;
- `GET /api/uv/projects/{project_id}/capability-jobs/{job_id}` reads status/result;
- `POST /api/uv/projects/{project_id}/capability-jobs/{job_id}/cancel` requests cancellation.

States are `queued`, `running`, `cancelling`, `succeeded`, `failed`, `cancelled`.

The existing selection and one-shot authorization preparation are reused. Job records do not persist request input or authorization tokens. Completed results reuse `CapabilityExecutionEnvelope` rather than inventing a second result schema.

Jobs are deliberately process-local and ephemeral. Backend restart does not resume them; canonical Project Store outputs remain the durable state. The job registry is bounded and prunes old terminal jobs. A job id is project-scoped; cross-project reads and cancellation fail as not found.

Unexpected exceptions are exposed only as a sanitized generic job failure, without traceback, absolute developer paths or secret-bearing environment data.

## Partial-output rule

A cancelled job must not publish a partial Project Store artifact. The initial allowlist contains only operations whose existing `except Exception` rollback removes generated output before re-raising, or operations that do not create a project artifact. Cancellation uses a normal UV exception type, so it participates in those rollback paths.

An operation with unproven rollback semantics stays outside the allowlist even if its underlying FFmpeg process can technically be terminated.

## Acceptance criteria

1. a real long-running child process is terminated after cancellation and cannot perform a delayed write;
2. timeout remains distinguishable from cancellation;
3. injected synchronous adapter runners continue to work unchanged when no cancellation token is supplied;
4. cancellation restores the request-local adapter runner in `finally`;
5. an FFmpeg operation that has opened a partial output removes that output and publishes no Project Store artifact when `CapabilityExecutionCancelled` propagates;
6. job start/cancel/poll reaches terminal `cancelled` with no result artifact;
7. successful jobs return the existing capability execution envelope;
8. cross-project job access fails closed;
9. unsupported local/remote/in-process operations are not falsely advertised as cancellable;
10. the ordinary synchronous `/execute` API remains backward-compatible;
11. unit and API integration suites pass on Linux and Windows, including the shipping Python runtime.

## Follow-up boundary

After this first contract is green, extend transactional cancellation to excluded long operations (`timeline.assemble`, `video.render_dubbing`) before product UI exposes cancellation for them. Resource/weak-hardware evidence remains a separate Stage 9 hardening concern.
