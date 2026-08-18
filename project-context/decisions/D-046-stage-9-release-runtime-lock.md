# D-046 — Exact supported language runtimes and Windows release input profile

- **Status:** Accepted
- **Date:** 2026-08-17
- **Stage:** Stage 9 Desktop Productization & Release Hardening

## Context

The development dependency contract intentionally uses bounded direct ranges so maintainers can evaluate dependency upgrades. That is not sufficient for a shipped desktop application: resolving the same ranges on different dates or Python patch levels can produce different transitive graphs.

Stage 9 also cannot simply copy historical development runtime versions into the installer. A release build must select exact supported runtimes and exact downloaded payloads, then prove that selection against UV Studio before it becomes part of the package contract.

## Decision

`packaging/runtime-profile.windows-x86_64.json` is the machine-readable source of truth for the first Windows x86_64 release build inputs. Schema version 4 records:

- **CPython 3.13.14** and the exact shipping constraints file;
- **Node.js 24.19.0**, the existing npm lockfile, and the exact official Windows x64 release ZIP HTTPS source plus SHA-256;
- **Kdenlive standalone 26.04.3** as the pinned Windows media distribution, with exact HTTPS source plus SHA-256;
- **PyInstaller 6.21.0** as build-only freezer provenance;
- **NSIS 3.12** as the build-only Windows installer compiler, acquired as exact Chocolatey package `nsis.install` version `3.12.0` from the configured HTTPS community feed and verified again by the actual `makensis /VERSION` result before use.

The Node release ZIP replaces the earlier bare `win-x64/node.exe` acquisition without changing the selected Node version. The workflow verifies the official ZIP SHA-256, extracts the exact `node.exe` and complete upstream `LICENSE` from the same verified distribution, checks the executable reports `v24.19.0`, and stages the license under `legal/node/LICENSE.txt`. This makes runtime and notice provenance one reviewed acquisition unit rather than reconstructing Node notices separately.

The profile is parsed by `uv_studio.release_profile`, which rejects unknown fields, unsafe/non-canonical relative paths, non-HTTPS or credential-bearing download/source URLs, non-canonical SHA-256 values, line-break injection, unsupported acquisition providers, and unsafe package/version tokens before values may be exported into build automation.

`tools/export_release_profile.py` exports validated profile values for CI/release tooling. Product version is deliberately not duplicated in this profile: it comes from `uv_studio.__version__`.

### Python dependency ownership

`requirements-uv.txt` remains the short, human-reviewed set of direct UV Studio runtime requirements with compatibility ranges. It describes what UV Studio intentionally depends on.

`requirements-uv-release-win-x86_64.txt` is the shipping resolution for the selected Python/runtime/platform profile. It contains the complete 32-package graph observed and tested on Windows x86_64 / CPython 3.13.14, pinned as exact `name==version` constraints.

Release installation/build commands must resolve direct requirements through this constraints file rather than installing the broad ranges by themselves.

`tools/verify_release_python_lock.py` verifies all of the following:

- the executing Python patch version exactly matches the release profile;
- every locked package exists at the exact locked version;
- no application runtime package exists outside the lock, apart from bootstrap package-management tools (`pip`, `setuptools`, `wheel`).

The verifier is deliberately stricter than `pip check`: a dependency graph can be internally consistent while still drifting away from the release that was reviewed and tested.

### Frontend dependency ownership

The frontend already has a complete npm lock (`frontend/package-lock.json`) and CI uses `npm ci`, so Stage 9 does not create a second duplicate frontend package lock. The release profile independently pins both the Node runtime version and the exact official Windows release archive used in the package.

### Media runtime ownership

The first Windows package uses the already-proven Kdenlive standalone archive as one coherent media runtime rather than extracting `melt.exe` in isolation. MLT depends on adjacent DLLs, plugins and data files; the curated runtime closure is staged under the immutable release root and D-044 hashes every staged file.

The manifest component version for FFmpeg, FFprobe and MLT is the pinned distribution identity (`kdenlive-26.04.3`). Parsing arbitrary third-party CLI version text is not a release trust boundary. Runtime diagnostics separately prove that each executable starts and resolves from the release manifest.

D-052 subsequently narrows the acquired Kdenlive tree only by evidence-backed exclusions. This changes the installed file set but not the acquisition identity recorded here; D-044 remains authoritative for the exact curated bytes that are actually shipped.

### Build-tool ownership

PyInstaller and NSIS remain build-only. Their exact versions and acquisition coordinates are recorded in the same release input profile so a build cannot silently float freezer or installer compiler versions, but neither tool is an application runtime dependency and neither belongs in the installed Python graph.

NSIS is deliberately acquired by an exact package coordinate rather than by the SourceForge `/download` redirect previously used during early installer bring-up. Redirect/download landing behavior is not a stable byte-level release input. The release workflow requests exactly `nsis.install` `3.12.0`, requires the configured provider to be `chocolatey`, and refuses to compile the product installer unless the installed compiler reports exactly `v3.12`.

Package-manager acquisition is a build-tool bootstrap boundary, not the final product trust boundary. The generated installer must still install the exact D-044-manifested immutable payload, and the installed product performs its own deep verification before activation/smoke testing.

## Evidence before acceptance

The Python 3.13.14 Windows compatibility job successfully installed the existing direct core requirements, passed `pip check`, imported the UV Studio server, passed the unit suite, and recorded the complete 32-package graph used for the release constraints file.

The Node 24.19.0 Windows compatibility job successfully installed the existing `package-lock.json` graph through `npm ci`, passed frontend lint and configured high-severity audit, and built the production Next frontend.

The Kdenlive 26.04.3 standalone archive and its SHA-256 are already exercised by the permanent Windows real-media CI. Stage 9 reuses that exact proven payload for the package rather than selecting another FFmpeg/MLT distribution.

The first direct NSIS SourceForge archive attempt failed closed because the bytes returned by the redirect did not match the pinned SHA-256. That failure is preserved as evidence for moving build-tool acquisition to the exact Chocolatey package coordinate instead of weakening or replacing the checksum with an unreviewed response hash.

## Byte-level reproducibility

Exact versions and source archive hashes are necessary but not sufficient for byte-for-byte product integrity. D-044 remains the final packaged trust boundary: the assembled Windows release manifest records exact relative paths, file sizes and SHA-256 for the actual staged backend, frontend, Node, legal/provenance files and complete curated media runtime payload.

A future Python, Node, media distribution or build-tool upgrade must update this profile only after the relevant compatibility/release evidence is repeated. It is a reviewed product-runtime/build-input change, not an automatic dependency refresh.
