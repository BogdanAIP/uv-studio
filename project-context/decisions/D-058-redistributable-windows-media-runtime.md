# D-058 — Redistributable Windows media runtime boundary

- **Status:** Proposed
- **Date:** 2026-08-18
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

Stage 9 originally reused the exact Kdenlive 26.04.3 standalone package that had already proven FFmpeg/FFprobe/MLT behavior in Windows CI. That was technically correct but not sufficient for public redistribution.

The exact executable self-report from the pinned Kdenlive carrier showed FFmpeg 8.1.1 configured with both `--enable-gpl` and `--enable-nonfree`. FFmpeg upstream explicitly distinguishes `--enable-nonfree` as a build configuration that is not redistributable. Therefore the Kdenlive-carried FFmpeg/FFprobe build is rejected as a public UV Studio release input even though its runtime behavior is proven.

A temporary research PR (#39) separately proved that the product can inspect and reject this class of packaging risk and that redistributable Windows FFmpeg candidates exist. Stage 9 now needs one coherent MLT + FFmpeg runtime closure whose actual shipped FFmpeg build and corresponding-source coordinates are mechanically recorded rather than assumed from a package name.

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

The Shotcut archive is an acquisition carrier, not a second editor or canonical runtime tree. UV Studio prunes only evidence-backed application/UI/helper surface (`shotcut.exe`, `share/shotcut/**`, `ffplay.exe`, `glaxnimate.exe`, `whisper-cli.exe`) and retains FFmpeg/FFprobe, `melt`, DLLs, MLT modules/data and supporting runtime trees until a separate dependency-closure proof justifies additional pruning.

## Current runtime evidence

Exact head `e1fba386f5fefd46806317a844023169e7ecacc7` passed Stage 9 Windows Release #112 / Actions run `32107133982` with the pruned Shotcut carrier. That run proved archive identity, FFmpeg buildconf audit, immutable staging/deep verification, packaged FFmpeg/FFprobe/MLT execution, packaged browser/backend behavior, native launcher supervision, silent install/uninstall, clean-machine execution and A -> B -> A rollback.

The same SHA passed both platform bootstrap jobs, Ubuntu and Windows application baselines including real-media/browser outcomes, release-runtime compatibility and release-frontend compatibility. Fresh CI #1758 / Actions run `32109010491` also passed `development-context` after the PR journal metadata was corrected.

The remaining D-058 work is to land the schema-v5 corresponding-source provenance and then prove that exact resulting head through the permanent CI and Windows Release gates.

## License boundary

This decision removes the known `--enable-nonfree` blocker and records an official corresponding-source artifact. It does not claim that every GPL/LGPL obligation is satisfied automatically.

The final release audit must still:

1. identify the exact MLT/`melt` and FFmpeg licenses applicable to the shipped binaries/modules;
2. preserve required copyright/license notices in or alongside the immutable payload;
3. verify that the pinned official source bundle is sufficient corresponding-source/source-offer evidence for the exact shipped closure, supplementing it where any shipped component requires additional material;
4. keep the UV Studio MIT source/license distinct from separately distributed GPL/LGPL components;
5. reject future media-runtime upgrades if the executable audit or provenance changes without review.

## Acceptance criteria

D-058 may move to Accepted only when one exact Stage 9 head proves all of the following:

1. the Shotcut `26.4.30` binary archive matches the pinned SHA-256;
2. the release profile pins the official `shotcut-src-26.4.30.txz` corresponding-source asset by HTTPS URL and SHA-256 and the profile is present in the immutable D-044 payload;
3. the extracted runtime contains regular `ffmpeg.exe`, adjacent `ffprobe.exe` and `melt.exe`;
4. the exact FFmpeg audit succeeds and reports `nonfree_enabled=false`;
5. `legal/ffmpeg-buildconf.json` is included in the D-044 manifest and survives installed deep verification;
6. packaged FFmpeg, FFprobe and MLT execute from release-manifest-owned paths with no PATH fallback;
7. existing real-media MLT/FFmpeg behavior, packaged browser outcomes, desktop supervision, silent install/uninstall and A -> B -> A update/rollback remain green with the evidence-backed pruned carrier;
8. required notices/source-provenance obligations are recorded for the exact carrier;
9. the exact head passes all five permanent CI jobs and the Stage 9 Windows Release workflow.

Until those criteria are satisfied the PR remains Draft and the replacement carrier is an implementation under review, not an accepted release dependency.
