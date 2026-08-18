# D-058 — Redistributable Windows media runtime boundary

- **Status:** Accepted
- **Date:** 2026-08-18
- **Stage:** Stage 9 Desktop Productization & Release Hardening
- **Acceptance head:** `6060f620fe6f0751496e98ba85e5405ece3613a7`

## Context

Stage 9 originally reused a Kdenlive 26.04.3 standalone package that had already proven FFmpeg/FFprobe/MLT behavior in Windows CI. Exact executable self-report later showed that carrier's FFmpeg 8.1.1 was configured with `--enable-nonfree`. That carrier is therefore rejected from the public UV Studio release path even though its runtime behavior was technically valid.

The replacement needed to satisfy two independent requirements:

1. preserve the already-proven UV editor/runtime behavior without creating a second editor authority; and
2. make the exact shipped Windows media closure mechanically traceable to corresponding source, license/notice material and immutable release evidence.

This decision records the accepted boundary. It is an engineering redistribution/provenance decision, not legal advice and not a substitute for the final whole-product release audit.

## Decision

Use official Shotcut portable `26.4.30` only as the Windows media **acquisition carrier** for Stage 9:

- binary: `shotcut-win64-26.4.30.zip`;
- binary SHA-256: `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`;
- corresponding-source asset: `shotcut-src-26.4.30.txz`;
- corresponding-source SHA-256: `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`;
- Shotcut release/build identity: `26.4.30`, tag commit `1da45a9de2ab3a6d3823aa455be315dc8b034cfe`;
- Qt source coordinate: `qt-everywhere-src-6.8.3.tar.xz`, SHA-256 `cdd3a69967208276bb01af7ace7dba0ba53e679f886a4cbe624225c60fb73f2c`.

The acquisition archive is not UV Studio's canonical runtime definition. UV Studio copies it into a staging tree, rejects unsafe filesystem content, removes non-required application/plugin/helper surface, verifies the exact retained closure and only then lets D-044 hash the product payload.

Shotcut itself is never invoked as a second editor. Project Store remains canonical and MLT remains behind the UV-owned adapter.

## Exact FFmpeg boundary

The retained carrier reports FFmpeg `n8.1-11-g75d37c499d`, upstream commit `75d37c499da2a9fd50e3ef5a69c7dd87cd96f62a`.

`tools/audit_ffmpeg_release.py` executes the exact selected staged `ffmpeg.exe -buildconf` and fails closed on `--enable-nonfree`. The accepted build reports:

- GPL enabled;
- license version 3 enabled;
- `nonfree_enabled=false`.

Accordingly the exact combined FFmpeg binary/library boundary is recorded as `GPL-3.0-or-later` in the component manifest. The bounded machine-captured build configuration is staged as `legal/ffmpeg-buildconf.json` before D-044 and survives installed deep verification.

## Exact UV MLT/runtime closure

`MLTTimelineAdapter` requires only:

- `avformat-novalidate` producers;
- the core playlist/tractor graph;
- XML loading;
- the `avformat` output consumer;
- the carried `melt` non-XML-consumer `qtcrop` preflight.

The retained MLT module boundary is exactly:

- `libmltavformat.dll`;
- `libmltcore.dll`;
- `libmltqt6.dll`;
- `libmltxml.dll`.

The recursive Windows PE closure contains exactly **52 retained PE binaries**. `tools/media_runtime_closure.py` converts that audited graph into the exact staged allowlist, retains the required small MLT data tree and `qwindows.dll`, and rejects duplicate FFmpeg/FFprobe/melt entrypoints.

The accepted media payload remains **446 files / 128,695,917 bytes (122.73 MiB)**. Compared with the first Shotcut candidate (#114: 2,530 files / 454.35 MiB), 2,084 files and 331.62 MiB were removed without losing permanent product/release outcomes.

## Component-level provenance

`packaging/media-runtime-components.windows-x86_64.json` is the machine-readable component/source authority for the retained PE graph.

It maps all **52/52 PE binaries** exactly once into **28 component groups**. The release fails closed when a retained PE file is:

- missing from the map;
- mapped more than once;
- no longer present in the retained closure; or
- backed by incomplete source provenance.

The map records exact or bounded source coordinates for FFmpeg, MLT, Qt and the retained MSYS2/runtime/codec groups including x264, x265, GCC runtime, winpthreads, dlfcn-win32, libiconv, liblzma, bzip2, Ogg/Vorbis/Theora/Opus, libvpx, WebP, SVT-AV1, oneVPL, zimg, SDL2, libxml2 and zlib.

The generic Shotcut root license files are not treated as blanket coverage for these transitive components.

## Exact license/notice assets

`packaging/media-runtime-license-files.windows-x86_64.json` is the machine-readable authority for the concrete license/notice texts staged beside the retained media runtime.

The accepted manifest has:

- **27 bounded license/notice assets**;
- complete coverage of all **28 component groups**;
- `release_gate.require_hashes=true`;
- an exact SHA-256 for every asset;
- HTTPS-only remote acquisition where an asset is not already inside the verified carrier;
- per-asset and aggregate size limits;
- path/traversal validation;
- fail-closed cleanup of partial output.

A common license text may cover multiple components, while one component may require more than one asset. For example, GCC runtime carries both the GPLv3 text and GCC Runtime Library Exception; codec groups may carry both license and patent-notice material.

The `liblzma-5.dll` scope is intentionally recorded as `0BSD`. XZ 5.8.3's own licensing description states that liblzma itself is 0BSD; GPL/LGPL terms attached to other XZ utilities/build helpers are therefore not assigned to this retained DLL.

The concrete files are staged under:

`legal/media-runtime/licenses/`

and the exact license-file manifest itself is staged as:

`legal/media-runtime/license-files.windows-x86_64.json`.

All of this happens before D-044 builds the immutable release manifest.

## Two-pass license evidence

The license asset boundary was deliberately closed in two evidence passes rather than guessing hashes.

### Audit pass — exact head `edc3c216c76059ed32aab16b18d712bea689f5d0`

- CI #1786 / run `32137075777`: **completed / success**;
- Stage 9 Windows Release #140 / run `32137075864`: **completed / success**;
- 27 license/notice assets were acquired under size/path bounds;
- all 28 component groups were covered;
- D-044 deep verification passed;
- packaged smoke, installer, silent install/uninstall and A -> B -> A rollback passed.

Artifact #140 supplied the exact bytes used to measure every license-asset SHA-256 rather than trusting mutable remote content by name.

### Pinned acceptance pass — exact head `6060f620fe6f0751496e98ba85e5405ece3613a7`

Every one of the 27 measured asset hashes was pinned and `require_hashes=true` became mandatory.

Permanent evidence:

- CI #1788 / run `32139063217`: **completed / success** across all permanent jobs;
- Stage 9 Windows Release #142 / run `32139063188`: **completed / success**;
- Windows Release artifact id `9325376444`;
- artifact digest `sha256:e676ab832c7f5c536d6f1783051c895505a9b8bf932d98f9831f6cf95e901446`.

A post-run artifact inspection also proved:

- exactly **27/27** expected license/notice files exist in the portable payload;
- **27/27** file SHA-256 values equal the pinned license manifest;
- **27/27** files are present in D-044 `release-manifest.json`;
- their D-044 SHA-256 values equal the actual payload bytes.

Thus the installed and portable candidates carry the same mechanically reviewed legal/provenance evidence that the release workflow validated.

## Acceptance criteria

D-058 acceptance requires one exact head to prove all of the following:

1. Shotcut `26.4.30` binary archive matches the pinned SHA-256 — **passed**.
2. Official Shotcut corresponding-source URL/SHA-256 is pinned and staged in immutable release inputs — **passed**.
3. Exact FFmpeg audit reports `nonfree_enabled=false` — **passed**.
4. `legal/ffmpeg-buildconf.json` is D-044-owned and survives installed verification — **passed**.
5. Exact required MLT service closure is present — **passed**.
6. Staged carrier is bounded to the audited PE/data closure; duplicate entrypoints fail closed — **passed**.
7. FFmpeg/FFprobe/MLT execute only from release-manifest-owned paths with no packaged PATH fallback — **passed**.
8. Real-media behavior, browser outcomes, desktop supervision, installer and A -> B -> A rollback remain green — **passed**.
9. Component-level source/license/notice evidence covers every retained media-runtime group and is immutable-payload-owned — **passed**: 52 PE / 28 groups / 27 hash-pinned assets.
10. The exact acceptance head passes all permanent CI jobs and Stage 9 Windows Release — **passed**: CI #1788 and Windows Release #142.

All ten criteria are satisfied on `6060f620fe6f0751496e98ba85e5405ece3613a7`.

**D-058 is Accepted.**

## Consequences

- Kdenlive 26.04.3 remains rejected historical evidence and cannot silently return to the public release path.
- Shotcut 26.4.30 remains only an acquisition carrier; UV-owned exact closure/provenance manifests define what ships.
- A future media-carrier/version update must re-run the exact PE closure, component map, source coordinates, license-asset hashes, D-044 verification and permanent Windows evidence. Existing acceptance does not automatically transfer to new bytes.
- D-058 acceptance does **not** declare the entire Stage 9 public release finished. Real Windows code signing, the final whole-payload dependency/security/license audit and post-signing release checksums remain separate blockers before PR #38 can move from Draft to Review.

## Release checksums boundary

`tools/write_release_checksums.py` remains intentionally unwired as the final publication step until real Authenticode signing exists. Signing changes executable bytes, so the required order remains:

`final build -> real signing -> SHA256SUMS -> publication`.
