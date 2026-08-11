# Next Task

**Primary target:** after the optional Qwen-MM pack PR merges, implement the **MCP/provider execution consent + cost boundary**. Test execution with the local fake MCP server first. Do not make real paid Qwen/DashScope calls in CI.

## Why this comes next

UV Studio now has:

```text
semantic capability
  -> capability offers
      -> fail-closed selection policy
      -> safe local FFmpeg execution
      -> generic MCP discovery
      -> explicit MCP tool binding
      -> optional pinned Qwen-MM offers
```

The missing boundary is the one that turns a discovered/bound external offer into a permitted invocation **without allowing implicit spending**.

D-014 already says metadata is not execution permission. This slice implements that rule for MCP/provider calls.

## 1. Define external execution authorization

Create a product-owned, versioned authorization/request model. It should distinguish at least:

```text
free/local
free/remote
potentially_paid
paid
unknown_cost
```

Do not encode Qwen-specific logic into the authorization model.

A useful shape may include:

```text
capability_id
offer_id
selection_policy
cost_class
cost_estimate
cost_currency
cost_estimate_state
consent_mode
consent_token / one-shot authorization reference
project_id
run_id
```

Exact field names may change, but cost knowledge and user consent must be explicit.

## 2. Fail closed on unknown or paid-capable cost

Initial policy:

- local/free remains executable by existing rules;
- remote/free requires explicit remote-execution permission but no payment consent;
- `potentially_paid`, `paid` or unknown-cost external tools require an explicit **one-shot** user authorization before invocation;
- no remembered global "always allow paid" switch in the first version;
- no automatic fallback from local failure into a paid offer;
- no invocation when price is unknown unless the authorization explicitly acknowledges unknown cost.

The API must return a structured `consent_required` response rather than silently invoking the tool.

## 3. Cost estimate contract

Do not invent prices.

Support an estimate state such as:

```text
known
bounded
unknown
not_applicable
```

A provider adapter may later supply:

- fixed known price;
- upper bound;
- estimated range;
- unknown.

For the first slice, fake MCP fixtures can expose deterministic test metadata. Qwen cloud offers may remain `unknown` until an auditable current pricing adapter exists.

Never treat `potentially_paid` as free merely because no estimate is available.

## 4. One-shot authorization store

Use UV Studio machine/runtime state, not portable project state, for ephemeral authorization tokens.

Requirements:

- random opaque token;
- bound to exact project + capability + offer + normalized input digest;
- one use only;
- short expiration;
- not written into `.uvproj.zip`;
- cannot authorize a different tool/input after mutation;
- no raw secret credentials inside token/public API.

If a simpler signed in-memory grant is safer than persistence, prefer it initially.

## 5. Add actual generic MCP tool invocation

Only after authorization exists, extend the official SDK adapter with a bounded `call_tool` path.

Requirements:

- exact discovered/bound tool only;
- no fuzzy tool resolution;
- bounded call timeout;
- official SDK cancellation/cleanup;
- no resident child process required initially;
- normalized JSON-serializable arguments;
- strict maximum request/response sizes;
- child stderr remains private;
- structured tool error handling;
- external invocation provenance recorded.

Use the existing local MCP fixture for all execution tests.

## 6. Project-scoped external inputs/outputs

Do not let MCP tool arguments become arbitrary host filesystem access through UV Studio.

Where a binding accepts project files:

- resolve project-relative paths through Project Store;
- binding/adapter decides which input fields are file paths;
- only allowed project roots;
- do not expose canonical project directory paths to APIs unnecessarily;
- imported/generated output must be copied/registered into canonical project artifacts before being considered durable.

Do not attempt a universal automatic path-rewriter based on field names.

## 7. Invocation provenance

Every allowed external execution should produce durable run metadata containing at least:

```text
run_id
project_id
capability_id
offer_id
adapter/profile/tool identity
started_at/completed_at
selection/authorization mode
cost estimate snapshot
status
input digest
result/artifact references
error class if failed
```

Do not persist secret values or full sensitive provider payloads by default.

Reuse Project Store `tasks/` or introduce a small versioned run record only if needed; do not add a database without measured need.

## 8. API shape

Prefer a two-step explicit flow for paid-capable tools:

```text
POST /api/uv/projects/{project}/capabilities/{capability}/prepare-execution
  -> selected offer + cost state + consent_required

POST /api/uv/projects/{project}/capabilities/{capability}/authorize-execution
  -> one-shot grant

POST /api/uv/projects/{project}/capabilities/{capability}/execute
  -> grant required when policy says so
```

Exact endpoint split may be simplified, but a single call must not both request and silently assume paid consent.

Existing free/local execution compatibility should remain stable.

## 9. Qwen boundary

Do not make a real DashScope call in this slice unless the user later explicitly requests testing with credentials and understands potential cost.

For current Qwen packs:

```text
core.media_info             -> local/free metadata offer
Qwen API tools              -> remote/potentially_paid
qwen_image/qwen_tts/wan_*   -> remote/potentially_paid
```

`wan_s2v` may become an executable digital-human offer only after this consent boundary works generically.

Qwen price remains unknown unless separately verified from current official provider pricing; unknown cost must require explicit acknowledgement.

## 10. OpenClaw boundary

Do not add OpenClaw during this slice.

The authorization/cost contract must be reusable by a future OpenClaw adapter without making it mandatory.

## 11. Tests

Use the local official-SDK MCP fixture. Extend it with deterministic tools such as:

```text
free_echo
remote_free_echo
paid_echo
large_result
slow_tool
error_tool
```

Cover at least:

- free/local existing FFmpeg path still works unchanged;
- `local_free_first` still never widens to remote/paid;
- remote/free external invocation requires correct remote permission;
- potentially-paid/unknown-cost tool returns consent-required before invocation;
- one-shot authorization works exactly once;
- expired authorization rejected;
- grant bound to exact project/offer/input digest;
- altered input after authorization rejected;
- unknown-cost requires explicit acknowledgement;
- MCP `call_tool` success through real local stdio fixture;
- MCP tool timeout/error cleans process and creates failure provenance;
- response-size limit enforced;
- unbound tool cannot be invoked even if discovered;
- missing/renamed tool fails closed;
- public execution/run records contain no resolved API keys;
- project archives do not contain ephemeral consent tokens;
- Linux + Windows unit/API/HTTP/frontend CI green.

## Architecture decisions to preserve

- D-011: adapters are peers; OpenClaw optional.
- D-012: Qwen-MM optional; no mandatory DashScope.
- D-013: semantic capability != offer.
- D-014: metadata != execution permission.
- D-015: MCP discovery is explicit and safe.
- D-016: Qwen pack is pinned, optional, and per-tool cost classified.

## What NOT to do

- no "allow all paid providers" global switch;
- no implicit spend after selection fallback;
- no price guessing;
- no generic arbitrary MCP tool endpoint by raw tool name;
- no fuzzy binding;
- no raw host paths from external callers;
- no secret values in run records/API/projects;
- no database unless measured need appears;
- no real paid CI calls;
- no OpenClaw dependency;
- no native-Windows Qwen claim while upstream remains WSL2-only.

## Acceptance criteria

- external execution cannot occur without a semantic binding and policy approval;
- paid-capable/unknown-cost execution cannot occur without explicit one-shot authorization;
- authorization is bound to exact execution intent and cannot be replayed;
- real local MCP `call_tool` is cross-platform tested through official SDK;
- failures/timeouts leave no orphan process;
- provenance is durable and secret-free;
- current Qwen cloud offers remain non-executed in CI;
- all existing local/free behavior remains green on Linux and Windows.

After that, enable individual external capabilities incrementally, beginning with operations whose contracts/costs are well understood, and then move toward Stage 4 existing-video workflows.