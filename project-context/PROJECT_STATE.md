# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: stage-6-sequence-continuity-review -->

**Updated:** 2026-08-16

**Repository:** `BogdanAIP/uv-studio`

## Product now

Stage 5 is merged on `main` through PR #32 / merge commit `6f7531d9b87f569074a632972ca11e36562e8bd7`, with the bounded post-merge hardening completed by PR #34 / merge commit `e98015da54834a2684e075ede121847df59eda0a`.

UV Studio currently has:

- UV-owned FastAPI runtime and secret/configuration boundary;
- canonical file-first Project Store and portable `.uvproj.zip` archives;
- provider-neutral Recipe Registry and Production Policy;
- semantic Capability Registry with local, MCP and exact native compatibility adapters;
- D-017 exact one-shot authorization for remote/non-free execution;
- MLT behind a UV-owned editor adapter and FFmpeg as the deterministic authoritative media/render layer;
- complete targeted existing-video range workflow through Brief -> Plan -> Candidate -> Review -> Accept -> render/preview;
- Stage 5 transcript/translation/PreparedSpeech/alignment/review/accepted-dubbing state;
- local whisper.cpp ASR baseline, optional Argos translation and optional WhisperX alignment;
- D-017-protected Edge TTS reuse;
- deterministic accepted dubbing render, project-owned WebVTT export and bounded artifact download;
- optional Stage 6 linked-shot continuity state with explicit planned/observed separation, SHA-bound takes, accepted/rejected lifecycle, current Review semantics and explicit re-anchor;
- bounded TimelineContext over accepted-anchor tail and candidate head with fail-closed trust checks for approved anchor observations;
- provider-neutral ephemeral Review Assist over semantic `media.understand`, where VLM suggestions never create canonical Review/Accept/re-anchor state and suggestion collections are bounded before normalization;
- acceptance-time revalidation of exact current review-target coverage and required pass outcomes;
- load/reopen-time revalidation that every already accepted take still has a current approved Review bound to the exact current plan, anchor, take SHA, complete target set and passing required targets;
- maintained production-browser E2E composing targeted replacement, dubbing and linked-shot continuity on Ubuntu and Windows.

## Architecture invariants

- Project Store/domain state is canonical. MLT, FFmpeg, VideoClaw compatibility code and optional model runtimes are adapters/engines, not second project authorities.
- Reuse-first/orchestration-first is mandatory for general editor/media primitives.
- GUI, scripts, AI and MCP must converge on UV-owned semantic commands/workflows; direct canonical-state mutation is not an automation API.
- Remote/non-free execution stays behind D-017.
- Optional continuity, dubbing, music and other specialized workflows must remain optional.
- Windows and Linux remain continuous engineering targets.
- Development and PR review are Chat-first under D-040: automatic Codex code review is excluded from the UV Studio workflow and Codex is used only when the repository owner explicitly launches it manually.

## What is verified

PR #34's final review head `e0f143dcb25e3e8a3190f86b92230fd0af11d0de` passed exact-head PR run `31800185611`: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline were all green, including the permanent Playwright browser user-outcome scenario on both operating systems.

PR #34 merged at `e98015da54834a2684e075ede121847df59eda0a`. The mechanical idle closure head `9f47f5ac2e4c6cc608162550313894bdb6e194ae` then passed push run `31801356588` with all five permanent checks green, including browser E2E on Ubuntu and Windows. This satisfied the Stage 6 entry gate.

The initial Stage 6 implementation head `9c0f9dbc0ff67dc6bce283d5ebc2db1f106669fc` passed exact-head PR run `31809934767` with all five required jobs green: development-context, Ubuntu/Windows bootstrap and Ubuntu/Windows app-baseline. Both app-baseline jobs passed API integration, real HTTP, FFmpeg/MLT real-media coverage, frontend lint, high-severity dependency audit, production build and the permanent Playwright browser scenario.

The browser scenario creates one project and composes the targeted existing-video workflow, Stage 5 dubbing and Stage 6 linked-shot continuity. It accepts and explicitly re-anchors two linked video takes and verifies bounded TimelineContext contains observations from the exact current approved anchor Review.

A later Chat-only pre-merge audit hardened two additional trust boundaries. Exact code head `5d075abb1aad35498baab5a46d0895c928097dd1` passed PR CI run `31945066401` / #1316 with all five required jobs green, including Ubuntu and Windows browser E2E. Accepted state now fails closed on load/reopen if its approved Review is later corrupted or no longer matches the current plan/anchor/targets/required pass outcomes, so such a take cannot remain usable for re-anchor or future-shot anchoring. Review Assist normalization also rejects result-count mismatches and more than `MAX_OBSERVATIONS_PER_REVIEW` observations before constructing suggestion objects. The transient earlier run #1314 exposed only an obsolete test message expectation after the accepted-state check intentionally moved earlier; the test was updated to require the stronger load-time failure and #1316 verified the result.

Focused tests now prove project archive round-trip, stale plan/media rejection, Review Assist non-authority and bounded suggestion input, preserved not-found semantics, fail-closed rejection of corrupted approved-anchor observations, fail-closed Accept when an approved Review's required result is corrupted from `pass` to `fail` before acceptance, and fail-closed reopen/re-anchor when the same corruption occurs after acceptance.

## Stage 6 sequence continuity/review ready for review

PR #35 implements optional linked-shot continuity only where an accepted prior shot/take must constrain a later shot. Standalone clips and existing one-shot workflows remain free of sequence state and review overhead until the user explicitly enables the mode.

The implemented architecture is:

- planned continuity is distinct from observed accepted-take state;
- plans carry explicit locks, allowed changes and review targets;
- prepared takes bind exact project-owned video bytes and exact plan revisions;
- Review binds candidate SHA, plan revision and anchor identity;
- Accept independently revalidates current target coverage, required pass outcomes, candidate bytes, plan revision and anchor binding before promotion;
- accepted state independently revalidates the same authoritative Review evidence on load/reopen, preventing corrupted accepted records from remaining trusted anchors;
- re-anchor remains an explicit semantic command over an accepted current take;
- bounded `TimelineContext` is a derived inspection view from canonical Project Store state, never a second timeline/EDL authority;
- trusted anchor observations are exposed only from a current approved Review whose take/SHA/plan/anchor/target binding still matches current state;
- optional VLM assistance uses an ephemeral provider-neutral `media.understand` Review Assist package and suggestion schema; even a normalized `approved` suggestion leaves the take prepared until a human creates the canonical Review and explicitly accepts it;
- Review Assist enforces its advertised result/observation collection bounds before normalizing external model output;
- `browser-use/video-use` remains an architecture donor only, while PySceneDetect remains only a future optional scene-boundary candidate.

The full Chat-only pre-merge audit found four trust/input-boundary issues and all are covered by regression tests: stale/corrupted approved-anchor observations cannot be reused as TimelineContext facts; corrupted approved Review outcomes cannot pass Accept; post-Accept corruption invalidates the accepted state itself before it can be reused as an anchor; and Review Assist cannot normalize oversized observation collections. No Qwen-specific Stage 6 binding was added.

D-040 records the repository-owner development policy: Chat owns normal development/review, automatic Codex code review is not part of readiness or lifecycle, and Codex is reserved for explicit manual owner use. The repository itself contains no Codex review workflow; any automatic `chatgpt-codex-connector[bot]` review activity is external integration behavior rather than project automation.

The lifecycle remains `review`; merge remains a reviewer/integration action and is not part of this transition.

## Cross-cutting backlog

Remaining non-blocking debt includes recursive portability validation for general JSON mappings, broader codec/device fixtures, measured Python/frontend quality gates, dependency reproducibility hardening, stronger renderer file-handle/TOCTOU hardening at media trust boundaries, richer continuity-authoring UX and eventual retirement of transitional compatibility surfaces such as `/api/stages`.

## Development-memory lifecycle

D-038 keeps one canonical active slice. PR #35 is the current review slice on `stage-6/sequence-continuity-review`, based on verified idle main head `9f47f5ac2e4c6cc608162550313894bdb6e194ae`. The declared next handoff is `stage-7-music-video-mode`; it remains blocked until PR #35 is reviewed, merged, `main` closes back to `idle`, and the post-merge closure checks are green.
