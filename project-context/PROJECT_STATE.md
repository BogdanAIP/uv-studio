# Project State

<!-- uv-context-state: review -->
<!-- uv-active-slice: project-identity-v2-compat-reader -->

**Updated:** 2026-09-01

**Repository:** `BogdanAIP/uv-studio`

## Current lifecycle

`project-identity-v2-compat-reader` is frozen in `review` for PR #89 on branch `stage-19/project-identity-v2-compat-reader`, based on lifecycle-closed `main` at `52be1939eca51d7147990288cfc6258b023c2cd2`.

The last material change is prepared-audio recovery commit `9b56d5f2fb071e212bf9fcf5900301d8f6ac1d28`. The synchronized final Draft context head `fb2db3e964a6ff73b32618cc68625b668e4d28a6` passed CI #4377 (`33543179747`) **5/5** after PR body/context synchronization. Immediately before this context-only refreeze, live PR review threads were re-resolved and **0 unresolved** remained. No runtime, test, schema, documentation-contract or product code is allowed to change after this freeze without returning the PR to Draft.

## Fifth review repair completed

### P2 — preserve redoable generated output bytes during startup recovery

The required fresh ordinary-ChatGPT review of frozen fourth-repair head `64412b254f53a159c759a6183ac38365c6917e37` found that startup orphan recovery could quarantine `artifacts/generated_<attempt>.*` bytes still required by the current durable `ProjectUnitOfWork` Redo branch after output/Take Undo.

Repair `dcb5f6158f1a92225501904ddad0fbe6309162e7` protects managed paths derivable from committed `project.json` snapshots in `history.entries[history.cursor:]`. A later canonical commit truncates that redo suffix through the existing UOW contract and automatically removes protection. Binary media remains outside UOW snapshots and no new authority is introduced.

Regression `fad2134f02cddb9a6ac3f364d76543c2d068cb8d` proves both `two Undo -> restart -> two Redo` exact-byte/identity preservation and redo-branch truncation followed by genuine-orphan quarantine. Final fifth-repair Draft head `78b62033e1739f2eb2e27e3beb4fcece6a049f30` passed CI #4369 (`33539281258`) **5/5**.

## Sixth Draft repair completed

### P2 — recover prepared-audio hard-crash publications

Prepared-audio upload and artifact promotion stage under `assets/.aud_<uuid>...upload|promote`, atomically publish final `assets/aud_<uuid>.*`, probe canonical bytes and only then persist the owning `ProjectReference`. Hard process loss can therefore leave either self-identifying staging bytes or final unregistered bytes.

Regression `44d7e036230f50e2a82cd908da13ec67508bd041` covers final prepared-audio orphan bytes, `.upload`, `.promote`, registered prepared audio, ordinary near-miss preservation, archive rejection before recovery, exact-byte quarantine outside the project tree and successful archive after recovery.

Repair `9b56d5f2fb071e212bf9fcf5900301d8f6ac1d28` extends startup managed-output scanning to `assets` and the exact `aud_<32-hex>` namespace, including leading-dot self-identifying staging names. Current registered and current redo-owned paths are preserved before filename matching; ordinary assets such as `aud_preview.wav` remain untouched.

Exact material head `9b56d5f2fb071e212bf9fcf5900301d8f6ac1d28` passed CI #4374 (`33542443308`) **5/5**. Both P2 inline threads from the fifth/sixth repair cycle were replied to with evidence and resolved before the final Draft sync.

## Final Draft verification

Exact synchronized Draft head `fb2db3e964a6ff73b32618cc68625b668e4d28a6` passed CI #4377 (`33543179747`) **5/5**:

- `development-context` — success;
- `bootstrap (ubuntu-latest, 3.11)` — full unit suite success;
- `bootstrap (windows-latest, 3.11)` — full unit suite success;
- `app-baseline (ubuntu-latest)` — API, real-media, frontend and browser Product Truth success;
- `app-baseline (windows-latest)` — API, real-media, frontend and browser Product Truth success.

Immediately before refreeze, live PR #89 remained open, unmerged and Draft with BASE `52be1939eca51d7147990288cfc6258b023c2cd2`, HEAD `fb2db3e964a6ff73b32618cc68625b668e4d28a6`, and zero unresolved inline review threads.

## Stage-19 invariants retained

The frozen review candidate preserves:

- canonical Project schema v2 with schema-v1 project/archive readability and exact historical recipe identity;
- exact historical schema-v1/v2 UOW snapshot restoration with migration only for validation;
- coherent cross-runtime Project/Generation/publication fencing;
- attempt-specific Generation recovery and exact size/SHA-256/provenance authority;
- current Production Take authority and durable explicit Undo preservation;
- self-identifying `src_`, `aud_`, `art_`, `sub_` and `generated_attempt_` crash recovery without provider/renderer replay;
- redo-owned media preservation until the durable Redo branch is truncated;
- arbitrary-path `timeline.assemble` durable publication markers with path + reference identity;
- archive consistent snapshot, streamed digest, technical lock exclusion and symlink fail-closed behavior;
- Product Truth immediate-next-action behavior and Production Undo/Redo refresh repair.

## Current review gate

Lifecycle is `review`. The branch is frozen except for lifecycle evidence. Next required sequence:

1. return PR #89 to **Ready for review** without changing the frozen Git head;
2. require authoritative post-Ready exact-head CI **5/5**;
3. re-resolve live repository/base/head/PR/thread identity;
4. run a completely fresh ordinary-ChatGPT semantic review under governing BASE `.agents/skills/code-review/SKILL.md` v1.0 against the exact frozen BASE..HEAD;
5. merge only if the fresh result is `CURRENT`, reports zero findings, exact-head CI remains green, base/head remain unchanged and zero unresolved review threads remain.

After merge, D-038 lifecycle closure to `idle` remains mandatory before starting the declared handoff.

## Out of scope

Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign and later D-070 compression work remain separate slices.
