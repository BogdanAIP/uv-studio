# Stage 9 media-runtime license asset policy

This file accompanies `media-runtime-license-files.windows-x86_64.json`.

The license-file manifest is intentionally separate from the 52-PE component provenance map. The component map answers **what binary is this and where is its corresponding source?** This file set answers **which concrete license/notice texts are staged beside the shipped binaries?**

Windows Release #140 proved the bounded acquisition path: 27 license/notice assets covered all 28 retained media component groups, entered the D-044 immutable payload, installed successfully and survived A -> B -> A rollback.

The acceptance candidate now pins the SHA-256 of every one of those exact bytes and sets `require_hashes=true`. A remote origin is therefore an acquisition coordinate, not trusted mutable content: any changed response fails staging before D-044.

Release rules:

- every retained component must be covered by at least one license/notice asset;
- a single common license text may cover multiple components;
- a component may require multiple assets (for example GCC runtime plus Runtime Library Exception, or codec license plus patent notice);
- remote assets must use HTTPS and are bounded by per-file and aggregate size limits;
- carrier-local assets are read only from the exact already-verified media carrier;
- every staged asset SHA-256 is mandatory and must match the checked-in manifest;
- partial `legal/media-runtime/licenses/` output is removed on any failure;
- all staged license assets are written before D-044 builds the immutable release manifest.

`liblzma-5.dll` is scoped to the upstream XZ statement for liblzma itself (`0BSD`); GPL/LGPL terms used by other XZ utilities/build helpers are not assigned to that retained DLL.

Future hardening may vendor the already-audited license texts to remove release-time network dependence entirely. That is not permission to weaken the current hash gate: a carrier/component update still requires explicit provenance, license-map and exact Windows Release review.
