# D-058 — Redistributable Windows media runtime boundary

- **Status:** Proposed
- **Date:** 2026-08-18
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Stage 9 originally reused the exact Kdenlive 26.04.3 standalone package that had already proven FFmpeg/FFprobe/MLT behavior in Windows CI. That was technically correct but not sufficient for public redistribution.

The exact executable self-report from the pinned Kdenlive carrier showed FFmpeg 8.1.1 configured with both `--enable-gpl` and `--enable-nonfree`. FFmpeg upstream explicitly distinguishes `--enable-nonfree` as a build configuration that is not redistributable. Therefore the Kdenlive-carried FFmpeg/FFprobe build is rejected as a public UV Studio release input even though its runtime behavior is proven.

A temporary research PR (#39) separately proved that the product can inspect and reject this class of packaging risk and that redistributable Windows FFmpeg candidates exist. Stage 9 needs one coherent MLT + FFmpeg runtime closure whose actual shipped FFmpeg build, corresponding-source coordinates and retained service surface are mechanically recorded rather than assumed from a package name.

## Proposed decision

Use the official Shotcut portable release `26.4.30` as the Stage 9 Windows media acquisition carrier:

- binary acquisition: `shotcut-win64-26.4.30.zip` from `mltframework/shotcut` release `v26.4.30`;
- binary SHA-256: `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`;
- corresponding-source acquisition: `shotcut-src-26.4.30.txz` from the same official release;
- corresponding-source SHA-256: `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`;
- the source asset is provenance/source-offer material, not an application runtime dependency and is therefore not downloaded into every release build;
- the checked-in release profile is staged verbatim at `legal/release-inputs.windows-x86_64.json`, so these source coordinates become D-044-manifest-owned immutable evidence for every built candidate;
- the carrier contains the Windows MLT/FFmpeg runtime closure built and shipped together by the MLT/Shotcut project;
- upstream Windows build automation configures FFmpeg as shared and GPL-enabled but does not enable `--enable-nonfree`;
- UV Studio nevertheless trusts only the downloaded runtime bytes and their executable self-report, not the build-script claim.

`tools/audit_ffmpeg_release.py` is a permanent release gate. It executes the exact selected `ffmpeg.exe` with `-buildconf`, bounds the returned evidence and fails closed if `--enable-nonfree` is present. GPL/shared/static flags are recorded as evidence instead of being silently interpreted as permission.

The exact audit JSON is copied into the immutable release payload as `legal/ffmpeg-buildconf.json` before D-044 builds the release manifest. Historical installed releases therefore identify not only which FFmpeg bytes were shipped but also the configuration the executable reported during packaging.

## UV-owned MLT service closure

The Shotcut archive is an acquisition carrier, not a second editor or canonical runtime tree. The exact UV MLT path is documented in `docs/stage9-mlt-runtime-closure.md`.

`MLTTimelineAdapter` emits only:

- `avformat-novalidate` producers;
- one core playlist/tractor graph;
- an XML `.mlt` input consumed by `melt`;
- an `avformat` output consumer.

The carried `melt` binary also requires its non-XML-consumer `qtcrop` preflight. The resulting retained MLT module boundary is therefore exactly:

- `libmltavformat.dll`;
- `libmltcore.dll`;
- `libmltqt6.dll`;
- `libmltxml.dll`.

`tools/stage_windows_release.py` fails closed unless those modules and the required avformat/core/qtcrop data are present. It then removes MLT modules outside this service graph plus `lib/frei0r-1/**`, `lib/ladspa/**` and `lib/qml/**`. Top-level shared DLLs and Qt plugin directories remain untouched in this pass because dynamic loading requires separate Windows evidence.

## Current runtime evidence

Exact head `2726a26db41c913e6b764594bf5498000da57d21` passed CI #1760 / run `32109323588` and Stage 9 Windows Release #114 / run `32109323594` with release-profile schema v5 and the official corresponding-source coordinate. All release steps were green, including immutable staging/deep verification, packaged FFmpeg/FFprobe/MLT execution, native launcher supervision, silent install/uninstall and A -> B -> A rollback.

The #114 artifact contains 2,530 media files totaling `476,424,143` bytes (`454.35 MiB`) after the first Shotcut application/UI/helper pruning pass. Applying the proposed service closure to those exact bytes locally leaves 755 media files totaling `413,254,124` bytes (`394.11 MiB`): 1,775 files and `63,170,019` bytes (`60.24 MiB`, about 13.26%) are removed.

This second pruning result is not accepted merely from the local copy test. The exact committed pruning head must prove the same boundary through permanent CI and Windows Release before it can become D-058 evidence.

## Release checksums

`tools/write_release_checksums.py` creates deterministic `SHA256SUMS` records for final release artifacts and verifies them fail-closed. The generator is committed now because its behavior is independent of media pruning. It is intentionally not yet wired as the final publication step: authentic release checksums must be calculated after any future code-signing step, because signing changes the executable bytes.

## License boundary

This decision removes the known `--enable-nonfree` blocker and records an official corresponding-source artifact. It does not claim that every GPL/LGPL obligation is satisfied automatically.

The final release audit must still:

1. identify the exact MLT/`melt`, FFmpeg, Qt and other licenses applicable to the actually retained binaries/modules;
2. preserve required copyright/license notices in or alongside the immutable payload;
3. verify that the pinned official source bundle is sufficient corresponding-source/source-offer evidence for the exact shipped closure, supplementing it where any retained component requires additional material;
4. keep the UV Studio MIT source/license distinct from separately distributed GPL/LGPL components;
5. reject future media-runtime upgrades if the executable audit, service closure or provenance changes without review.

## Acceptance criteria

D-058 may move to Accepted only when one exact Stage 9 head proves all of the following:

1. the Shotcut `26.4.30` binary archive matches the pinned SHA-256;
2. the release profile pins the official `shotcut-src-26.4.30.txz` corresponding-source asset by HTTPS URL and SHA-256 and the profile is present in the immutable D-044 payload;
3. the extracted runtime contains regular `ffmpeg.exe`, adjacent `ffprobe.exe` and `melt.exe`;
4. the exact FFmpeg audit succeeds and reports `nonfree_enabled=false`;
5. `legal/ffmpeg-buildconf.json` is included in the D-044 manifest and survives installed deep verification;
6. the fail-closed UV MLT service closure contains the exact required avformat/core/xml/qt6 modules and data while excluded plugin trees remain absent;
7. packaged FFmpeg, FFprobe and MLT execute from release-manifest-owned paths with no PATH fallback;
8. existing real-media MLT/FFmpeg behavior, packaged browser outcomes, desktop supervision, silent install/uninstall and A -> B -> A update/rollback remain green with the service-closure-pruned carrier;
9. required notices/source-provenance obligations are recorded and the component-level license/source sufficiency audit is complete for the exact retained carrier;
10. the exact head passes all five permanent CI jobs and the Stage 9 Windows Release workflow.

Until those criteria are satisfied the PR remains Draft and the replacement carrier is an implementation under review, not an accepted release dependency.
