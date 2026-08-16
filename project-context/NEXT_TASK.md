# Next Task

<!-- uv-next-slice: stage-7-music-video-mode -->

## Goal

Start Stage 7 Music Video Mode only after Stage 6 sequence continuity/review is reviewed, merged and the repository returns to a green idle lifecycle.

## Required direction

- compose existing Project Store, Capability Registry, editor/render and production-policy primitives rather than introducing a second project/media engine;
- integrate `musical-mv-storyboard` only through a tested, license-compatible adapter boundary;
- make song/lyrics/structure analysis and the Music Map explicit project-owned state where persistence is required;
- keep music-aware shot timing, beat-sync, source review, sample-first generation and evidence-based final review as music-specific policy rather than universal editor behavior;
- preserve local/free baselines where viable and keep remote/non-free generation behind D-017 authorization;
- keep GUI, scripts, AI and MCP on the same UV-owned semantic command/workflow contracts;
- add a complete user-facing music-video excerpt path without making music mandatory for general video, dubbing or targeted existing-video editing.

## Completion proof

Stage 7 must prove a 20–30 second music-video excerpt can be planned, assembled, reviewed and rendered through the product UI with music-aware timing and explicit provider/cost behavior, while permanent non-music regression scenarios remain green.

## Entry gate

Do not start this slice until `stage-6-sequence-continuity-review` is merged, its lifecycle is closed to `idle`, and the post-merge idle head passes all permanent required checks.
