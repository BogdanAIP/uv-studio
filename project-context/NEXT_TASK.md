# Next Task

<!-- uv-next-slice: project-identity-v2-compat-reader -->

## Current slice

`project-identity-v2-compat-reader` remains the only active Stage-19 slice in PR #89. Fresh review of frozen head `6603e46e932432e52e409a4a9656f5625bd9b540` returned `CURRENT / FINDINGS / 1 P1 / 15 rejected candidates`; the P1 is independently confirmed and the PR/lifecycle are back in Draft before material repair.

The defect is a same-path publication ABA/recovery race: an unresolved durable managed-publication marker can reserve path `P` while `P` is still absent, but a second runtime can currently create another marker for `P`, publish/register new bytes, and leave the older marker to quarantine those newer valid bytes during later recovery.

## Immediate continuation

1. Add a deterministic regression in the managed-publication recovery coverage: first marker reserves a path with no canonical bytes; a second same-path reservation must fail before a second marker can be created; recovery of the first marker must then clear it without quarantining unrelated/newer bytes.
2. Repair `begin_managed_publication()` as the shared authority: under the same re-entrant cross-runtime project lock, validate pending markers and reject any unresolved marker whose canonical `relative_path` matches the requested path before creating the new marker.
3. Keep the adapter's final in-lock file-existence check; the durable marker reservation closes the crash window where the target is absent.
4. Run focused publication/recovery tests and full Draft CI, then synchronize context/PR body.
5. Refreeze `draft -> review`, mark Ready, and launch another genuinely fresh ordinary-ChatGPT read-only review on the new exact BASE/HEAD.
6. After `CURRENT / PASS / 0 findings`, obtain final exact-head CI/browser/real-media acceptance, verify live identity and unresolved threads, and merge with expected HEAD SHA.
7. After merge, perform D-038 lifecycle closure to `idle` before the next slice.

## Invariants to preserve

A canonical arbitrary publication path has at most one unresolved durable reservation at a time. Reservation validation + marker creation is atomic under the project lock. Recovery of an interrupted marker without materialized bytes must not be able to invalidate a later successful publication.

Generation redo-only retry/recovery, archive authority, source/WebVTT/Generation publication semantics and all previously repaired Stage-19 invariants remain unchanged.

## Out of scope

Do not mix Recipe endpoint retirement, execution-plan retirement, Product Orchestrator redesign/retirement, Stage8 retirement, provider-selection redesign, Production Direction authority changes, Timeline identity redesign or later D-070 compression work into this repair cycle.
