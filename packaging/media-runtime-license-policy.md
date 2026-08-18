# Stage 9 media-runtime license asset policy

This file accompanies `media-runtime-license-files.windows-x86_64.json`.

The license-file manifest is intentionally separate from the 52-PE component provenance map. The component map answers **what binary is this and where is its corresponding source?** This file set answers **which concrete license/notice texts are staged beside the shipped binaries?**

Release rules:

- every retained component must be covered by at least one license/notice asset;
- a single common license text may cover multiple components;
- a component may require multiple assets (for example GCC runtime plus Runtime Library Exception, or codec license plus patent notice);
- remote assets must use HTTPS and are bounded by per-file and aggregate size limits;
- carrier-local assets are read only from the exact already-verified media carrier;
- once hashes are pinned, any changed upstream bytes fail the release closed;
- all staged license assets are written before D-044 builds the immutable release manifest.

The first audit pass may temporarily keep `require_hashes=false` only to measure the exact upstream bytes. D-058 cannot be accepted on such a pass. The acceptance candidate must set `require_hashes=true` with every asset SHA-256 pinned and pass the exact Windows release workflow.
