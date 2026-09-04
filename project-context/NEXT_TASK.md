# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Finish review of PR #95 on the new frozen identity after the confirmed rhythm-gate P2 repair.

## Frozen implementation evidence

Material Draft head `cb9852c6ee8b59020d00c0adc8c1b309705cced2` passed exact-head CI #4888 with all five permanent jobs SUCCESS. That evidence includes the repaired direct Music render prerequisite on both Ubuntu and Windows real-media suites and the complete browser user-outcome suite on both operating systems.

The repair remains deliberately narrow:

- `video.render_music_video` now requires the current Music Director rhythm audit to be fully aligned before media execution;
- the regression test proves a valid 500,000 µs misalignment is rejected before any FFmpeg/FFprobe runner invocation and without a render artifact;
- the aligned render path remains accepted;
- no Product Workflow Music mutation action, UI gate, replacement planner or new endpoint was restored.

## Review gate

1. Keep product/runtime/frontend/E2E bytes frozen.
2. Mark PR #95 Ready only after this context-only review refreeze is on the branch.
3. Require all five permanent jobs SUCCESS on the exact new review head.
4. Reply to and resolve the confirmed old P2 thread with exact repair and CI evidence.
5. Obtain a genuinely fresh ordinary-ChatGPT semantic review for exact BASE `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` and the new frozen review HEAD using `.agents/skills/code-review/SKILL.md` v1.0.
6. Merge only on `PASS`, `review_validity=CURRENT`, `reported_findings=0`, current exact-head green CI and no unresolved review threads.
7. After merge, complete the mandatory separate D-038 lifecycle closure before starting another product slice.
