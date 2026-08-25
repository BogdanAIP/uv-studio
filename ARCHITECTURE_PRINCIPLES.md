# UV Studio Architecture Principles

These rules are product architecture constraints, not implementation suggestions.

## Production Directions over one Studio Core

D-064 is the current long-term product-composition authority. D-063 remains the accepted shared-Studio-core foundation that D-064 refines.

UV Studio is one professional local-first production/editing application with a shared Studio Core and multiple Production Directions. New product growth may introduce a direction when a user journey has materially different production entities/navigation/policy, but it MUST NOT introduce a separate canonical project engine, recipe execution stack or duplicated editor infrastructure.

The normal composition is:

- one UV-owned Project and Project Store;
- one selected Production Direction for projects that need a domain-specific production model;
- direction-specific project-owned production documents where useful;
- shared Media/Assets, Preview/Canvas, Inspector/AI Tools and canonical multitrack Timeline;
- explicit user-visible model choice where the model materially affects the creative result;
- one application/command authority used by manual UI and automation;
- shared Model Registry, Job Manager, Capability Registry, adapters and export infrastructure.

Initial first-class directions are micro-drama/story, commercial/product, music video, narrated video, dub battle/cinematic revoicing and free project.

Operation-level features such as targeted edit, ordinary dubbing/translation, slideshow, visualizer, action transfer, talking character and lip-sync remain contextual tools unless a later evidence-backed decision proves that one requires a distinct production model.

Recipe/Product-Orchestrator/Stage 8 state remains compatibility/migration material until retired through evidence-backed caller migration. A Production Direction is not a `RecipeDefinition` and does not select an execution engine/provider.

## Reuse-first / orchestration-first

UV Studio MUST prefer a mature, professionally usable, maintained and license-compatible open-source component over a custom implementation of a general media/editor primitive.

Before implementing a new timeline, waveform, media player, compositor, render engine, subtitle engine, tracking/masking primitive, audio-processing primitive, interchange format or similar infrastructure, the active slice MUST:

1. identify credible existing open-source candidates;
2. verify license compatibility and redistribution obligations;
3. test the capabilities that matter to the product instead of relying on README claims;
4. record why the selected component is integrated, or why every credible candidate is rejected.

Custom implementation is justified only for UV-specific orchestration, a missing adapter/integration, a small compatibility layer, or a capability for which the repository records a concrete technical rejection of existing solutions.

A convenient custom implementation is not sufficient justification when a suitable reusable component exists.

### Donors provide parts, not product authority

Open-source reuse is successful only when UV Studio owns the surrounding product contract.

Preferred sequence:

`candidate -> license/evidence spike -> pin -> UV adapter/command boundary -> needed primitive -> tests -> Studio tool/direction service`

Do not copy a donor's application/project/workflow/session model merely because one of its primitives is useful. In particular, donor stages, task taxonomies, provider settings or storage architecture do not become UV Studio product concepts without an explicit architecture decision.

## One command model: GUI = scripts = AI = MCP

Every meaningful non-trivial editor or production mutation MUST have one product-owned programmatic command contract.

The GUI, user scripts, AI actions and MCP automation MUST call the same command model. They MUST NOT maintain independent editing/production implementations or mutate canonical project/timeline/production JSON directly.

The command/application layer owns:

- validation and project/path boundaries;
- deterministic mutation semantics;
- transaction grouping and undo/redo integration;
- provenance needed for automation/review;
- conversion to the selected editor/render-engine adapter;
- canonical UV Studio domain invariants.

A Project Unit of Work MUST be capable of coordinating direction/domain documents, project assets/references, generation records and timeline state atomically when one semantic operation spans them.

An AI assistant may inspect project/direction state and propose commands or higher-level plans, but it does not receive a privileged raw-state mutation bypass.

## Project state is UV-owned; engine state is derived

Project Store and UV-owned versioned domain documents remain canonical.

MLT is the selected timeline/edit engine behind the D-033 adapter. Raw MLT XML/in-memory state is an engine representation and MUST NOT become a second public project authority. OpenCut Classic remains a selective editor-UX donor, not a storage/backend authority.

A second canonical timeline engine requires an explicit superseding decision backed by executable evidence.

## Model visibility and execution abstraction

Capability Registry and adapters abstract execution; they do not hide professional creative choices.

- The relevant Studio AI tool MUST expose the selected named model when model choice materially affects output.
- A future `Auto` policy may select a model on the user's behalf, but explicit model pinning remains supported.
- Settings own provider/runtime/account connection state; the tool owns per-operation model choice and model-specific creative parameters.
- Provider-specific transport details stay behind Model/Capability/Adapter boundaries rather than spreading through frontend feature code.
- Remote/non-free execution remains subject to D-017 authorization.

## Hybrid foundations are allowed

UV Studio does not require one upstream editor to own the entire product. A license-compatible editor UI donor, a separate media/timeline engine, UV Studio Project Store, UV Studio Command API, local tools and cloud/MCP providers may be composed when this reduces custom code and preserves clean ownership boundaries.

Copyleft components may be used only in a manner consistent with their license obligations. Their presence does not silently relicense UV Studio source. License compatibility is an explicit selection gate for every reused component.

## Evidence before adoption

A foundation dependency is selected only after a reproducible spike proves the required operations on representative real media and records deployment/maintenance/licensing risks. Aspirational roadmap items in an upstream project do not count as implemented capability.
