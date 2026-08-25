# Stage 14 implementation notes

This slice implements `studio-v2-model-registry-job-manager-generation` from the idle main handoff.

The implementation must preserve D-064/D-065 production semantics, D-017 authorization and Stage-12 ProjectUnitOfWork authority. D-066 contributes idempotency/GenerationContract/effects/provenance patterns; D-067 requires backend/frontend/E2E Product Truth parity. D-068 desktop updater work is explicitly out of scope.

The first vertical must prove same-key replay deduplication, same-key/different-digest conflict and fresh-key intentional creative reroll.

D-069 adds one bounded seam learned from sequential-generation systems such as InfinityEdit before the Stage-14 contracts harden:

- `GenerationContract.continuation_source_reference_id` is a provider-neutral parent project-media identity for edit/continuation lineage;
- an offer must advertise `generation.continuation` or the service rejects that contract fail-closed;
- the continuation parent is part of the normalized request and therefore the idempotency digest;
- generated artifact provenance records explicit parent -> child continuation lineage;
- provider/runtime KV caches, latent state, sessions, sliding windows and anchor caches stay behind the adapter and never become Project Store truth;
- InfinityEdit/Helios integration, continuation UI and a real continuation model remain later adapter/product work and must satisfy D-067 before being exposed as ready.
