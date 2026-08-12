# Stage 4C editor-foundation spike

This spike selects reusable editor foundations by executable evidence rather than product screenshots or upstream roadmaps.

## Question

What is the smallest license-compatible composition that gives UV Studio a professional timeline/editor UX, scriptable editing semantics and real-media render/preview while keeping UV-owned Project Store, safety and AI workflow boundaries?

## Candidate roles

- **libopenshot** — engine candidate. Python bindings, timeline JSON/diff model, preview/render. Evaluate the library independently from GPL OpenShot Qt UI.
- **MLT** — engine candidate. Python bindings and mature playlist/tractor/render model.
- **OpenCut** — UX/component donor candidate. Evaluate pinned implemented timeline/editor code and license; do not treat planned Editor API/MCP/headless work as already available.

A hybrid result is valid and expected if one candidate is best for editor UX and another is best for the engine.

## Capability gate

`candidate-matrix.json` defines the same evidence fields for every candidate. Engine probes must use generated real media and emit machine-readable JSON reports. A missing capability is a result, not a reason to silently weaken the requirements.

The key architectural test is not merely whether an engine can render. It is whether a UV-owned Command API can drive the same edit model as the GUI/script/AI paths without raw project-state mutation.

## Running

The repository workflow `.github/workflows/editor-foundation-spike.yml` installs distribution-packaged bindings on Ubuntu, generates a deterministic FFmpeg fixture, runs the libopenshot and MLT probes, validates their JSON reports, and performs a pinned OpenCut source/license inspection.

The workflow is intentionally separate from the permanent required CI matrix while D-033 is proposed. Its evidence becomes part of D-033 before the decision is accepted.
