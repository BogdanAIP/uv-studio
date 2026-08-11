# D-019 — MCP project files are binding-owned portable references

Status: accepted  
Date: 2026-08-11

## Decision

MCP bindings may receive files from a UV Studio project only through an explicit, versioned `MCPProjectFileInput` contract owned by that exact `MCPToolBinding`.

Version 1 declares one top-level argument name plus the canonical project roots from which that argument may resolve:

```text
argument_name
allowed_roots
required
```

The generic roots that a binding may expose are deliberately limited to media/product data:

```text
sources
assets
artifacts
exports
```

Internal project history/control roots are not exposable through this contract:

```text
tasks
timeline
reviews
```

UV Studio never infers file semantics from names such as `path`, `file`, `image` or `video`, and never infers them from an MCP tool schema. A binding with no `project_file_inputs` receives ordinary JSON only.

## Resolution order

For an exact READY binding:

1. the API request remains portable project-relative JSON;
2. D-017 authorization and provenance input digest are computed from that portable input;
3. caller-supplied absolute POSIX paths, Windows drive paths, UNC paths and `file://` URIs are rejected;
4. only fields explicitly declared by the binding are resolved through `ProjectStore.resolve_project_file(...)` with `must_exist=True` and the binding's exact `allowed_roots`;
5. the resolved value must be a file;
6. the absolute machine path exists only in the short-lived MCP invocation dictionary;
7. provenance and project archives keep only the original portable digest, never the resolved machine path.

Any change to `project_file_inputs` is part of the existing profile/binding configuration digest and therefore requires a new MCP discovery/READY snapshot before execution.

## Qwen core application

The pinned UV Studio Qwen-MM reference remains:

```text
QwenLM/Qwen-MM-Plugins@7dfc08b7de8e621fc28bf9814e3d41a59b4595ae
```

On 2026-08-11 the pinned `media_info` implementation was re-verified against the current upstream source. Both use the same implementation blob and the same contract:

```text
media_info(path: str, raw: bool = False)
```

where `path` is documented as an absolute path to an image or video.

Therefore only the already trusted local/free binding

```text
qwen-mm-core.media-info -> media.probe
```

receives an explicit `path` project-file contract in this slice. It may resolve from `sources`, `assets`, `artifacts` or `exports`.

No Qwen cloud/API/video-edit binding receives an inferred file contract. Those schemas must be independently verified before any future expansion.

## Qwen execution catalog correction

D-018 made exact MCP tool invocation available generically, so the older Qwen catalog field `tool_execution_enabled: false` became factually stale. The catalog now reports execution support as conditional generic MCP execution:

- never automatic;
- requires successful exact READY discovery;
- still passes D-017 authorization for remote/non-free offers;
- does not imply Qwen, DashScope or WSL is part of the baseline.

## Reason

External MCP tools often need real filesystem paths, while UV Studio projects must remain portable and must not expose arbitrary host filesystem access. A binding-owned translation contract is the narrowest boundary that satisfies both requirements.

It also prevents machine-specific absolute paths from contaminating authorization grants, run history or `.uvproj.zip` archives.

## Consequences

- old bindings remain backward-compatible with an empty file-input contract;
- undeclared fields are never translated;
- wrong-root, missing, traversal and raw host-path inputs fail before MCP spawn;
- changing a file contract invalidates the READY execution snapshot;
- Qwen core `media_info` can now receive a real project media file through the generic MCP executor after trusted configuration/discovery;
- cloud Qwen execution remains optional, potentially paid and consent-gated;
- future nested/list/multi-file argument semantics require a new explicit contract version rather than hidden heuristics.
