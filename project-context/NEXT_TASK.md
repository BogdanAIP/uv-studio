# Next Task

**Primary target:** continue Stage 3 with UV Studio-owned local deterministic capability execution and an explicit selection policy. Do not connect Qwen-MM/OpenClaw or execute potentially-paid offers in this slice.

## Why this comes next

The first Stage 3 slice now provides:

```text
CapabilityDefinition
  -> AdapterDefinition
      -> CapabilityOffer
```

with explicit availability, locality and cost class. The registry can honestly report:

- local/free FFmpeg/FFprobe availability;
- free remote Edge TTS compatibility;
- VideoClaw model paths as `configuration_required / potentially_paid`;
- no offer where a compatible implementation has not been proved.

What is still missing is a safe execution boundary. Implement that first for deterministic local tools where execution is testable without credentials or money.

## Do first

1. Add product-owned capability execution contracts, for example:

```text
CapabilityExecutionRequest
CapabilityExecutionResult
CapabilityExecutionError
```

2. Add an explicit selection policy model:

```text
manual
pinned_offer
local_free_first
```

Do **not** add an automatic paid fallback.

3. Implement offer selection rules:
   - `local_free_first` may choose only `available + free` offers;
   - prefer local over hybrid over remote inside the allowed free set;
   - if no safe offer exists, return explicit unavailable/configuration-required rather than selecting `potentially_paid`;
   - `pinned_offer` executes only the exact requested offer;
   - a potentially-paid/paid pinned offer is still rejected in this slice because external paid execution is out of scope.

4. Implement first local adapters:

### `media.probe`

Use local `ffprobe` through an argv subprocess (no shell string interpolation).

Return structured metadata such as:

- duration;
- streams;
- dimensions/frame rate where available;
- audio/video presence;
- source path/artifact metadata.

Validate file paths and timeouts.

### `timeline.assemble`

Start with a deliberately bounded deterministic operation supported by the pinned baseline, e.g. ordered concat of compatible local clips.

Requirements:

- explicit ordered input file list;
- output stays inside the canonical project's artifact/export area;
- no arbitrary user-supplied FFmpeg flags;
- safe temporary manifest handling;
- clear error on incompatible/failed concat;
- register output as a project artifact rather than returning an orphan file.

If concat requires normalization/transcoding for reliable output, make that behavior explicit rather than silently degrading quality.

5. Add project/domain execution API, not raw command execution. Possible shape:

```text
POST /api/uv/projects/{project_id}/capabilities/media.probe/execute
POST /api/uv/projects/{project_id}/capabilities/timeline.assemble/execute
```

or one typed endpoint if validation remains strict.

6. Persist resulting artifacts/references through Project Store-owned helpers. Do not let API code invent filesystem paths independently.

7. Add tests for:

- `local_free_first` never selecting potentially-paid offers;
- exact pinned selection;
- missing tool behavior;
- subprocess timeout/failure;
- paths outside project/source boundary where applicable;
- successful probe fixture;
- successful small concat fixture when FFmpeg exists;
- no shell injection;
- artifact registration/persistence;
- Windows path behavior.

8. Keep API/frontend baseline green on Windows and Linux.

## Important product rule

The Capability Registry describes what exists. The execution layer executes only what current policy explicitly allows.

Do not turn registry ordering into implicit purchasing behavior.

```text
metadata preference != permission to execute
```

## Qwen-MM / OpenClaw boundary

Still out of scope for this next slice:

- installing Qwen-MM-Plugins;
- requiring WSL2;
- DashScope calls;
- direct MCP process management;
- OpenClaw Gateway/runtime;
- paid provider execution;
- provider OAuth/API-key UI.

Those adapters should plug into the same execution contract after local deterministic execution is proven.

## Suggested files

```text
uv_studio/capabilities/execution.py
uv_studio/capabilities/selection.py
uv_studio/capabilities/adapters/local_ffmpeg.py
uv_studio/api/capability_execution.py

uv_studio/projects/artifacts.py   # only if a dedicated helper is cleaner

tests/test_capability_selection.py
tests/test_local_ffmpeg_adapter.py
tests_api/test_capability_execution_api.py

docs/architecture/CAPABILITY_EXECUTION.md
```

## Acceptance criteria

- local deterministic capability execution works without credentials;
- `local_free_first` can never fall through to potentially-paid/paid;
- no arbitrary shell/FFmpeg command surface is exposed;
- outputs are canonical project artifacts;
- failure does not leave a falsely registered successful artifact;
- Windows/Linux tests remain green;
- vendor tree remains unmodified;
- no Qwen/OpenClaw runtime dependency is added.

After this slice, the next priority is direct MCP adapter infrastructure so Qwen-MM-Plugins can be integrated optionally behind the same semantic contracts without changing recipes or project state.
