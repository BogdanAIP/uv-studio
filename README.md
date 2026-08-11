# UV Studio

Universal Video Studio — open-source desktop/local-first video production and editing workspace.

The project is built by reusing proven open-source video-production components instead of rebuilding the whole stack. The initial technical base is the modern `video-claw/video-claw` application from `HITsz-TMG/VideoClaw`, pinned and tracked as upstream.

## Product scope

UV Studio should support task-specific workflows instead of one mandatory pipeline:

- general video creation;
- narrated/explainer video;
- story video;
- music video;
- dubbing/translation;
- targeted editing of an existing video range;
- photo-to-video;
- performance/lip-sync;
- commercial/product video;
- free-form projects.

Music, narration, story, characters, continuity and automatic review are optional capabilities, not requirements for every project.

## Development source of truth

Repository and GitHub state are the durable project memory. Coding agents and new development chats must start with `AGENTS.md`; it defines the required reading order, active-slice contract and multi-agent ownership rules. Do not rely on an old chat transcript to know the current implementation state.

## Development rule

Every meaningful development slice must end with:

- code/tests committed to one integration branch;
- a PR describing what changed and what was verified;
- `project-context/ACTIVE_SLICE.json` synchronized with the PR and its single handoff;
- `PROJECT_STATE.md` updated to the actual repository state;
- `NEXT_TASK.md` containing one concrete next development target;
- architectural decisions recorded in `DECISIONS.md` when they change long-term behavior.

See `DEVELOPMENT_PROTOCOL.md` for the full cross-chat workflow.
