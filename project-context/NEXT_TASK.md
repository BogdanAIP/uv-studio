# Next Task

Updated: 2026-08-11

## Primary target

Implement **explicit binding-owned project-file argument translation for MCP capabilities**.

Generic authorized MCP invocation now exists, but it deliberately rejects raw host paths and does not convert `sources/...`, `assets/...` or other project-relative strings into host filesystem paths. The next slice must add that capability without creating a generic arbitrary-path escape hatch.

## Required implementation

### 1. Versioned binding file-input contract

Extend `MCPToolBinding` with an explicit, backward-compatible project-file argument contract.

The contract must identify exactly which MCP argument fields are project file references and which canonical Project Store roots are allowed for each field. Bindings with no such declaration continue to treat arguments as ordinary JSON data and must not receive resolved host paths.

Prefer a small product-owned model over provider-specific special cases. Do not infer file arguments from names such as `path`, `image`, `video` or `file`.

### 2. Project Store resolution only

For every declared project-file argument:

- accept a project-relative reference only;
- resolve it through `ProjectStore.resolve_project_file(...)`;
- constrain resolution to the binding-declared allowed roots;
- require the referenced file to exist when the tool contract requires an input file;
- reject traversal, absolute paths, UNC paths and `file://` values;
- never expose arbitrary host paths supplied by the API caller.

Resolved host paths may exist only in the short-lived adapter invocation payload. They must not be written back into canonical project metadata or provenance.

### 3. Digest semantics

Keep D-017 authorization bound to the user-facing normalized input, not to machine-specific resolved absolute paths.

The provenance `input_digest` must therefore remain stable when the same project is moved to another machine/root. Do not recompute authorization or provenance digests from translated host paths.

### 4. Exact binding drift protection

Include the new file-input contract in the existing MCP configuration digest. Any change to declared file fields or allowed roots must require reconnect before execution.

No fuzzy migration or automatic widening of allowed roots.

### 5. Fake MCP fixture first

Add a deterministic fake MCP tool/binding that accepts one declared project file argument and returns safe metadata about the received path/content.

Tests must prove the translation works without depending on Qwen, WSL, network access or paid APIs.

### 6. Qwen core follow-up only after fresh verification

After the generic contract is green, re-check the pinned/current Qwen-MM core tool schema before binding any real project-file field. If the pinned `media_info` contract still maps cleanly, enable only the exact required project-file argument for the existing `core.media_info -> media.probe` trusted binding.

Do not broaden other Qwen tools in the same slice unless their file contracts are independently verified and covered by tests.

## Acceptance criteria

The slice is complete only when tests prove:

1. Existing MCP bindings with no file contract behave exactly as before.
2. Raw POSIX/Windows/UNC/file-URI host paths remain rejected.
3. Declared project-relative file input resolves successfully through Project Store.
4. Undeclared argument fields never receive path translation.
5. `..` traversal and wrong-root references fail closed.
6. Missing required project input fails before MCP process invocation.
7. Authorization digest is computed from portable user input, not resolved host paths.
8. Provenance contains the portable input digest and no resolved host path.
9. Changing file-input contract invalidates the READY configuration digest and requires reconnect.
10. Project archive contains no machine-specific resolved paths.
11. Fake MCP integration passes on Linux and Windows.
12. If Qwen core mapping is enabled, no DashScope/network/paid call is made in CI.

## Expected files

Likely changes:

- `uv_studio/mcp/models.py`
- `uv_studio/mcp/manager.py`
- `uv_studio/capabilities/adapters/mcp_execution.py`
- `uv_studio/projects/store.py` only if a small additional safe resolver primitive is genuinely required
- fake MCP fixture and MCP execution tests
- optional trusted Qwen pack binding update after upstream verification
- `project-context/PROJECT_STATE.md`
- this file
- architecture decision record if the file-input contract becomes durable

## Explicit non-goals

- No generic host filesystem access.
- No automatic inference of file arguments from tool schemas or field names.
- No arbitrary command execution.
- No paid Qwen/DashScope call in tests or CI.
- No OpenClaw work in this slice.
- No Stage 4 workflow expansion until Stage 3 external execution boundaries remain green on Linux and Windows.
