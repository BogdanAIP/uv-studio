# UV Semantic API

## Status

This document defines the integration-facing semantic contract of UV Studio.

**UV Semantic API is not a second command system, a new backend, or a new registry.** It is the curated external projection of semantic contracts UV Studio already owns: Project Store/domain state, the UV Command API, Capability Registry/execution, Recipe Registry and execution planning.

The concrete mutation subset remains the **UV Command API** accepted by D-033. Existing product modules remain authoritative; this document gives their safe integration boundary one stable name.

## Purpose

UV Studio needs one product-owned surface that can be used consistently by the GUI, scripts, AI clients, automation and future external bridges without giving those callers direct access to canonical storage or engine internals.

The Semantic API exists to make that boundary explicit:

```text
GUI / scripts / AI / Local Bridge / future MCP server
                         |
                  UV Semantic API
                         |
       +-----------------+------------------+
       |                 |                  |
  Project Store     UV Command API    Capability / Recipe
  bounded views     semantic edits     semantic execution
       |                 |                  |
       +-----------------+------------------+
                         |
                 engines / adapters
```

This follows the existing architecture principle `GUI = scripts = AI = MCP`: integrations reuse product-owned semantics instead of growing independent mutation or execution implementations.

## Existing authorities

The Semantic API does not replace or relocate these components:

- `uv_studio/projects/` remains the canonical Project Store and domain authority;
- `uv_studio/editor/` remains the product-owned semantic editor command implementation;
- `uv_studio/capabilities/` remains the provider-neutral capability, offer, selection, authorization and execution authority;
- `uv_studio/recipes/` remains the provider-neutral recipe/workflow catalog and planning authority;
- `uv_studio/mcp/` remains the adapter boundary for explicitly bound external MCP tools;
- `uv_studio/api/` remains the current local HTTP transport for product-owned API surfaces.

Adding a Semantic API integration MUST reuse these authorities. It MUST NOT create a parallel project store, command registry, capability registry, provider lifecycle or job system.

## Semantic planes

### 1. Observation and planning

External callers may receive bounded product-owned views needed to understand the current project and available operations. The view should expose semantic state and stable identifiers rather than renderer, donor-runtime or filesystem internals.

Current examples include:

- `GET /api/uv/projects/{project_id}/editor/state`;
- `GET /api/uv/projects/{project_id}/execution-plan`;
- `GET /api/uv/capabilities` and capability/offer inspection;
- `GET /api/uv/recipes` and recipe inspection.

A read endpoint is not automatically part of the Semantic API merely because it lives below `/api/uv`.

### 2. Semantic mutation — UV Command API

Meaningful editor mutation goes through one UV-owned command contract.

The current HTTP projection is:

- `POST /api/uv/projects/{project_id}/editor/commands`.

The command implementation remains in `uv_studio/editor/`; callers do not receive an alternate AI-, script-, bridge- or MCP-specific mutation implementation.

When a future external integration needs an edit that is not yet represented semantically, the rule is:

1. add or extend the product-owned editor/domain command;
2. validate it through the existing Project Store and domain invariants;
3. then project that same command through the required transport.

Do not add a transport-specific mutation shortcut first.

### 3. Semantic capability execution

Media/model/runtime work remains provider-neutral and follows the existing Capability Registry and D-017 authorization boundary.

The current project-scoped HTTP flow is:

- `POST /api/uv/projects/{project_id}/capabilities/{capability_id}/prepare-execution`;
- `POST /api/uv/projects/{project_id}/capabilities/{capability_id}/authorize-execution` when explicit consent is required;
- `POST /api/uv/projects/{project_id}/capabilities/{capability_id}/execute`.

Selection, authorization and execution remain separate. A Semantic API caller MUST NOT bypass cost/locality disclosure, one-shot authorization, project-file boundaries or adapter validation.

Discovered MCP tools also remain subject to explicit semantic bindings. Tool discovery metadata is not permission and does not automatically create a UV capability.

### 4. Recipes and higher-level workflows

Recipes may expose higher-level product intent by composing existing semantic capabilities and editor/workflow primitives. They do not create a second universal engine.

The current read-only recipe catalog is:

- `GET /api/uv/recipes`;
- `GET /api/uv/recipes/{recipe_id}`.

Project execution planning is exposed through the existing `execution-plan` endpoint. Future workflow mutations may join the Semantic API only when they are product-owned, bounded and share the same underlying domain implementation used by the product UI.

## Current implementation map

| Semantic concern | Current authority / projection |
| --- | --- |
| Canonical project/domain state | `uv_studio/projects/` |
| Bounded editor/project observation | `GET /api/uv/projects/{project_id}/editor/state` |
| Semantic editor mutation | `uv_studio/editor/` + `POST /api/uv/projects/{project_id}/editor/commands` |
| Capability definitions/offers | `uv_studio/capabilities/` + `/api/uv/capabilities` |
| Capability selection/consent/execution | `uv_studio/capabilities/` + project-scoped prepare/authorize/execute endpoints |
| Provider-neutral recipes | `uv_studio/recipes/` + `/api/uv/recipes` |
| Project execution planning | `GET /api/uv/projects/{project_id}/execution-plan` |
| External MCP tools used by UV | `uv_studio/mcp/` through explicit capability bindings |

This table describes the current mapping. It is **not** a declaration that every current HTTP payload is already a permanently versioned public SDK contract.

## Transport independence

Semantic meaning is owned by UV Studio, not by HTTP, MCP or a particular AI provider.

The current UV-owned server provides local HTTP projections. A future Local Bridge, MCP server or other integration adapter should translate its external protocol to the same product-owned semantic operations rather than reimplementing them.

```text
Local HTTP -------+
                  |
Local Bridge -----+--> same UV-owned semantic operations
                  |
future MCP server +
```

The existing MCP client has a different direction: it lets UV bind approved external MCP tools to semantic capabilities. Documenting the Semantic API does **not** by itself turn UV Studio into an MCP server.

No model vendor, AI harness, provider SDK or local model runtime is part of the Semantic API contract.

## Security and trust boundary

The Semantic API preserves existing security decisions rather than introducing a privileged automation path.

- UV-owned HTTP remains loopback-oriented under D-025 unless a separate remote-access threat model is explicitly accepted.
- A Local Bridge or other remote/tunnel component owns its own external authentication and transport boundary; UV Studio does not become internet-facing merely to support that bridge.
- Remote or non-free capability execution remains behind D-017 authorization.
- Secrets and machine/runtime configuration remain outside canonical project state and are not exposed as semantic project data.
- Project-owned source/artifact identifiers are preferred over arbitrary filesystem paths.
- External callers do not receive arbitrary shell, FFmpeg command-line, MLT XML/state or provider-SDK execution access.

## Explicit exclusions

The following are **not** Semantic API merely because implementation code or HTTP routes exist for them:

- direct mutation of canonical Project Store JSON, generic `settings` or `extensions` as an automation bypass;
- raw MLT state/XML or render-engine internals;
- arbitrary shell commands, raw FFmpeg/filtergraph construction or unrestricted filesystem paths;
- runtime configuration and secret-management endpoints;
- raw provider/model SDK calls;
- unbound tools discovered from an MCP server;
- legacy/donor VideoClaw compatibility endpoints solely because transitional frontend code can still reference them;
- a separate AI command registry or AI-specific project state;
- a new model/harness/runtime manager.

Any transitional compatibility surface must be migrated or retired in its own reviewed slice. It must not be deleted opportunistically while adding Semantic API integrations.

## Evolution rules

1. **Reuse first.** Before adding a new semantic layer, verify that the operation is not already represented by Project Store, Editor Commands, Capabilities or Recipes.
2. **One mutation implementation.** GUI, script, AI, bridge and MCP transports converge on the same product-owned command/workflow implementation.
3. **Curate exposure.** Do not expose all internal `/api/uv` routes as a public automation surface by default.
4. **Add semantics before transport.** Missing product intent is added to the product domain/command/capability layer first; transport adapters come after.
5. **Preserve authorization.** Transport convenience never bypasses D-017 or project/file validation.
6. **Keep adapters replaceable.** Provider/model/runtime identity stays behind semantic capabilities and outside canonical project semantics.
7. **No duplicate ownership.** A new integration may adapt the Semantic API, but may not become a competing Project Store, Command API, Capability Registry or Recipe Registry.
8. **Retire deliberately.** Legacy/donor/compatibility surfaces are removed only through an explicit migration with regression evidence.

## Related architecture

- `ARCHITECTURE_PRINCIPLES.md` — one command model and reuse-first constraints;
- `project-context/decisions/D-033-reuse-first-scriptable-editor-foundation.md` — accepted UV Command API and Project Store ownership;
- `docs/architecture/CAPABILITIES.md` — semantic capability model;
- `docs/architecture/CAPABILITY_EXECUTION.md` — selection, authorization and execution boundary;
- `docs/architecture/RECIPES.md` and `docs/architecture/RECIPE_EXECUTION.md` — provider-neutral workflow composition;
- `docs/architecture/MCP_ADAPTER.md` and D-015/D-018 — external MCP discovery/binding/invocation;
- D-017 — exact execution authorization;
- D-025 — runtime/server security boundary;
- D-042 — composition-first rule against duplicate universal engines.
