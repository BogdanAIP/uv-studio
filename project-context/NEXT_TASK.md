# Next Task

<!-- uv-next-slice: stage-8-additional-recipes -->

## Goal

Start Stage 8 Additional Recipes only after Stage 7 Music Video Mode is reviewed, merged and the repository returns to a green idle lifecycle.

## Required direction

- broaden the studio mainly by composing the Project Store, Recipe Registry, Capability Registry, production-policy hooks and existing editor/render primitives rather than adding new universal engines;
- add story video, commercial/product, photo-to-video, visualizer, performance/lip-sync and free-project modes as focused recipes/capability mappings with only the product-owned state and UI each actually needs;
- keep paid/remote providers optional and behind D-017 authorization;
- preserve local/free baselines where viable and keep provider IDs out of canonical project state;
- reuse Stage 4 targeted edit, Stage 5 dubbing, Stage 6 continuity and Stage 7 music primitives selectively instead of forcing them into every recipe;
- keep GUI, scripts, AI and MCP on the same UV-owned semantic command/workflow boundaries;
- maintain all permanent regression scenarios while adding representative user-facing paths for the new recipe families.

## Completion proof

Stage 8 is complete when the additional modes are mostly recipe + capability mapping + production policy + minimal task-specific UI, each can execute its relevant user outcome without introducing a competing project/media engine, and the permanent general-video, narrated-video, music-video, dubbing and targeted-edit scenarios remain green.

## Entry gate

Do not start this slice until `stage-7-music-video-mode` is merged, its lifecycle is closed to `idle`, and the post-merge idle head passes all permanent required checks.
