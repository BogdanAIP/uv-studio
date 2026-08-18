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

## Exact UV-owned media closure

The Shotcut archive is an acquisition carrier, not a second editor or canonical runtime tree. The exact UV MLT path and binary closure are documented in `docs/stage9-mlt-runtime-closure.md`.

`MLTTimelineAdapter` emits only:

- `avformat-novalidate` producers;
- one core playlist/tractor graph;
- an XML `.mlt` input consumed by `melt`;
- an `avformat` output consumer.

The carried `melt` binary also requires its non-XML-consumer `qtcrop` preflight. The required MLT module boundary is exactly:

- `libmltavformat.dll`;
- `libmltcore.dll`;
- `libmltqt6.dll`;
- `libmltxml.dll`.

The retained executable/module/framework roots were recursively audited through PE imports. The resulting non-system closure contains **52 PE binaries**. `tools/media_runtime_closure.py` converts that result into a deterministic staged-carrier allowlist while retaining the complete small `share/mlt/**` data tree, `qwindows.dll`, `COPYING.txt`, `LICENSE` and `qt.conf`.

Runtime entrypoints are retained at their unique carrier-relative location. Duplicate `ffmpeg.exe`, `ffprobe.exe` or `melt.exe` entrypoints fail closed instead of silently widening the release. `tools/stage_windows_release.py` also rechecks the required MLT modules/data after pruning.

This exact closure removes Shotcut application/UI/helper content, QML, frei0r, LADSPA, unused MLT modules, OpenCV/whisper/ggml helpers and all other carrier files outside the proven runtime graph.

## Current runtime evidence

The exact hardened closure is proven on head `4f0cd32ecd98332f03a430706129d0f23f51c0ce`:

- CI #1772 / run `32119127628`: **completed / success** across every job, including both OS bootstraps, release-runtime compatibility, Linux/Windows real-media and browser user-outcome suites and release-frontend compatibility;
- Stage 9 Windows Release #126 / run `32119127633`: **completed / success** through acquisition/hash audit, exact staging, D-044 build/deep verification, same-size tamper rejection, packaged FFmpeg/FFprobe/MLT execution, native desktop supervision, NSIS installer build, silent install/installed launch/safe uninstall, A -> B -> A rollback, portable archive and artifact upload.

Artifact #126 (`9318051186`) contains:

- **446 media files**;
- `128,695,917` uncompressed media bytes = **122.73 MiB**;
- exactly four retained MLT module DLLs, one `qwindows.dll`, 391 MLT data files and the bounded carrier-root closure;
- all required UV media entrypoints/modules/data present;
- no frei0r, LADSPA or QML plugin trees.

The #126 outer artifact is `213,097,938` bytes. Its portable ZIP is `105,941,643` bytes and its installer is `108,422,128` bytes.

Compared with the first audited Shotcut Stage 9 candidate (#114), the exact closure reduces media from **2,530 files / 454.35 MiB** to **446 files / 122.73 MiB**: 2,084 files (82.37%) and 331.62 MiB (72.99%) are removed while all permanent product/release evidence remains green.

Runtime closure is therefore no longer the reason D-058 remains Proposed.

## Release checksums

`tools/write_release_checksums.py` creates deterministic `SHA256SUMS` records for final release artifacts and verifies them fail-closed. The generator is committed and unit-tested because its behavior is independent of media pruning.

It is intentionally not wired as the final publication step yet. Authentic release checksums must be generated after any future Authenticode signing step because signing modifies executable bytes. The intended order is final build -> real signing -> `SHA256SUMS` -> publication.

## Remaining license/source boundary

The known `--enable-nonfree` blocker is removed and the official Shotcut corresponding-source asset is pinned, but that source asset is not automatically sufficient evidence for every retained Windows DLL.

The narrowed carrier includes externally provisioned Qt/MSYS2/runtime libraries in addition to Shotcut/MLT/FFmpeg-built components. Its generic root license texts are not treated as a substitute for component-level notices/corresponding-source evidence.

The remaining D-058 work is therefore explicit and bounded:

1. map the 52 retained PE binaries into exact upstream/component groups;
2. identify the applicable license/notice obligations for those actually retained groups;
3. pin additional corresponding-source coordinates where the Shotcut source bundle does not contain the exact source, especially externally provisioned Qt/MSYS2/runtime components;
4. stage the resulting UV-owned media-runtime notice/source manifest and required license texts into the immutable D-044 payload;
5. verify the exact legal/provenance payload through permanent CI and Windows Release.

This is an engineering provenance/compliance gate, not a claim of legal advice or an assumption that a carrier's aggregate license text covers all transitive binaries.

## Acceptance criteria

D-058 may move to Accepted only when one exact Stage 9 head proves all of the following:

1. the Shotcut `26.4.30` binary archive matches the pinned SHA-256;
2. the release profile pins the official `shotcut-src-26.4.30.txz` corresponding-source asset by HTTPS URL and SHA-256 and the profile is present in the immutable D-044 payload;
3. the exact FFmpeg audit succeeds and reports `nonfree_enabled=false`;
4. `legal/ffmpeg-buildconf.json` is included in the D-044 manifest and survives installed deep verification;
5. the fail-closed UV MLT service closure contains the exact required avformat/core/xml/qt6 modules and data;
6. the exact staged carrier is bounded to the audited PE/data allowlist and duplicate media entrypoints fail closed;
7. packaged FFmpeg, FFprobe and MLT execute from release-manifest-owned paths with no PATH fallback;
8. real-media behavior, packaged browser outcomes, desktop supervision, silent install/uninstall and A -> B -> A update/rollback remain green with the exact closure;
9. the exact component-level license/notice/source manifest is complete for every retained media-runtime group and its required evidence is included in the immutable payload;
10. the exact acceptance head passes all permanent CI jobs and the Stage 9 Windows Release workflow.

Criteria 1–8 are now demonstrated by the exact runtime evidence above. Criterion 9 remains open, so D-058 correctly remains **Proposed**. PR #38 stays Draft.
