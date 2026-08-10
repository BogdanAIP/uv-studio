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

Repository state is the durable project memory. A new ChatGPT development chat should start by reading:

1. `project-context/PROJECT_STATE.md`
2. `project-context/NEXT_TASK.md`
3. `project-context/DECISIONS.md`
4. `ROADMAP.md`
5. the latest merged PR / current open PR

Do not rely on an old chat transcript to know the current implementation state.

## Development rule

Every meaningful development slice must end with:

- code/tests committed to a feature branch;
- a PR describing what changed and what was verified;
- `PROJECT_STATE.md` updated to the actual repository state;
- `NEXT_TASK.md` containing one concrete next development target;
- architectural decisions recorded in `DECISIONS.md` when they change long-term behavior.

See `DEVELOPMENT_PROTOCOL.md` for the full cross-chat workflow.
