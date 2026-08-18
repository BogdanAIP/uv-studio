# D-046 — Exact supported language runtimes and Windows release input profile

- **Status:** Accepted
- **Date:** 2026-08-17
- **Updated:** 2026-08-18
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The development dependency contract intentionally uses bounded direct ranges so maintainers can evaluate dependency upgrades. That is not sufficient for a shipped desktop application: resolving the same ranges on different dates or Python patch levels can produce different transitive graphs.

Stage 9 therefore selects exact supported runtimes, exact binary acquisition coordinates and, where redistribution requires it, exact corresponding-source coordinates before those inputs become part of the package contract.

## Decision

`packaging/runtime-profile.windows-x86_64.json` is the machine-readable source of truth for the first Windows x86_64 release inputs. Schema version 5 records:

- **CPython 3.13.14** and the exact shipping constraints file;
- **Node.js 24.19.0**, the npm lockfile, and the exact official Windows x64 release ZIP HTTPS source plus SHA-256;
- the exact Shotcut portable `26.4.30` Windows media carrier URL/SHA-256 used for FFmpeg/FFprobe/MLT;
- the official `shotcut-src-26.4.30.txz` corresponding-source URL/SHA-256 for that media carrier;
- **PyInstaller 6.21.0** as build-only freezer provenance;
- **NSIS 3.12** as the build-only Windows installer compiler, acquired as exact Chocolatey package `nsis.install` version `3.12.0` from the configured HTTPS community feed and verified again by `makensis /VERSION`.

Schema v5 makes `media.corresponding_source` mandatory and validates it with the same credential-free HTTPS and canonical lowercase SHA-256 rules as binary downloads. The source artifact is provenance/source-offer material, not an application runtime dependency; release automation does not download 266 MB of source merely to assemble the installed product. Instead the validated profile itself is staged as `legal/release-inputs.windows-x86_64.json` before D-044 hashes the immutable payload, permanently binding each candidate to the exact source coordinate reviewed for its media carrier.

The Node release ZIP replaces the earlier bare `win-x64/node.exe` acquisition without changing the selected Node version. The workflow verifies the official ZIP SHA-256, extracts exact `node.exe` and the complete upstream `LICENSE`, checks `v24.19.0`, and stages the license under `legal/node/LICENSE.txt`.

The media profile originally pointed to Kdenlive standalone 26.04.3 because it had passed Windows MLT/FFmpeg engineering tests. Review of the actual executable build configuration later found `--enable-nonfree`; D-058 rejects that carrier for public redistribution and replaces it with official Shotcut portable `26.4.30`, binary SHA-256 `986e7a13ef5fcce00f98ae3fefd7bfc9d280c4ccb7a803a63d623caf0688cb6a`, with official source bundle SHA-256 `fa2efbab8c1510c2b5a9ea812e0690d128f891d2e2ff61540accb21abf4c7442`.

The profile parser rejects unknown fields, unsafe/non-canonical relative paths, non-HTTPS or credential-bearing URLs, non-canonical SHA-256 values, line-break injection, unsupported acquisition providers and unsafe package/version tokens before build automation can consume them.

`tools/export_release_profile.py` exports only executable build inputs. Corresponding-source coordinates deliberately remain provenance data in the immutable profile rather than environment variables that could accidentally become runtime/build dependencies. Product version continues to come from `uv_studio.__version__`.

## Python dependency ownership

`requirements-uv.txt` remains the short, human-reviewed direct runtime requirement set. `requirements-uv-release-win-x86_64.txt` is the complete 32-package shipping resolution for Windows x86_64 / CPython 3.13.14. Release installation/build commands resolve direct requirements through this constraints file.

`tools/verify_release_python_lock.py` requires the exact Python patch version, every locked package at the exact locked version, and no application runtime package outside the lock apart from bootstrap package-management tools.

## Frontend dependency ownership

The frontend retains its complete `frontend/package-lock.json` and release CI uses `npm ci`; Stage 9 does not create a duplicate lock. The release profile independently pins the Node runtime version and exact official Windows archive.

## Media runtime ownership

MLT depends on adjacent DLLs, plugins, data and FFmpeg libraries. Stage 9 packages a coherent Windows carrier rather than extracting `melt.exe` in isolation. D-044 hashes every staged file and D-047 requires packaged resolution only from manifest-owned paths.

Package identity alone is not enough to approve FFmpeg redistribution. `tools/audit_ffmpeg_release.py` executes the exact selected `ffmpeg.exe -buildconf`, rejects `--enable-nonfree`, and stages bounded evidence as `legal/ffmpeg-buildconf.json` before D-044 builds the manifest. D-058 owns final acceptance of the Shotcut carrier.

The manifest component identity for FFmpeg, FFprobe and MLT is `shotcut-portable-26.4.30`; runtime diagnostics separately prove each executable starts from the release manifest. Shotcut itself is only an acquisition carrier and its application/UI/helper surface can be pruned only with explicit evidence.

## Build-tool ownership

PyInstaller and NSIS remain build-only. Their exact versions/acquisition coordinates are recorded so freezer or installer compiler versions cannot silently float. The generated installer must still carry the exact D-044-manifested payload and the installed product performs deep verification before activation.

## Evidence before acceptance

Python 3.13.14 compatibility, Node 24.19.0 compatibility, exact shipping graphs and the NSIS acquisition boundary were proven by Stage 9 CI/release runs before D-046 acceptance. Subsequent media review demonstrated why this profile must be upgradeable under explicit review: Kdenlive runtime behavior was green but its FFmpeg build was not redistributable.

The Shotcut replacement has independently passed the full packaged Windows proof on `e1fba386f5fefd46806317a844023169e7ecacc7`; D-058 remains the separate acceptance gate for final media redistribution/source evidence.

## Byte-level reproducibility

Exact versions, binary hashes and corresponding-source hashes are necessary but not sufficient for byte-for-byte product integrity. D-044 remains the final packaged trust boundary and records exact relative paths, file sizes and SHA-256 for the actual staged backend, frontend, Node, legal/provenance files and curated media runtime.

A future Python, Node, media distribution, source bundle or build-tool upgrade must update this profile only after the relevant compatibility/release evidence is repeated. It is a reviewed product-runtime/build-input change, not an automatic dependency refresh.
