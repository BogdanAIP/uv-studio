# UV Studio Direct MCP Adapter

**Status:** CURRENT SUPPORTING TECHNICAL CONTRACT  
**Product authority:** `CURRENT_ARCHITECTURE.md` / D-064

## Purpose

MCP is an optional source of tools/models/capabilities. It is not a project model, Production Direction, mandatory runtime or privileged Agent path.

```text
Studio Tool / Application Command
  -> Model/Capability selection
  -> explicit MCPToolBinding when MCP backs the operation
  -> D-017 authorization when required
  -> bounded MCP invocation
  -> project-owned result/provenance
```

## Machine configuration, not project state

MCP profiles live in machine configuration (`UV_STUDIO_CONFIG_DIR` / `data/config`), outside `project.json` and `.uvproj.zip`. Profiles store command/argv and environment-variable **references**, never raw secret values as portable project fields.

There is intentionally no generic public endpoint that lets an arbitrary browser caller create an unrestricted local command profile. Machine process configuration remains a privileged local setting.

## Discovery and binding

Discovery uses the official MCP Python SDK and bounded configured transports. Tool catalogs are normalized under size/count limits. Discovered tool names do not become UV semantics automatically.

Only an explicit `MCPToolBinding` maps a provider/package-specific tool to a UV semantic `capability_id` and declares locality/cost/feature facts. Unbound tools never become executable semantic offers by inference.

## Execution

MCP execution is implemented through the UV capability execution boundary. Invocation is bound to the configured profile/tool/binding and bounded project-file translation. Remote/non-free MCP offers use D-017 exactly like other adapters.

Portable provenance records semantic/tool identity and bounded result facts without persisting reusable authorization tokens, secrets or resolved host-only paths.

## Cost/locality

Package license does not determine operation cost. One open-source MCP server may expose both local/free and remote/potentially-paid tools; those are separate offers with separate policy/authorization behavior.

`local_free_first` never widens to a remote or paid-capable MCP offer.

## Qwen-MM / OpenClaw boundary

Qwen-MM-Plugins and OpenClaw remain optional adapters/packages, not required layers. Qwen cloud operations must remain explicitly configured and classified; OpenClaw is not a mandatory hop for direct MCP.

The pinned Qwen evaluation in `QWEN_MM_PLUGINS_EVALUATION.md` is historical component evidence and must not restore recipe-first product composition.

## D-064 invariants

1. MCP does not define Production Direction identity or domain state.
2. MCP/Agent cannot mutate canonical project files directly outside the same application/domain command authority used by GUI/scripts.
3. User-significant model choice remains visible in the Studio tool even when execution uses MCP.
4. Project Unit of Work must own future multi-document acceptance/materialization; MCP success alone is not permission to partially mutate project state.
5. No hidden remote/non-free fallback.
