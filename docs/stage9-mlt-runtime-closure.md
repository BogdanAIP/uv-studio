# Stage 9 MLT runtime closure evidence

This document records the exact evidence-backed Windows media closure used by Stage 9. It is release evidence behind the UV-owned editor adapter; it does not make MLT or Shotcut canonical project state.

## Canonical UV graph

`uv_studio/editor/mlt_adapter.py` projects accepted UV range edits into ephemeral MLT XML. The canonical Project Store remains the source of truth.

The emitted graph is intentionally narrow:

1. each source/replacement producer declares `mlt_service=avformat-novalidate`;
2. those producers are referenced by one MLT `playlist`;
3. the playlist is referenced by one `tractor`;
4. rendering invokes `melt <temporary>.mlt -consumer avformat:<output>` with `vcodec=mpeg4`, `an=1`, `real_time=-1` and `terminate_on_pause=1`;
5. the `.mlt` input requires the XML producer/loader path;
6. the current carried `melt` binary performs its non-XML-consumer `qtcrop` preflight, so the Qt6 MLT module remains part of the closure even though UV XML does not declare a Qt filter.

No Stage 9 projection in this path declares frei0r, LADSPA, Movit, OpenCV, Glaxnimate, DeckLink, JACK, SDL consumer, SoX, rubberband, vidstab, xine, OpenFX or other MLT plugin services.

## Service -> module/data mapping

| UV/runtime requirement | Retained MLT module | Required data retained |
| --- | --- | --- |
| `.mlt` XML loading | `libmltxml.dll` | MLT XML/core loader data |
| playlist/tractor/core loader services | `libmltcore.dll` | `share/mlt/core/loader.ini`, `loader.dict` |
| `avformat-novalidate` producer | `libmltavformat.dll` | `share/mlt/avformat/producer_avformat-novalidate.yml` |
| `avformat` output consumer | `libmltavformat.dll` | `share/mlt/avformat/consumer_avformat.yml` |
| `melt` non-XML-consumer Qt preflight (`qtcrop`) | `libmltqt6.dll` | `share/mlt/qt6/filter_qtcrop.yml` |

`tools/stage_windows_release.py` fails closed unless these four modules and required data files are present before pruning and after staging.

## Binary dependency closure

The Stage 9 artifact audit recursively followed PE imports from the actual retained runtime roots:

- `ffmpeg.exe` and `ffprobe.exe`;
- `melt.exe`;
- `libmlt-7.dll` and `libmlt++-7.dll`;
- `libmltavformat.dll`, `libmltcore.dll`, `libmltqt6.dll`, `libmltxml.dll`;
- the Windows Qt platform plugin `lib/qt6/platforms/qwindows.dll`.

Important direct edges include:

- `melt.exe -> libmlt-7.dll + SDL2.dll`;
- `libmltxml.dll -> libmlt-7.dll + libxml2-16.dll`;
- `libmltavformat.dll -> libmlt-7.dll + avcodec/avdevice/avfilter/avformat/avutil + swresample/swscale`;
- `libmltqt6.dll -> libmlt-7.dll + libmlt++-7.dll + Qt6Core/Gui/Svg/SvgWidgets/Widgets/Xml`.

The recursive non-system closure contains **52 PE binaries**. `tools/media_runtime_closure.py` represents this audited boundary as an allowlist. The staged carrier also retains `COPYING.txt`, `LICENSE`, `qt.conf` and the complete small `share/mlt/**` data tree. Runtime entrypoints (`ffmpeg.exe`, `ffprobe.exe`, `melt.exe`) are retained at their unique carrier-relative location; duplicate entrypoint basenames fail closed rather than silently widening the release.

This allowlist intentionally excludes Shotcut UI/application files, QML, frei0r, LADSPA, unused MLT modules, OpenCV/whisper/ggml helpers and other DLL/plugin trees that are neither in the recursive retained PE graph nor required MLT data.

## Permanent Windows proof

The exact allowlist first passed Stage 9 Windows Release #122 / run `32118426303` on head `56c12de971c25670a6f4f064ee815668f2755b8d`, including real packaged MLT execution, D-044 deep verification, native desktop supervision, silent installation/launch/uninstall and A -> B -> A rollback.

The hardened unique-entrypoint version then passed on exact head `4f0cd32ecd98332f03a430706129d0f23f51c0ce`:

- CI #1772 / run `32119127628`: **completed / success**, including both OS bootstraps, release-runtime compatibility, Linux/Windows real-media and browser user-outcome suites and release-frontend compatibility;
- Stage 9 Windows Release #126 / run `32119127633`: **completed / success**, including acquisition/hash audit, exact media staging, D-044 manifest/deep verification, same-size tamper rejection, packaged FFmpeg/FFprobe/MLT execution, desktop supervision, NSIS build, silent install/installed launch/safe uninstall, A -> B -> A rollback, portable archive and artifact upload.

Artifact #126 (`9318051186`) independently confirms the staged shape:

- **446 media files**;
- `128,695,917` uncompressed media bytes = **122.73 MiB**;
- 50 carrier-root files, 4 MLT module DLLs, one `qwindows.dll`, 391 `share/mlt` files;
- all required MLT modules/data and the three media entrypoints present;
- no `lib/frei0r-1`, `lib/ladspa` or `lib/qml` files.

The #126 outer artifact is `213,097,938` bytes. Its portable ZIP is `105,941,643` bytes and the installer is `108,422,128` bytes.

## Reduction from the Stage 9 baseline

The first audited Shotcut candidate (#114) contained **2,530 media files / 476,424,143 bytes (454.35 MiB)**.

The exact UV closure contains **446 media files / 128,695,917 bytes (122.73 MiB)**.

Therefore the evidence-backed pruning removes:

- **2,084 media files (82.37%)**;
- **347,728,226 uncompressed bytes = 331.62 MiB (72.99%)**.

The complete GitHub Actions release artifact fell from `446,791,269` bytes on #114 to about `213.10 MB` on the exact-closure candidates, while the same product/installer/rollback tests remained green.

## Remaining D-058 boundary

Runtime closure is no longer the D-058 uncertainty. The remaining blocker is redistribution evidence for the exact retained binary groups.

The Shotcut source asset remains a strong source coordinate for Shotcut/MLT/FFmpeg and dependencies built into its source bundle, but the Windows carrier also includes externally provisioned Qt/MSYS2/runtime libraries. The narrowed carrier's generic root license texts are not treated as sufficient per-component evidence for every retained transitive DLL.

Before D-058 can be Accepted, UV Studio must produce an exact component-level media-runtime notice/source manifest for the 52 retained PE binaries/groups, pin any additional corresponding-source coordinates needed by Qt/MSYS2-provided components, and stage the required notices/source evidence into the immutable D-044 payload. No further size pruning is required merely to make that audit tractable.
