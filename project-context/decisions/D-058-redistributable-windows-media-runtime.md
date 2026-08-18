# D-058 — Redistributable Windows media runtime boundary

- **Status:** Proposed
- **Date:** 2026-08-18
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Stage 9 originally reused the exact Kdenlive 26.04.3 standalone package that had already proven FFmpeg/FFprobe/MLT behavior in Windows CI. That was technically correct but not sufficient for public redistribution.

The exact executable self-report from the pinned Kdenlive carrier showed FFmpeg 8.1.1 configured with both `--enable-gpl` and `--enable-nonfree` (along with `--enable-libx264`, `--enable-libx265` and other optional codec integrations). FFmpeg upstream explicitly distinguishes `--enable-nonfree` as a build configuration that is not redistributable. Therefore the Kdenlive-carried FFmpeg/FFprobe build is rejected as a public UV Studio release input even though its runtime behavior is proven.

A temporary research PR (#39) separately proved that the product can inspect and reject this class of packaging risk and that redistributable Windows FFmpeg candidates exist. Stage 9 now needs one coherent MLT + FFmpeg runtime closure whose actual shipped FFmpeg build is mechanically checked rather than assumed from a package name.

## Proposed decision

Replace the Stage 9 Windows media carrier with the official Shotcut portable release `26.4.30`:

- acquisition: `shotcut-win64-26.4.30.zip` from `mltframework/shotcut` release `v26.4.30`;
- pinned SHA-256: `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`;
- the carrier contains the Windows MLT/FFmpeg runtime closure built and shipped together by the MLT/Shotcut project;
- upstream Windows build automation configures FFmpeg as shared and GPL-enabled but does not enable `--enable-nonfree`;
- UV Studio nevertheless trusts only the downloaded bytes and their executable self-report, not the build-script claim.

`tools/audit_ffmpeg_release.py` becomes a permanent release gate. It executes the exact selected `ffmpeg.exe` with `-buildconf`, bounds the returned evidence and fails closed if `--enable-nonfree` is present. GPL/shared/static flags are recorded as evidence instead of being silently interpreted as permission.

The exact audit JSON is copied into the immutable release payload as `legal/ffmpeg-buildconf.json` before D-044 builds the release manifest. Historical installed releases therefore identify not only which FFmpeg bytes were shipped but also the configuration the executable reported during packaging.

The existing D-052 curation rule remains a historical safety rule for the former Kdenlive acquisition and is harmless if the replacement carrier contains no matching Qt test subtree. D-058 supersedes Kdenlive as the Stage 9 media acquisition choice; it does not weaken D-052's rule that runtime pruning requires explicit evidence.

## License boundary

This decision removes the known `--enable-nonfree` blocker. It does not claim that GPL/LGPL obligations are satisfied automatically.

The final release audit must still:

1. identify the exact MLT/`melt` and FFmpeg licenses applicable to the shipped binaries/modules;
2. preserve required copyright/license notices in or alongside the immutable payload;
3. provide the corresponding-source/source-offer information required by the licenses for the exact shipped build where applicable;
4. keep the UV Studio MIT source/license distinct from separately distributed GPL/LGPL components;
5. reject future media-runtime upgrades if the executable audit or provenance changes without review.

## Acceptance criteria

D-058 may move to Accepted only when one exact Stage 9 head proves all of the following:

1. the Shotcut `26.4.30` archive matches the pinned SHA-256;
2. the extracted runtime contains regular `ffmpeg.exe`, adjacent `ffprobe.exe` and `melt.exe`;
3. the exact FFmpeg audit succeeds and reports `nonfree_enabled=false`;
4. `legal/ffmpeg-buildconf.json` is included in the D-044 manifest and survives installed deep verification;
5. packaged FFmpeg, FFprobe and MLT execute from release-manifest-owned paths with no PATH fallback;
6. existing real-media MLT/FFmpeg behavior, packaged browser outcomes, desktop supervision, silent install/uninstall and A -> B -> A update/rollback remain green;
7. required notices/source-provenance obligations are recorded for the exact carrier;
8. the exact head passes all five permanent CI jobs and the Stage 9 Windows Release workflow.

Until those criteria are satisfied the PR remains Draft and the replacement carrier is an implementation under review, not an accepted release dependency.
