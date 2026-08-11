# UV Studio Capability Execution

## Purpose

The Capability Registry answers **what implementations exist**. The execution layer answers **which implementation is allowed to run now**.

These are deliberately separate decisions:

```text
Recipe / ExecutionPlan
  -> semantic capability_id
      -> Capability Registry
          -> offers
              -> Selection Policy
                  -> Execution Adapter
```

Registry ordering is never permission to spend money or invoke a remote service.

## Selection policies

### `manual`

No automatic selection occurs. The API returns the known offers and requires an explicit later choice.

### `pinned_offer`

Select exactly one named available offer. The selector itself does not reinterpret the choice.

The current Stage 3 execution API still permits only `free + local + local_ffmpeg` execution. Therefore a pinned remote, potentially-paid or paid offer remains known metadata and is rejected before execution.

### `local_free_first`

This policy is intentionally strict.

It selects only offers satisfying all three conditions:

```text
availability = available
cost_class   = free
locality     = local
```

It does **not** widen to:

- remote free services;
- hybrid services;
- `potentially_paid` offers;
- `paid` offers.

If no eligible offer exists, execution stops explicitly.

## Project-scoped filesystem boundary

Local media execution never accepts an unrestricted OS path.

All media paths are canonical project-relative paths such as:

```text
sources/input.mp4
assets/reference.png
artifacts/assembled.mp4
exports/final.mp4
```

`ProjectStore.resolve_project_file()` enforces:

- no absolute paths;
- no `..` traversal;
- Windows backslashes are normalized to canonical project paths;
- operation-specific allowed top-level project roots;
- existing parent directory for writes;
- resolved path must remain under the canonical project directory;
- symlink parents cannot escape the project.

The API never exposes `project.json` or arbitrary host filesystem writes as capability inputs.

## Local FFmpeg adapter

The first executable adapter is `local_ffmpeg`.

It deliberately exposes a very small semantic surface instead of raw FFmpeg commands.

### `media.probe`

Input:

```json
{
  "path": "sources/input.mp4"
}
```

Execution:

- resolve the path through Project Store;
- execute local `ffprobe` using argv with `shell=false`;
- fixed arguments only;
- timeout enforced;
- parse JSON output.

Returned metadata includes:

- duration;
- format;
- byte size where available;
- audio/video presence;
- primary video codec, dimensions and average frame rate;
- stream metadata.

No project artifact is created because probing is an inspection operation.

### `timeline.assemble`

Input:

```json
{
  "input_paths": [
    "sources/a.mp4",
    "sources/b.mp4"
  ],
  "output_path": "artifacts/joined.mp4"
}
```

Current bounded behavior:

- ordered concat only;
- maximum 200 inputs;
- all inputs must already be project files;
- output only under `artifacts/` or `exports/`;
- existing output is never overwritten;
- no arbitrary FFmpeg flags;
- temporary concat manifest lives under the project's `tasks/` directory;
- FFmpeg is invoked through argv with `shell=false`;
- current mode uses stream copy (`-c copy`), so incompatible clips fail explicitly instead of being silently transcoded;
- temporary manifest is always removed;
- output is registered as a canonical `ProjectReference` only after FFmpeg succeeds;
- if project metadata registration fails, the newly created output is removed.

Artifact metadata records:

```text
capability_id
offer_id
input_paths
assembly_mode = concat_copy
```

## API

```text
POST /api/uv/projects/{project_id}/capabilities/{capability_id}/execute
```

Request envelope:

```json
{
  "selection_policy": "local_free_first",
  "offer_id": null,
  "input": {}
}
```

Allowed top-level request fields are exactly:

```text
selection_policy
offer_id
input
```

This prevents the endpoint from becoming a hidden raw command surface.

Successful response contains both the selection decision and execution result, so provenance is visible:

```text
selection.policy
selection.offer
result.capability_id
result.offer_id
result.adapter_id
result.output
result.artifact
```

## Error classes

The adapter normalizes errors into capability-domain failures:

- invalid input/path -> HTTP 422;
- manual/no eligible offer -> HTTP 409;
- known but not-yet-executable adapter/cost class -> HTTP 409;
- local tool missing -> HTTP 503;
- FFmpeg/FFprobe timeout or command failure -> HTTP 502;
- unknown capability/project -> HTTP 404.

Internal Project Store validation exceptions are not exposed as an uncontrolled execution surface.

## Security invariants

1. No shell command string is constructed from user input.
2. `shell=false` is explicit for subprocess execution.
3. No arbitrary FFmpeg options are accepted.
4. Local execution is restricted to canonical project paths.
5. Symlink escape is rejected.
6. `local_free_first` cannot fall through to paid-capable offers.
7. Pinned paid/remote offers remain non-executable in this slice.
8. Registry metadata is not execution permission.
9. Failed media generation does not create a successful artifact record.
10. Vendor VideoClaw code remains unchanged.

## What is intentionally not implemented yet

- remote provider execution;
- direct MCP process/client execution;
- Qwen-MM-Plugins runtime installation;
- DashScope calls;
- OpenClaw Gateway/runtime;
- OAuth/API-key flows;
- automatic paid fallback;
- live price selection;
- arbitrary FFmpeg command execution;
- implicit normalization/transcoding of incompatible concat inputs.

## Next architecture step

After this local execution boundary is green on Linux and Windows, add direct MCP adapter infrastructure behind the same contracts.

Qwen-MM-Plugins can then be an optional MCP capability package without changing recipes, Project Store semantics or the local-free safety rules.
