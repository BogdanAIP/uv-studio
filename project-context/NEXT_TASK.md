# Next Task

**Primary target:** after the generic MCP discovery PR merges, add an **optional Qwen-MM-Plugins profile/binding pack** against a freshly re-verified upstream revision. Do not enable paid/cloud MCP tool execution yet.

## Why this comes next

Stage 3 now has the provider-neutral seam Qwen-MM needed:

```text
MCPProfile
  -> official SDK stdio discovery
      -> MCPToolDescriptor
          -> explicit MCPToolBinding
              -> semantic CapabilityOffer
```

This means Qwen-MM no longer needs a special architecture path or OpenClaw hop. It can be integrated as one optional capability package while recipes/projects remain unchanged.

## Mandatory first step — re-verify upstream

`QwenLM/Qwen-MM-Plugins` changes quickly. Before writing bindings, inspect the **current** repository/release/commit and verify:

- license;
- current install/launch method;
- MCP server entrypoint(s);
- actual current `list_tools` surface;
- current split between local/core operations and cloud/API operations;
- required environment variables;
- Windows native vs WSL support;
- whether tool names/schemas have changed from the previously inspected revision;
- whether pricing/cloud requirements have changed.

Pin the researched upstream revision in the Qwen profile-pack documentation/provenance. Do not assume the earlier `7dfc08b...` revision is still current.

## Qwen profile/binding pack

### 1. Keep it optional

Do not add Qwen-MM as a baseline runtime dependency.

A normal UV Studio installation must still start and run local/free functionality when:

- Qwen-MM is not installed;
- no DashScope/Qwen key exists;
- WSL is unavailable;
- the user never enables the profile.

### 2. Do not vendor the whole project by default

Prefer a profile/binding pack containing:

- verified launch template/instructions;
- environment-variable references;
- explicit tool bindings;
- provenance/version metadata;
- capability classifications;
- platform requirements.

Only copy code if a concrete technical need exists and Apache-2.0 NOTICE/attribution obligations are handled.

### 3. Classify each tool independently

For every useful current Qwen-MM tool considered for binding, record actual:

```text
semantic capability_id
locality
cost_class
configuration requirement
platform requirement
input/output contract
features
```

Important rule:

> Open-source repository license does not make a cloud model invocation free.

Examples of expected classification pattern, subject to re-verification:

- genuinely local file preparation/probing -> `local + free` when actually local;
- remote but no billed AI service -> `remote/hybrid + free` only when verified;
- DashScope/Qwen/Wan/Omni/cloud generation or analysis -> `remote/hybrid + potentially_paid` or `paid`;
- credentials missing -> not executable / configuration required.

Do not classify from names alone.

### 4. Bind only useful, semantically clean tools

Do not mirror the entire Qwen tool catalog into UV Studio.

Bind only operations that correspond cleanly to existing semantic capabilities or justify one new **provider-neutral** capability.

If a Qwen tool is highly provider-specific, leave it unbound rather than contaminating RecipeDefinition.

### 5. No MCP tool execution yet

This slice should validate:

```text
profile can be configured
  -> discovery succeeds where platform/runtime is available
  -> current tools match expected bindings
  -> offers show correct availability/locality/cost
```

Do not add general MCP `call_tool` execution until the explicit remote/paid consent/cost boundary is designed.

Even a Qwen binding marked local/free should not bypass the current execution architecture merely because discovery says it is available.

### 6. Windows behavior

If the current Qwen package still requires WSL2:

- represent that as an optional platform constraint;
- do not alter native UV Studio startup to require WSL;
- show profile unavailable/configuration-required with a clear reason on native Windows when the configured runtime is missing;
- generic direct MCP + local FFmpeg remain native Windows paths.

If Qwen now supports native Windows, verify it with a real CI/test path before claiming support.

### 7. Safe configuration helper

It is acceptable to add a **Qwen-specific trusted profile template/helper** because its command/arguments are known and constrained.

Do not add a generic HTTP endpoint that accepts arbitrary command strings.

A Qwen helper may write a profile with env references, but must never persist resolved API-key values.

### 8. Tests

Add fixture/config tests that do not require real paid credentials.

Cover at least:

- Qwen pack absent -> UV Studio starts normally;
- profile template contains no secret values;
- pinned upstream/provenance metadata exists;
- expected bindings are explicit and unique;
- cloud tools retain `potentially_paid/paid` metadata;
- missing credentials/runtime do not become `available` execution permission;
- unrecognized newly discovered Qwen tools remain unbound;
- missing/renamed expected tool degrades its offer to unavailable instead of fuzzy-remapping;
- `local_free_first` cannot select remote/potentially-paid Qwen offers;
- project archives contain no Qwen machine config/secrets;
- Windows baseline stays green without Qwen/WSL.

## Architecture decisions to preserve

- D-011: OpenClaw optional peer, not mandatory.
- D-012: Qwen-MM workflow donor/optional capability package, not paid baseline dependency.
- D-013: semantic capability != adapter offer.
- D-014: metadata != execution permission.
- D-015: direct MCP discovery is generic, explicit and non-executing.

## What NOT to do

- no mandatory DashScope;
- no implicit API purchase/spend;
- no OpenClaw dependency for Qwen;
- no fuzzy auto-binding of every discovered tool;
- no Qwen-specific names in RecipeDefinition;
- no raw secret values in config/API/projects;
- no generic arbitrary command profile editor;
- no MCP tool invocation in this slice;
- no WSL requirement for baseline native Windows UV Studio.

## Acceptance criteria

- current Qwen upstream is re-verified and pinned in provenance docs;
- optional Qwen profile can be represented without changing canonical projects;
- useful current Qwen tools have explicit semantic bindings only where justified;
- local/free vs remote/paid classification is auditable per tool;
- discovery mismatch fails closed;
- no real paid API call is needed for tests/startup;
- Qwen absence leaves all existing UV Studio functionality intact;
- Linux + Windows baseline CI remains green.

After that, design the **MCP/provider execution consent + cost boundary** and only then enable carefully selected tool invocation paths.
