# Stage 9 MLT runtime closure evidence

This document records the service boundary used for the second evidence-backed pruning pass of the Stage 9 Windows media carrier. It is release evidence, not a replacement for the UV-owned editor model.

## Canonical UV graph

`uv_studio/editor/mlt_adapter.py` projects accepted UV range edits into ephemeral MLT XML. The canonical Project Store remains the source of truth.

The emitted graph is intentionally narrow:

1. each source/replacement producer declares `mlt_service=avformat-novalidate`;
2. those producers are referenced by one MLT `playlist`;
3. the playlist is referenced by one `tractor`;
4. rendering invokes `melt <temporary>.mlt -consumer avformat:<output>` with `vcodec=mpeg4`, `an=1`, `real_time=-1` and `terminate_on_pause=1`;
5. the `.mlt` input requires the XML producer/loader path;
6. the current carried `melt` binary contains the `qtcrop` preflight used for non-XML consumers, so the Qt6 MLT module remains part of the closure even though UV XML does not declare a Qt filter.

No UV Stage 9 projection in this path declares frei0r, LADSPA, Movit, OpenCV, Glaxnimate, DeckLink, JACK, SDL consumer, SoX, rubberband, vidstab, xine, OpenFX or other MLT plugin services.

## Service -> module/data mapping

| UV/runtime requirement | Retained MLT module | Required data retained |
| --- | --- | --- |
| `.mlt` XML loading | `libmltxml.dll` | core loader data remains present |
| playlist/tractor/core loader services | `libmltcore.dll` | `share/mlt/core/loader.ini`, `loader.dict` |
| `avformat-novalidate` producer | `libmltavformat.dll` | `share/mlt/avformat/producer_avformat-novalidate.yml` |
| `avformat` output consumer | `libmltavformat.dll` | `share/mlt/avformat/consumer_avformat.yml` |
| `melt` non-XML-consumer Qt preflight (`qtcrop`) | `libmltqt6.dll` | `share/mlt/qt6/filter_qtcrop.yml` |

`tools/stage_windows_release.py` treats these four modules and data files as a fail-closed service closure. A missing required file aborts staging before a plausible partial release is produced.

## Exact artifact #114 static dependency audit

Baseline artifact: Stage 9 Windows Release #114 / run `32109323594`, exact head `2726a26db41c913e6b764594bf5498000da57d21`.

The retained PE roots (`ffmpeg.exe`, `ffprobe.exe`, `melt.exe`, `libmlt-7.dll`, the four MLT modules and the Windows Qt platform plugin) resolve to a bounded static PE closure. Important direct edges include:

- `melt.exe -> libmlt-7.dll + SDL2.dll`;
- `libmltxml.dll -> libmlt-7.dll + libxml2-16.dll`;
- `libmltavformat.dll -> libmlt-7.dll + avcodec/avdevice/avfilter/avformat/avutil + swresample/swscale`;
- `libmltqt6.dll -> libmlt-7.dll + libmlt++-7.dll + Qt6Core/Gui/Svg/SvgWidgets/Widgets/Xml`.

The static audit also shows that `lib/frei0r-1`, `lib/ladspa` and `lib/qml` are not reachable from those retained roots. They are therefore removed together with MLT modules that register services UV does not use. Top-level shared DLLs and Qt plugin directories are deliberately retained in this pass because some libraries are loaded dynamically and require a separate proof before removal.

## Measured pruning result on artifact #114

Applying the proposed closure locally to the exact #114 portable payload gives:

- before: **2,530 media files**, `476,424,143` bytes (`454.35 MiB`);
- after: **755 media files**, `413,254,124` bytes (`394.11 MiB`);
- removed: **1,775 files**, `63,170,019` bytes (`60.24 MiB`, about `13.26%` of uncompressed media bytes).

The removed surface is:

- existing Shotcut application/UI/helper exclusions;
- `lib/frei0r-1/**`;
- `lib/ladspa/**`;
- `lib/qml/**`;
- every `lib/mlt/libmlt*.dll` except `libmltavformat.dll`, `libmltcore.dll`, `libmltqt6.dll`, and `libmltxml.dll`.

This measured result is only a pre-commit local proof. D-058 remains Proposed until the exact committed head passes the permanent Windows release workflow, including real MLT rendering, packaged execution, installation and rollback.

## Remaining pruning reserve

The artifact contains a much larger set of top-level DLLs that are outside the static closure. They are not removed by this pass. Future pruning may consider them only after dynamic-load behavior is measured on the actual Windows runner and the supported input/output contract is explicit. Passing one static import scan is not sufficient evidence to remove dynamically discovered Qt/FFmpeg dependencies.
