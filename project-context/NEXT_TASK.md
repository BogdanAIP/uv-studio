# Next Task

<!-- uv-next-slice: stage-9-desktop-productization-release-hardening -->

## Goal

Start Stage 9 Desktop Productization & Release Hardening only after Stage 8 Additional Recipes is reviewed, merged and the repository returns to a green idle lifecycle.

## Required direction

- package/provision the UV Studio frontend, backend and required FFmpeg runtime for native Windows use without separately prepared Python, Node/npm or FFmpeg;
- add launcher/process supervision, installer/uninstaller and versioned update/migration behavior;
- provide backup/recovery, cancellation and diagnostics UX suitable for user data;
- add capability self-checks and explicit optional-dependency diagnostics;
- prove clean-machine installation and representative weak-hardware/long-project behavior;
- perform final license/security/dependency release audit and produce signed release artifacts;
- preserve all five permanent user-facing regression scenarios through the packaged application;
- keep optional WSL/cloud/provider integrations from blocking normal native-Windows use.

## Completion proof

Stage 9 is complete when a user can install and run UV Studio on a clean Windows machine without manually preparing development toolchains, canonical projects survive upgrade/backup/recovery, all permanent regression scenarios pass through the packaged app, and release artifacts/documentation are ready.

## Entry gate

Do not start this slice until `stage-8-additional-recipes` is merged, its lifecycle is closed to `idle`, and the post-merge idle head passes all permanent required checks.
