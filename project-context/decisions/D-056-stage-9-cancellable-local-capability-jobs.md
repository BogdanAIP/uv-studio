# D-056 — Cancellable local capability jobs

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The canonical capability execution endpoint is synchronous. Local FFmpeg work is dispatched to a thread pool, but the adapter ultimately blocked in `subprocess.run`. Closing the browser request therefore did not stop a live FFmpeg process. For long renders this was a product-hardening gap: an apparent cancellation must stop actual work and must not publish a partial artifact.

Cancellation cannot be advertised generically. Some adapters are in-process Python runtimes, some are remote, and some FFmpeg compositions currently have multi-artifact side effects. A single universal "cancel" flag would overstate guarantees.

## Decision

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

Backend shutdown is itself a cancellation boundary: every active job receives its token and the backend waits boundedly for worker threads to terminate and reap their local tool process. A normal desktop/backend shutdown must therefore not knowingly leave an owned FFmpeg/FFprobe child running after the job owner disappears.

Unexpected exceptions are exposed only as a sanitized generic job failure, without traceback, absolute developer paths or secret-bearing environment data.

## Partial-output rule

A cancelled job must not publish a partial Project Store artifact. The initial allowlist contains only operations whose existing `except Exception` rollback removes generated output before re-raising, or operations that do not create a project artifact. Cancellation uses a normal UV exception type, so it participates in those rollback paths.

An operation with unproven rollback semantics stays outside the allowlist even if its underlying FFmpeg process can technically be terminated.

## Product UX

The authoritative editor master-render path now starts `video.render_edits` through the job API, polls the terminal state, exposes an explicit **Отменить рендер** action while work is active and preserves the existing successful render/browser-preview user outcome. Leaving the render surface requests cancellation for its active job; closing the backend is covered by the shutdown cancellation boundary above.

## Acceptance evidence

Accepted on exact branch head `b98d6f441214844e947ab9f714c4935ba0a9de58`.

- CI #1699 / Actions run `32064429265`: `success` on the exact head. This includes Linux and Windows unit/API integration, shipping Python 3.13.14 compatibility, real-media FFmpeg evidence, production Next build and Chromium user outcomes. The pre-existing real browser master-render outcome passed unchanged while the product UI used the new `job -> polling -> result` execution path.
- Stage 9 Windows Release #66 / Actions run `32064429227`: `success` on the exact head. The frozen portable bundle, deep D-044 manifest verification, same-size tamper rejection, desktop supervision, pinned NSIS installer, silent install/installed launch/uninstall and versioned A -> B -> A update/rollback all passed.
- The preceding core-cancellation head `1ae4e7bcde01fc7e78fa0f4f2ea21b4144106389` independently passed CI #1697 and Windows Release #64, including a provisioned real FFmpeg process that was cancelled before its nominal 30-second input completed.

## Acceptance criteria

1. a real long-running child process is terminated after cancellation and cannot perform a delayed write;
2. the provisioned real-media suite proves the same cancellation path against an actual FFmpeg process whose nominal input duration is much longer than the cancellation interval;
3. timeout remains distinguishable from cancellation;
4. injected synchronous adapter runners continue to work unchanged when no cancellation token is supplied;
5. cancellation restores the request-local adapter runner in `finally`;
6. an FFmpeg operation that has opened a partial output removes that output and publishes no Project Store artifact when `CapabilityExecutionCancelled` propagates;
7. job start/cancel/poll reaches terminal `cancelled` with no result artifact;
8. successful jobs return the existing capability execution envelope;
9. cross-project job access fails closed;
10. unsupported local/remote/in-process operations are not falsely advertised as cancellable;
11. backend shutdown requests cancellation for all active jobs and waits for their workers to exit;
12. the ordinary synchronous `/execute` API remains backward-compatible;
13. unit, API integration and real-media suites pass on Linux and Windows, including the shipping Python runtime;
14. the real editor master-render user outcome remains green through the job API and the installed Windows product retains its complete install/update/rollback proof.

All acceptance criteria are satisfied by the evidence above.

## Follow-up boundary

Transactional cancellation for excluded long operations (`timeline.assemble`, `video.render_dubbing`) remains fail-closed until their rollback semantics are strengthened and tested. Resource/weak-hardware and long-project evidence is handled separately by D-057 rather than broadening this decision.
