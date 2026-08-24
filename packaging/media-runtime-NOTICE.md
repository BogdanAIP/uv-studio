# UV Studio Windows media runtime notice and source map

This notice describes the exact Stage 9 Windows media runtime retained from the
pinned Shotcut 26.4.30 acquisition carrier. It is generated/maintained by UV
Studio rather than treating the carrier's two root license files as blanket
coverage for transitive components.

The machine-readable authority is
`components.windows-x86_64.json`. Every retained `.exe`/`.dll` under
`runtime/media` must be mapped exactly once there; release staging fails closed
on an unmapped, duplicated, or missing PE file. The corresponding source
coordinates below are evidence for the exact retained versions. MSYS2-built
components additionally pin the recipe repository commit/path so packaging
patches are not lost.

This is redistribution/provenance engineering documentation, not legal advice.
The exact FFmpeg build enables both GPL and license version 3, so its combined
FFmpeg binary/library license is recorded as GPL-3.0-or-later.

The exact license/notice assets are governed separately by
`media-runtime-license-files.windows-x86_64.json`. Windows Release #140 proved
all 27 bounded assets through D-044/install/rollback; the acceptance candidate
pins every one of those exact asset SHA-256 values and rejects changed upstream
bytes before D-044.

| Component | Version | License expression | Retained PE files | Corresponding source |
| --- | --- | --- | ---: | --- |
| `ffmpeg` | n8.1-11-g75d37c499d | `GPL-3.0-or-later` | 9 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `mlt-framework` | 7.39.0-interim | `LGPL-2.1-or-later` | 6 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `mlt-melt` | 7.39.0-interim | `GPL-2.0-or-later` | 1 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `qt` | 6.8.3 | `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only` | 7 | https://download.qt.io/archive/qt/6.8/6.8.3/single/qt-everywhere-src-6.8.3.tar.xz (sha256 cdd3a69967208276bb01af7ace7dba0ba53e679f886a4cbe624225c60fb73f2c) |
| `libaom` | 3.13.1 | `BSD-2-Clause` | 1 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `dav1d` | 1.5.1 | `BSD-2-Clause` | 1 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `vmaf` | 3.0.0 | `BSD-2-Clause-Patent` | 1 | https://github.com/mltframework/shotcut/releases/download/v26.4.30/shotcut-src-26.4.30.txz (sha256 fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442) |
| `x264` | 0.165.r3222.b35605a | `GPL-2.0-or-later` | 1 | https://code.videolan.org/videolan/x264.git @ b35605ace3ddf7c1a5d67a2eb553f034aef41d55 |
| `x265` | 4.1 | `GPL-2.0-or-later` | 1 | https://bitbucket.org/multicoreware/x265_git/downloads/x265_4.1.tar.gz (sha256 a31699c6a89806b74b0151e5e6a7df65de4b49050482fe5ebf8a4379d7af8f29) |
| `lame` | 3.100 | `LGPL-2.0-or-later` | 1 | https://downloads.sourceforge.net/lame/lame-3.100.tar.gz (sha256 ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e) |
| `gcc-runtime` | 15.2.0 | `GPL-3.0-or-later WITH GCC-exception-3.1` | 2 | https://ftp.gnu.org/gnu/gcc/gcc-15.2.0/gcc-15.2.0.tar.xz (sha256 438fd996826b0c82485a29da03a72d71d6e3541a83ec702df4271f6fe025d24e) |
| `winpthreads` | 14.0.0.r14.g4761eabdd | `MIT AND BSD-3-Clause-Clear` | 1 | https://git.code.sf.net/p/mingw-w64/mingw-w64 @ 4761eabdda9764d14778a52a4a9dd1d5e720569e |
| `dlfcn-win32` | 1.4.2 | `MIT` | 1 | https://github.com/dlfcn-win32/dlfcn-win32/archive/v1.4.2.tar.gz (sha256 f61a874bc9163ab488accb364fd681d109870c86e8071f4710cbcdcbaf9f2565) |
| `libiconv` | 1.19 | `LGPL-2.1-or-later` | 1 | https://ftp.gnu.org/pub/gnu/libiconv/libiconv-1.19.tar.gz (sha256 88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6) |
| `xz-liblzma` | 5.8.3 | `0BSD` | 1 | https://github.com/tukaani-project/xz/releases/download/v5.8.3/xz-5.8.3.tar.xz (sha256 fff1ffcf2b0da84d308a14de513a1aa23d4e9aa3464d17e64b9714bfdd0bbfb6) |
| `bzip2` | 1.0.8 | `bzip2-1.0.6` | 1 | https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz (sha256 ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269) |
| `libogg` | 1.3.6 | `BSD-3-Clause` | 1 | https://downloads.xiph.org/releases/ogg/libogg-1.3.6.tar.gz (sha256 83e6704730683d004d20e21b8f7f55dcb3383cdf84c0daedf30bde175f774638) |
| `libvorbis` | 1.3.7 | `BSD-3-Clause` | 2 | https://downloads.xiph.org/releases/vorbis/libvorbis-1.3.7.tar.gz (sha256 0e982409a9c3fc82ee06e08205b1355e5c6aa4c36bca58146ef399621b0ce5ab) |
| `libtheora` | 1.2.0 | `BSD-3-Clause` | 2 | https://downloads.xiph.org/releases/theora/libtheora-1.2.0.tar.gz (sha256 279327339903b544c28a92aeada7d0dcfd0397b59c2f368cc698ac56f515906e) |
| `opus` | 1.6.1 | `BSD-3-Clause` | 1 | https://downloads.xiph.org/releases/opus/opus-1.6.1.tar.gz (sha256 6ffcb593207be92584df15b32466ed64bbec99109f007c82205f0194572411a1) |
| `libvpx` | 1.16.0 | `BSD-3-Clause` | 1 | https://github.com/webmproject/libvpx/archive/v1.16.0/libvpx-1.16.0.tar.gz (sha256 7a479a3c66b9f5d5542a4c6a1b7d3768a983b1e5c14c60a9396edc9b649e015c) |
| `libwebp` | 1.6.0 | `BSD-3-Clause` | 3 | https://github.com/webmproject/libwebp/archive/v1.6.0/libwebp-1.6.0.tar.gz (sha256 93a852c2b3efafee3723efd4636de855b46f9fe1efddd607e1f42f60fc8f2136) |
| `svt-av1` | 4.1.0 | `BSD-3-Clause-Clear` | 1 | https://gitlab.com/AOMediaCodec/SVT-AV1/-/archive/v4.1.0/SVT-AV1-v4.1.0.tar.gz (sha256 6c4c0c44ff0ba3d136d6f57f3a707f9de8e9c866f50f809c1d22a43f0d8c9583) |
| `onevpl` | 2.16.0 | `MIT` | 1 | https://github.com/intel/libvpl/archive/v2.16.0/libvpl-2.16.0.tar.gz (sha256 d60931937426130ddad9f1975c010543f0da99e67edb1c6070656b7947f633b6) |
| `zimg` | 3.0.6 | `WTFPL` | 1 | https://github.com/sekrit-twc/zimg/archive/release-3.0.6/zimg-3.0.6.tar.gz (sha256 be89390f13a5c9b2388ce0f44a5e89364a20c1c57ce46d382b1fcc3967057577) |
| `sdl2` | 2.26.2 | `Zlib` | 1 | https://libsdl.org/release/SDL2-2.26.2.tar.gz (sha256 95d39bc3de037fbdfa722623737340648de4f180a601b0afad27645d150b99e0) |
| `libxml2` | 2.15.3 | `MIT` | 1 | https://download.gnome.org/sources/libxml2/2.15/libxml2-2.15.3.tar.xz (sha256 78262a6e7ac170d6528ebfe2efccdf220191a5af6a6cd61ea4a9a9a5042c7a07) |
| `zlib` | 1.3.2 | `Zlib` | 1 | https://github.com/madler/zlib/releases/download/v1.3.2/zlib-1.3.2.tar.xz (sha256 d7a0654783a4da529d1bb793b7ad9c3318020af77667bcae35f95d0e42a792f3) |

## Carrier and source bundle

- Shotcut portable: `26.4.30`
- Binary SHA-256: `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`
- Official Shotcut corresponding-source bundle:
  `shotcut-src-26.4.30.txz`
- Source bundle SHA-256:
  `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`
- Qt source archive: `qt-everywhere-src-6.8.3.tar.xz`
- Qt source SHA-256:
  `cdd3a69967208276bb01af7ace7dba0ba53e679f886a4cbe624225c60fb73f2c`

The source bundle is intentionally not installed on every machine. Its immutable
URL/hash, the Qt source URL/hash, and the exact component map are carried in the
release legal payload so the shipped binary closure can be traced without
guessing from filenames.

## Scope

This map covers the 52 PE binaries in the exact Stage 9 media closure. The
small `share/mlt/**` service metadata, `qt.conf`, and carrier license/config
files are retained as non-PE runtime data and remain covered by the D-044 file
manifest. Future carrier upgrades must update this component map and pass the
same exact-coverage gate before they can become release inputs.
