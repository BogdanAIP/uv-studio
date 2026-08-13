# Next Task

<!-- uv-next-slice: stage-5-correctness-browser-e2e -->

Updated: 2026-08-13

## Goal

Close the concrete Stage 5 correctness and user-quality gaps found by the post-merge audit before beginning Stage 6 sequence continuity.

## Required work

- give dubbing Review history an explicit chronological/current-review contract; never use UUID lexical order as recency;
- make translation identity immutable across `dubbing_id` and target language, and create a new translation ID for a new language;
- select a newly created TTS PreparedSpeech take explicitly;
- make transcript/translation mutation vs PreparedSpeech binding checks transaction-sized under the Project Store lock;
- verify current source/prepared-audio bytes at Review/Accept/render trust boundaries where stored SHA identity is relied on;
- stop presenting the legacy VideoClaw root workspace as a working UV-owned product surface unless its backend is deliberately isolated and supported;
- add real browser E2E for the targeted existing-video and dubbing user outcomes using a maintained reusable browser-testing framework;
- keep the existing Project Store, Command API, Capability Registry, D-017, MLT and FFmpeg boundaries intact.

## Completion proof

The slice is complete only when focused regression tests cover the discovered defects, browser E2E runs in CI, all declared checks are green on the exact review head, and the repository returns to `idle` after merge.

## After this slice

Proceed to `stage-6-sequence-continuity-review` only after this hardening slice merges and repository context is closed to idle.
