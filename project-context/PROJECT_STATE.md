# Project State

<!-- uv-context-state: draft -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-03

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is back in `draft` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The pre-Ready adversarial repair passed material CI #4507, synchronized Draft CI #4510, and post-Ready exact-head CI #4516 (`33716978812`) **5/5 SUCCESS** on frozen head `d38aec58f491f46db79f1ee2423d53d8f2ce4a7d`. After Ready, a new inline P2 review thread `PRRT_kwDOT0Lyms6ex9SS` identified a root-level staging recovery gap. The finding survived falsification, so the PR was immediately returned to Draft before any material repair.

## Confirmed root-staging P2

Several current publishers intentionally stage long-running or partial bytes at `ProjectStore.root`, outside every canonical project directory:

- Generation: `.uv-generation-<attempt>-*`;
- source upload: `.uv-source-upload-<source>.*.upload`;
- WebVTT: `.uv-webvtt-<artifact>-*`;
- crash-safe FFmpeg concat manifest: `.uv-ffconcat-*`;
- crash-safe timeline assembly: `.uv-timeline-assemble-<artifact>-*`.

Normal completion removes these paths in `finally`, but hard process termination bypasses `finally`. Startup recovery currently enumerates healthy projects and scans only per-project managed roots (`sources`, `assets`, `artifacts`, `exports`), so root-level staging files have no restart cleanup path. Repeated interrupted operations can therefore accumulate unbounded transient bytes in the Project Store root.

The repair must remain bounded to reserved UV-owned root staging namespaces. It must not traverse or delete arbitrary root content, project directories, recovery quarantine files, or canonical project media. Hard-kill regressions must prove exact matching staging files are reclaimed on startup while near-miss ordinary root files and directories remain untouched.

## Existing Stage-19 authority retained

All previous Stage-19 repairs remain in force: schema-v1/v2 exact historical identity, prepared-UOW recovery before archive sampling, archive locking/snapshot authority, staged/fenced WebVTT and Generation publication, Generation Job/artifact/Take recovery, explicit Take Undo preservation, source/WebVTT/legacy-art/prepared-audio recovery, redo-owned media preservation, publication-marker reference identity, Generation digest authority, exact redo-chain reachability, reserved Generation namespace, canonical Generation path/lineage, same-ID Generation authority immutability and immediate-next-action Product Truth behavior.

Key final-preflight commits before this P2 include `f0ea9f54854895646776572edf0602dffc5c1309`, `07253a6e8646b7caeb12bc92de5e89530f2b8847`, `6e16b5bcd42d887b14b22c36173bb77f4b78dc14`, `553b240dc8c1f4f06d25ee0b9dfdacd3a8bc2a27`, `abed09f7780159e2a6e16905993ca6b2383033f9`, `7e31b75b1aee9ba92a7e4043a5359195ed12d07e`, `8a3bc170a43a8f766635e6b5b23399e9452d3f7d`, `2eacf0ba055baf5e716ac1222aa7cec34fd2b5a7`, `808cf64f1c14484e6268e28412bbf937ac2e9d42`, `61acf52bf15568dd76ff082509fb5c332e1383d5`, and `ae95ad0d83d240dcbb29d51b0038f95eaa8b1fb1`.

## Verification before this repair

- material/test head `ae95ad0d83d240dcbb29d51b0038f95eaa8b1fb1`: CI #4507 (`33646746316`) **5/5 SUCCESS**;
- synchronized Draft head `3d45b3a999765c314ba289f973739f6d377f7eba`: CI #4510 (`33647534673`) **5/5 SUCCESS**;
- frozen Ready head `d38aec58f491f46db79f1ee2423d53d8f2ce4a7d`: post-Ready CI #4516 (`33716978812`) **5/5 SUCCESS**;
- prior inline threads were resolved; current P2 `PRRT_kwDOT0Lyms6ex9SS` remains intentionally unresolved until the repair has exact-head evidence.

## Next required action

1. add regression-first coverage for root-level staging cleanup across all reserved staging namespaces and near-miss preservation;
2. implement one centralized startup reconciliation pass over `ProjectStore.root` before per-project Generation/publication recovery;
3. synchronize Project Store/archive recovery documentation;
4. obtain exact material-head CI **5/5** and synchronized Draft CI **5/5**;
5. reply to and resolve P2 only with exact evidence;
6. run one final read-only cumulative preflight, refreeze to `review`, mark Ready, require post-Ready exact-head CI **5/5**, and perform the mandatory genuinely fresh ordinary-ChatGPT semantic review;
7. merge only on `review_validity=CURRENT`, `status=PASS`, `reported_findings=0` with clean live BASE/HEAD/CI/thread identity.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
