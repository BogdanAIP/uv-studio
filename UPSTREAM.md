# Upstream Sources

## VideoClaw

Repository: `HITsz-TMG/VideoClaw`  
License: MIT  
Pinned commit: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`  
Observed commit date: 2026-07-17  
Imported application subtree: `video-claw/video-claw`

UV Studio intentionally does **not** treat the whole upstream repository as product source. The target baseline is the modern application subtree containing the FastAPI backend, Next.js frontend, current pipelines, model configuration and Windows installer.

## Import policy

- never import from moving `main` without updating the pin through a reviewed change;
- preserve upstream MIT attribution;
- use deterministic vendoring tooling;
- import only the configured subtree;
- do not silently merge upstream changes;
- compare a candidate new upstream pin against the current pin before updating;
- baseline imported code before cleanup/refactoring.

## Upstream update procedure

1. inspect upstream commits since the current pin;
2. identify changes inside the imported subtree;
3. run baseline/regression tests on a temporary import;
4. document compatibility or required migrations;
5. update `upstream/video-claw.lock.json` and this file;
6. import the new revision in a dedicated PR;
7. never mix an upstream-pin update with unrelated feature work.

## Other projects

LocalMiniDrama, ViMax, Jellyfish, DirectorSKILL, `Emily2040/seedance-2.0`, OpenClaw and other researched repositories are not automatically vendored dependencies. They may be used as external runtimes, adapters, or architecture/method donors only after license and integration review.