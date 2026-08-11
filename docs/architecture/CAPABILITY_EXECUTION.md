# UV Studio Capability Execution

## Purpose

The Capability Registry answers **what implementations exist**. The execution layer answers **which exact implementation is allowed to run now**.

These remain separate decisions:

```text
Recipe / ExecutionPlan
  -> semantic capability_id
  -> Capability Registry
  -> CapabilityOffer
  -> SelectionPolicy
  -> ExecutionPreparation
  -> one-shot authorization when required
  -> exact execution adapter
```

Registry ordering, installed dependencies and open-source licenses are never execution permission.

## Selection policies

### `manual`

No automatic selection occurs. Known offers are returned for an explicit later choice.

### `pinned_offer`

Select exactly one named `available` offer. Pinning an offer does not bypass its locality/cost authorization requirements.

### `local_free_first`

Select only offers satisfying all of:

```text
availability = available
cost_class   = free
locality     = local
```

It never widens to remote/free, hybrid, `potentially_paid` or `paid` offers. If no eligible offer exists, execution stops explicitly.

## D-017 execution authorization

Selection is separate from permission to contact an external service or incur cost.

Consent scopes are derived from the selected offer:

```text
remote_execution  -> locality is remote or hybrid
external_cost     -> cost class is potentially_paid or paid
unknown_cost      -> current external price estimate is unknown
```

A free remote service therefore still requires `remote_execution`.

Authorization grants are:

- process-local;
- short-lived;
- one-shot;
- bound to exact project, capability, offer, selection policy and normalized input digest;
- consumed/fail-closed on replay or mismatch;
- never persisted to the project/archive.

API boundary:

```text
POST /api/uv/projects/{project_id}/capabilities/{capability_id}/prepare-execution
POST /api/uv/projects/{project_id}/capabilities/{capability_id}/authorize-execution
POST /api/uv/projects/{project_id}/capabilities/{capability_id}/execute
```

Local/free execution remains token-free.

## Project-scoped filesystem boundary

Capability inputs use canonical project-relative paths, never unrestricted OS paths:

```text
sources/input.mp4
assets/reference.png
artifacts/output.mp4
exports/final.mp4
```

`ProjectStore.resolve_project_file()` enforces:

- no absolute path input;
- no parent traversal;
- canonical path normalization;
- operation-specific top-level allowed roots;
- existing parent directory for writes;
- resolved parent/target containment inside the canonical project;
- when `allowed_roots` is supplied, resolved symlinks must also remain inside those roots;
- allowed canonical roots themselves cannot be symlinks for an allowlisted operation.

The last rule prevents a path written as `sources/alias` from resolving through a symlink into a disallowed internal root such as `tasks/`.

## Local FFmpeg adapter

`local_ffmpeg` exposes semantic operations rather than raw commands.

Current executable operations:

```text
media.probe
  -> local_ffmpeg.media_probe

timeline.assemble
  -> local_ffmpeg.timeline_assemble
```

### `media.probe`

Input:

```json
{"path":"sources/input.mp4"}
```

The adapter resolves the project path, runs bounded `ffprobe` via argv with `shell=false`, parses structured JSON and creates no artifact.

### `timeline.assemble`

Current mode performs ordered concat with a bounded number of project inputs and UV Studio-controlled project output. Raw FFmpeg flags are not accepted. Temporary manifests live under project `tasks/` and are removed. Output is registered only after successful FFmpeg completion; failed project registration removes the just-created output.

The current concat-copy mode fails explicitly for incompatible streams rather than silently transcoding.

## Exact MCP execution

Direct MCP execution uses the official MCP Python SDK v2 and an exact configured `MCPToolBinding`.

A selected MCP offer executes only when:

- the exact configured binding still exists;
- semantic capability identity still matches;
- the profile is enabled and READY;
- the bound tool exists exactly once in the READY discovery snapshot;
- current profile + binding configuration digest matches the discovery digest;
- D-017 authorization has been consumed when required.

Each call uses a bounded short-lived stdio process/session. No fuzzy tool remapping occurs after configuration drift.

### Explicit project-file translation

Generic MCP execution does not infer filesystem access from argument names or tool schemas.

A binding must declare an `MCPProjectFileInput` for the exact top-level argument. The contract contains:

```text
argument_name
allowed_roots
required
```

Generic MCP file contracts may expose only:

```text
sources
assets
artifacts
exports
```

Internal `tasks`, `timeline` and `reviews` are not generic input roots.

Authorization/provenance hash the original portable request. A resolved absolute path exists only in the short-lived invocation dictionary and is never written into portable history.

## Native VideoClaw compatibility execution

Native compatibility is not a generic bridge into vendored Python code.

The execution API currently routes exactly one native offer:

```text
native_videoclaw.edge_tts -> speech.synthesize
```

The product-owned `NativeVideoClawAdapter` accepts only that exact offer/capability pair.

Semantic request contract:

```text
text   required non-empty string, <= 20,000 chars
voice  optional non-empty string, <= 128 chars
speed  optional positive finite number
```

Default voice and speed-to-rate behavior match the pinned VideoClaw TTS contract. The adapter invokes `edge_tts.Communicate` directly; it does not import an arbitrary vendored module/function selected by a caller.

The offer remains:

```text
locality   = remote
cost_class = free
```

so D-017 requires one-shot `remote_execution` consent but no external-cost acknowledgement.

Callers do not choose the output path. UV Studio allocates:

```text
artifacts/art_<uuid>.mp3
```

and registers a canonical audio artifact after successful synthesis.

Other current `native_videoclaw.*` model offers remain configuration-required/non-executable until exact provider/model/credential contracts exist.

## External execution provenance

External MCP and native execution share `ExternalRunProvenance`.

A running record is written before the external operation and finalized to success/failure under:

```text
tasks/run_<uuid>.json
```

Persisted facts include:

- schema/run/project/capability/offer/adapter identity;
- stable concrete target identity;
- timestamps/status;
- authorization-required fact and semantic consent scopes;
- cost-class/estimate snapshot;
- portable normalized input digest;
- success result byte-count + SHA-256 summary;
- controlled failure exception class/code.

Not persisted:

- authorization tokens;
- resolved environment secret values;
- speech text as provenance content;
- host-only resolved project paths;
- raw stderr;
- raw remote/provider error text.

Provenance schema v1 retains historical serialized `profile_id` and `tool_name` fields for compatibility. The in-memory target contract is now transport-neutral: MCP maps profile/tool; native Edge TTS maps `native_videoclaw/edge_tts`. Any future serialized rename requires a schema migration.

## Error classes

Capability-domain failures expose stable machine codes while the API maps them to bounded HTTP classes:

- invalid semantic input/path -> HTTP 422;
- selection/manual/no eligible offer -> HTTP 409;
- selected but unsupported adapter/offer -> HTTP 409;
- local/optional tool unavailable -> HTTP 503;
- external/local tool operation failure -> HTTP 502;
- MCP timeout -> HTTP 504;
- unknown capability/project -> HTTP 404.

Provider exception text is not used as durable provenance.

## Security invariants

1. Registry metadata is not execution permission.
2. `local_free_first` cannot fall through to remote or paid-capable offers.
3. External consent is product-owned and transport-independent.
4. One-shot authorization is exact-input-bound and not portable state.
5. No generic capability accepts raw shell/FFmpeg commands.
6. Project file access is operation/binding-owned and root-bounded.
7. Resolved symlinks cannot cross an explicit allowed-root boundary.
8. MCP invocation is exact-binding/READY-digest-bound.
9. Native VideoClaw execution is exact-offer-only, never arbitrary Python dispatch.
10. Partial generated outputs are not left as successful artifacts.
11. Raw secrets/provider errors/host paths are not written to portable provenance.
12. Vendor VideoClaw source remains a compatibility/reference boundary rather than the UV Studio orchestration core.

## Next architecture step

After the native Edge TTS slice is merged, Stage 4 starts with a deterministic existing-video range model and local FFmpeg range/context extraction. Generative replacement is layered later on the same provider-neutral range contract rather than being baked into the mechanical edit primitive.
