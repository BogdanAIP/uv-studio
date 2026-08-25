# D-069 — Stateful generative continuation uses durable lineage, not provider state

**Status:** Accepted  
**Date:** 2026-08-25

## Context

Sequential video-generation/editing systems such as InfinityEdit demonstrate a useful interaction model: a generated result can become the source for the next text-directed continuation/edit while an adapter uses bounded recent context, anchor frames or cached runtime state to avoid replaying the complete history.

UV Studio already owns Project references, Shot/Take semantics, provider-neutral `GenerationContract`, retry-safe Job/Attempt history and adapter boundaries. Importing a generator's latent/session/cache graph as project truth would duplicate those authorities and make projects dependent on one runtime.

Technology-donor references:

- InfinityEdit project: https://yunzetong.github.io/InfinityEdit/
- InfinityEdit code: https://github.com/YunzeTong/InfinityEdit

InfinityEdit is a donor/candidate adapter, not UV Studio product authority or a required dependency.

## Decision

UV Studio supports **stateful/sequential generative continuation through durable media lineage**.

The canonical chain is:

```text
project media / generated Take reference
 -> GenerationContract.continuation_source_reference_id
 -> normalized generation request + idempotency digest
 -> Job / Attempt
 -> capability offer declaring generation.continuation
 -> provider/adapter execution
 -> new project-owned media + continuation lineage provenance
 -> new Take candidate
```

### Durable state

The Project Store may persist only provider-neutral, reproducible identities needed to explain and restart the operation, including:

- the source project media reference used as the continuation parent;
- named model and selected capability/offer/adapter mapping;
- generation constraints/inputs and normalized request digest;
- Job/Attempt history;
- resulting project media reference and Take candidate;
- explicit parent -> child continuation lineage in provenance.

A continuation request is part of the same idempotency identity as the rest of the `GenerationContract`: changing the parent reference changes the normalized request digest.

### Feature gate

A model/offer must explicitly advertise the capability feature `generation.continuation` before UV Studio accepts `continuation_source_reference_id`.

The system fails closed when a caller requests continuation through an offer that does not declare that feature. This prevents an ordinary generator from silently ignoring continuation semantics.

### Adapter-private execution state

Provider/runtime state is **not canonical project state**. This includes, for example:

- KV/attention caches;
- latent tensors;
- provider session handles/tokens;
- sliding history windows;
- extracted anchor-frame caches;
- model-specific continuation cursors.

An adapter may keep such data transiently as an optimization, but it must be disposable/reconstructible from durable project media and request provenance. Losing that cache may reduce performance; it must not destroy the project history or change its meaning.

### InfinityEdit-derived strategies

The following are useful adapter strategies, not UV-owned persistent contracts:

- bounded/sliding recent-history context;
- anchor-frame reconstruction of continuation context;
- edit-ignition, where a text edit is applied at the transition and the backbone then continues from the changed state;
- reuse of a frozen/base generator behind a lightweight editing adapter.

Different future adapters may implement these strategies differently or not at all.

### No second timeline or generation graph

Continuation lineage explains how candidate media was derived. It does not become a second canonical Timeline, a new Production Direction, or a separate Scene/Shot/Take graph.

Timeline state changes only through the existing explicit Take-acceptance/application-command path.

## Consequences

- Stage 14 reserves the continuation lineage field and feature gate before `GenerationContract` and Job/provenance APIs harden.
- No InfinityEdit/Helios runtime is required by Stage 14.
- A later InfinityEdit or comparable adapter can plug into Model Registry/Capability execution without changing Project Store authority.
- Product UI for `Continue/Edit from here` must not be exposed as ready until a real model/offer advertises `generation.continuation` and Product Truth evidence covers the user outcome.
- Sequential continuation remains retry-safe and inspectable across application restarts even when provider caches disappear.

## Relationship to earlier decisions

- D-009 remains the Project Store authority; D-069 only defines which continuation facts are durable there.
- D-017 remains the execution authorization boundary.
- D-033 remains the canonical editor/Timeline foundation.
- D-065 keeps Shot/Take/accepted-material semantics shared across Production Directions.
- D-066 owns the Job/generation reliability foundation; D-069 specializes the state boundary for sequential generative continuation.
- D-067 requires future continuation UI to have truthful backend/model support and E2E proof before being declared ready.
