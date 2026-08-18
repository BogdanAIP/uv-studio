# D-060 — Product UX surface boundary

**Status:** Accepted

## Context

Stage 9 release engineering proved that the packaged application could install, launch, persist projects, execute the permanent browser outcomes, recover, update, and roll back. A real installed-app review then exposed a separate product defect: technically valid backend concepts and donor-era UI were still leaking directly into the everyday interface. The result was operationally correct but visually inconsistent, difficult to understand, and full of implementation terminology that ordinary users should never need to know.

The fix must not create a second product model or hide functionality by deleting it. UV Studio already has durable semantic authorities: Project Store, task recipes, Editor Commands, capability state, authorization, and project-owned artifacts. The frontend must derive its visible surfaces from those authorities rather than inventing parallel workflow semantics.

## Decision

1. **Project and recipe state govern the product surface.** The frontend may add presentation metadata such as icons, concise labels, ordering, and grouping, but it must not create a second canonical recipe/capability authority.

2. **The primary editing geometry is assets → viewer → contextual inspector → timeline.** This is the default workspace for direct media editing. AI actions operate on the currently selected project object or time range instead of appearing as a disconnected global workflow.

3. **Specialized capabilities are contextual workspaces, not a permanent vertical stack.** Music-video preparation, local photo/video composition, lip-sync, dubbing, continuity, review, and export remain available when the current recipe/project state makes them relevant. Their backend APIs and state machines remain unchanged.

4. **Progressive disclosure is mandatory for technical and advanced controls.** Everyday project screens show the task, materials, preview, editing actions, checks, and result. Advanced configuration and diagnostics live under Settings/System or an explicit advanced disclosure.

5. **Implementation vocabulary is not product vocabulary.** The following must not be used as ordinary UI labels or explanatory copy: roadmap Stage numbers, D-xxx decision numbers, schema versions, project/edit/candidate/review IDs, raw capability IDs, MCP/Command API terminology, Project Store internals, FFprobe/FFmpeg implementation details, release-manifest details, or provider implementation IDs. These values may remain available in diagnostics when they are genuinely useful for troubleshooting.

6. **Unavailable actions must be understandable.** A user-facing action is either hidden when irrelevant or accompanied by a concise explanation of the unmet prerequisite. Unexplained inert controls are not an acceptable state.

7. **Settings configure the machine, not project semantics.** Provider credentials, model defaults, proxy/network settings, and other machine-local values remain outside canonical project data. API keys retain write-only/local secret semantics. A missing provider/model registry must not make unrelated project editing controls inert.

8. **No capability is removed merely to simplify the interface.** A capability can move behind a contextual workspace, secondary tab, or advanced disclosure, but removal requires separate evidence that it is obsolete and unused.

9. **Product acceptance requires packaged UX evidence.** Source-mode component correctness is insufficient for desktop productization. Permanent browser outcomes must exercise the same packaged frontend/backend navigation used by the installed application, and a new Stage 9 Windows artifact must be reviewed as an installed application before Stage 9 is considered closed.

## Consequences

- The frontend is intentionally less isomorphic to the backend module tree.
- Existing editor, dubbing, continuity, music, render, and Stage 8 APIs remain semantic authorities even when their UI is reorganized.
- Donor-era components may remain in the repository while compatibility evidence is still needed, but inactive donor surfaces must not re-enter primary navigation accidentally.
- New capabilities should first define their recipe/project relevance and only then add a visible surface.
- UI tests should assert user outcomes and stable product affordances rather than internal Stage names or implementation IDs.

## Verification

- Frontend lint/build must remain green on supported Node runtimes.
- Permanent browser user-outcome suites must pass through the product workspaces.
- Packaged Windows smoke/browser evidence must exercise Projects, Settings, project workspace navigation, and the same project APIs as the installed application.
- A human installed-app review remains part of Stage 9 product acceptance.
