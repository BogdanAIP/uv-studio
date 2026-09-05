# Next Task

<!-- uv-next-slice: legacy-music-action-envelope-retirement -->

## Target

Complete frozen review acceptance for PR #95 after both confirmed Music render P2 findings were repaired.

## Frozen material evidence

Material head `1ccf2e4cf07231064c0ab10c16dd3e0eeafd4116` passed CI #4897 with all five permanent jobs SUCCESS. PR-event CI #4899 on the same bytes and current PR metadata also passed all five permanent jobs SUCCESS, including both Stage 4A real-media suites and both browser user-outcome suites.

The direct `video.render_music_video` boundary now enforces both parts of the retired Product Workflow render prerequisite:

1. current rhythm audit must be fully aligned;
2. the audit Direction/Map revisions must match the loaded Direction/Assembly/Map revisions being rendered.

Focused acceptance proves both fail closed before FFmpeg/FFprobe and create no render artifact.

## Review sequence

1. Mark PR #95 Ready against this context-only review freeze.
2. Require one exact review-head Ready CI run with all five permanent jobs SUCCESS. Ignore any event-race run created while context says `review` but the PR event still says Draft; only a later Ready run is authoritative.
3. Reply to both confirmed P2 review threads with exact repair and CI evidence, then resolve them and verify zero unresolved threads.
4. Perform a new genuinely fresh ordinary-ChatGPT semantic review using `.agents/skills/code-review/SKILL.md` v1.0 with immutable BASE `57bbbec41b2e82e556d620efb21f3b6cdf2a5a47` and the exact frozen live review HEAD.
5. Merge only if the fresh result is CURRENT/PASS with zero findings, live HEAD is unchanged, exact-head CI remains green and no unresolved review thread exists.
6. After merge create the mandatory separate D-038 lifecycle closure to `idle` before selecting the next migration slice.

Any material repair supersedes the review freeze and requires returning PR #95 to Draft first.
