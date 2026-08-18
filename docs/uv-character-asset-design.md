# UV Character Asset — image/video identity continuity design

Status: future capability design; explicitly out of the active Stage 9 release-hardening scope.

This document preserves the architecture direction for persistent, portable character identity across image and video generation. It is inspired by the useful separation demonstrated by Inline Studio's `.char` container and FLUX.2 multi-reference workflow, but UV Studio must implement the design independently. Inline Studio is GPL-3.0; this document is an architectural note, not permission to copy its implementation.

## Goal

Introduce a provider-neutral **UV Character Asset**: one canonical character identity package that can be reused across projects, shots, image generators and video generators without requiring a trained LoRA for every character or binding canonical project state to one model family.

Working portable extension: `.uvcharacter`.

The key invariant is:

> Source references and human-authored character description are identity truth. Model-specific conditioning payloads, embeddings, crops, scores and other derived representations are caches that must be reproducible and replaceable.

This follows the existing UV Studio architecture: Project Store stays canonical, providers remain adapters/runtime concerns, and generated/derived state never silently becomes project truth.

## Why this exists

A reusable character should not be equivalent to a FLUX payload, LoRA, face embedding or provider ID. Those are different ways to condition or evaluate one underlying identity.

A character asset should therefore support all of these without changing its identity contract:

- native multi-reference image conditioning;
- native reference-conditioned video generation;
- optional LoRA/adapters when a model benefits from training;
- local identity scoring and candidate ranking;
- continuity checks across frames, shots and regenerated takes;
- future image/video providers that do not exist when the asset is created.

## Canonical data versus derived data

### Canonical identity truth

The canonical portion must remain small, inspectable and provider-independent:

- stable character UUID;
- display name;
- human-authored description;
- immutable image reference assets and hashes;
- reference roles/tags, for example front face, profile, full body, outfit, distinctive accessory, hairstyle, age appearance;
- optional negative/avoid notes where the user explicitly defines what must not drift;
- provenance and user ownership/import metadata;
- format version and migration information.

References are not embeddings. If every derived cache is deleted, UV Studio must still be able to reconstruct all supported conditioning/evaluation payloads from canonical references.

### Optional canonical video-oriented references

Video support must be designed in from the first format version even if the first implementation uses still images only.

The format must be able to reference or embed optional short source clips/keyframe sets with explicit roles such as:

- motion mannerism;
- walking/body movement;
- head turns/profile transition;
- speaking performance;
- pose/action reference;
- wardrobe-in-motion;
- characteristic gesture.

These are not automatically part of facial identity. Identity, motion, pose, outfit, voice and style must remain separately addressable semantics so a model adapter can request only what it needs.

Large video references should not make every `.uvcharacter` huge by accident. The portable format should support both:

1. embedded bounded keyframes/short normalized references for portability;
2. project/library asset references with content hashes for large source clips.

A future export command may choose a fully self-contained portable package when requested.

## Derived/cache surface

Derived data belongs in namespaced, versioned sections and may be deleted/rebuilt safely:

- detected face crops;
- face landmarks;
- SFace or equivalent face embeddings;
- DINOv2 or equivalent whole-subject embeddings;
- reference-agreement statistics;
- model-specific normalized reference images;
- model-specific conditioning metadata;
- optional trained adapter/LoRA coordinates or artifacts;
- sampled video-frame identity measurements;
- temporal continuity summaries.

Every derived entry must record at least:

- producer/encoder/adapter identity;
- producer version;
- source-reference fingerprint;
- transformation policy/version;
- content hash where materialized;
- rebuildability flag.

A stale encoder version or changed source fingerprint invalidates the cache instead of silently reusing incompatible vectors.

## Suggested package shape

```text
Character.uvcharacter
├── manifest.json
├── identity/
│   └── description.md
├── refs/
│   ├── images/
│   │   ├── 000.*
│   │   ├── 001.*
│   │   └── ...
│   └── video/
│       ├── keyframes/...          # optional portable subset
│       └── references.json        # optional external hashed assets
├── derived/
│   ├── faces/
│   ├── scoring/
│   └── continuity/
└── payloads/
    ├── image/<adapter-family>/...
    └── video/<adapter-family>/...
```

The exact archive/file format requires its own future architecture decision before implementation. The important boundary is canonical versus rebuildable state, not these directory names.

## Semantic capabilities

Character support should enter UV Studio through semantic capabilities rather than provider-specific commands.

Candidate capabilities:

- `character.create`
- `character.import`
- `character.export`
- `character.references.add`
- `character.references.validate`
- `character.conditioning.compile`
- `character.identity.evaluate`
- `character.continuity.evaluate`
- `character.generate.image`
- `character.generate.video`

Provider adapters may map these to FLUX.2, future image models, video models, LoRA-based workflows or hosted services. Provider/model IDs remain runtime/adaptor data, never canonical character semantics.

## Image generation path

The first useful path can be native multi-reference generation without training:

```text
UV Character Asset
    -> image conditioning adapter
    -> N candidate images
    -> local identity evaluator
    -> ranked candidates + component scores
    -> user review
    -> accepted take/artifact
```

For a FLUX.2 adapter, the adapter may compile reference images into the model's native multi-reference input. The character asset itself must not become a `flux2` object.

Optional LoRA training remains a separate adapter/payload strategy. A trained LoRA may improve a model-specific workflow, but it is not identity truth and must be replaceable.

## Identity evaluation

Embeddings are evaluators, not generators.

A practical first local evaluator can combine independent signals such as:

- face identity similarity (for example SFace-class encoder);
- whole-subject similarity (for example DINOv2-class encoder);
- optional outfit/accessory/color checks;
- description agreement;
- face-detection confidence and reference-quality warnings.

Do not collapse everything into one opaque number internally. Store component scores and an optional policy-weighted aggregate so ranking remains explainable.

Example:

```text
candidate A
face       94
subject    82
outfit     88
aggregate  90

candidate B
face       61
subject    91
outfit     90
aggregate  69
```

UV Studio may rank or flag candidates but should preserve human acceptance as the authority for creative output unless the user explicitly enables an automatic policy.

## Reference-set quality

The system should detect weak or contradictory reference sets before expensive generation:

- no usable face when a face-bearing character is expected;
- accidental different-person reference;
- all references from one nearly identical angle;
- insufficient body/outfit evidence for tasks that require it;
- contradictory age/hair/accessory references;
- low-resolution or occluded references.

Warnings should improve the asset rather than make character creation impossible by default.

## Video generation must be first-class

Video cannot be treated as repeated independent image generation. The Character Asset design must support temporal and shot-level identity continuity from the beginning.

### Video conditioning

A video adapter may compile any supported combination of:

- canonical still identity references;
- selected character keyframes;
- optional motion/pose clips;
- accepted prior-shot frames;
- wardrobe/state references for the current scene;
- provider-specific reference payloads.

Accepted prior outputs are contextual continuity evidence, not a replacement for the canonical Character Asset.

### Video identity evaluation

`character.continuity.evaluate` should sample a bounded set of frames rather than require scoring every frame for every draft.

At minimum report:

- face identity score over sampled visible-face frames;
- subject/body consistency over sampled frames;
- intra-shot identity drift;
- first/middle/last-frame agreement;
- shot-to-shot agreement with the accepted character state;
- missing/occluded-face coverage so a high score is not inferred from too little evidence.

Later evaluators may add hair, wardrobe, accessories, age appearance, body proportions and semantic description checks.

### Temporal drift

A useful video result is not one where the first frame matches and the face mutates later. UV should distinguish:

- absolute match to canonical references;
- variance/drift within the generated clip;
- discontinuity relative to the previous accepted shot.

This allows policies such as:

```text
canonical identity: 91
intra-shot drift:   low
previous-shot match: 89
coverage:            72% visible face
```

rather than a misleading single score.

### Character state versus identity

The same person can legitimately change outfit, hairstyle, makeup, injury state or age across a story. These must not overwrite the base identity.

Future projects should support a scoped **character appearance/state overlay** attached to a scene/shot/sequence, for example:

```text
base character identity
    + scene appearance state
    + shot pose/motion intent
    -> provider conditioning
```

This is important for both image and video pipelines and prevents outfit continuity from being confused with facial identity.

## Candidate ranking and regeneration

The intended orchestration is:

```text
Character Asset
    -> generation adapter
    -> candidates/takes
    -> identity + continuity evaluators
    -> ranking / drift flags
    -> user review
    -> accepted take
    -> optional context for next shot
```

This fits UV Studio's accepted-state/revision model and should not create a second authority outside Project Store.

A future automatic regeneration policy can request another candidate when a bounded identity threshold fails, but it must be explicit, cancellable and budget-aware for paid/remote providers.

## Voice and performance boundary

Do not mix voice identity into the first visual-character score. Voice may later be attached as another character facet with its own references/embeddings/consent/provenance rules. The Character Asset should reserve extensibility for it, but visual identity, voice identity and motion style remain independently addressable.

## Portability and size

A `.uvcharacter` should normally remain far smaller than model weights or trained adapters, but no fixed "few MB" promise should be made. Size depends on number/format of embedded references and whether video keyframes or clips are included.

Portable export should prefer bounded normalized references plus hashes/provenance. Full-resolution originals can remain project/library assets unless the user requests a self-contained export.

## Security, privacy and provenance

Character assets can contain biometric-like face representations and personal images. Implementation must therefore include:

- explicit user-controlled import/export;
- no silent cloud upload of references or embeddings;
- capability authorization before remote provider use;
- provenance for every reference and generated/derived payload;
- safe archive path validation and bounded extraction;
- no executable content in the character container;
- clear deletion/rebuild behavior for embeddings and model-specific caches.

## Relationship to Inline Studio

Useful architectural observations from Inline Studio to preserve conceptually:

- a character is portable rather than tied to one project;
- source references and text are truth;
- per-model payloads are caches;
- face and whole-subject embeddings are useful for scoring rather than as the sole generator identity;
- multi-reference conditioning can avoid mandatory per-character training when the model supports it.

UV Studio should not import Inline Studio's GPL implementation into the MIT codebase. Reimplement the concept from first principles behind UV-owned semantic capabilities and Project Store invariants.

## Implementation ordering after Stage 9

This is intentionally deferred until Stage 9 is merged and the repository returns to green idle.

Recommended future slices:

1. **Character Asset format + Project Store integration** — canonical references, description, hashing, migration, portable import/export, cache invalidation.
2. **Local identity evaluator** — face + whole-subject scoring, reference agreement, explainable component scores.
3. **Image multi-reference adapter** — first provider/model adapter, likely FLUX.2-class native multi-ref, with candidate ranking and accepted-take flow.
4. **Video character conditioning contract** — provider-neutral still/keyframe/motion-reference inputs and shot appearance state.
5. **Video continuity evaluator** — sampled-frame identity, intra-shot drift and previous-shot consistency.
6. **Optional trained adapters** — LoRA or future identity representations as replaceable model-specific payloads, never canonical truth.
7. **Cross-project character library** — reusable user-owned character assets with versioning and provenance.

Each slice should keep local/free evaluation available where practical and keep paid/remote execution optional under the existing UV capability/authorization rules.

## Non-goals

- replacing Project Store with a node graph;
- making FLUX.2 or any current video model mandatory;
- making embeddings the canonical identity representation;
- requiring LoRA training for every character;
- automatically accepting generated output solely because a score passes;
- copying Inline Studio implementation code;
- starting this feature inside the Stage 9 release-hardening PR as product code.

## Reminder

This document is a preserved post-Stage-9 direction. When implementation starts, first validate current image/video model capabilities and licensing, then create an explicit architecture decision for the concrete `.uvcharacter` format and semantic capability contracts before writing provider adapters.
