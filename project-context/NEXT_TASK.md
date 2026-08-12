# Next Task

<!-- uv-next-slice: fix-runtime-security-boundary -->

Updated: 2026-08-12

## Primary target

Close the application-wide **runtime security boundary** before adding `RangeContinuityBrief`, another provider, or new remote generation behavior.

The UV Studio-owned capability path already has strong selection and D-017 authorization semantics, but the running application still exposes legacy VideoClaw routes that can read/write provider configuration and invoke upstream model clients outside that boundary.

The next slice is therefore:

```text
fix-runtime-security-boundary
  -> protect provider secrets
  -> restrict browser access to the local backend
  -> stop legacy remote/non-free execution from bypassing UV Studio authorization
  -> keep useful legacy UI/runtime compatibility only behind explicit safe boundaries
```

This is a Stage 3.5 product prerequisite, not general release hardening.

## Required findings to close

### 1. Raw provider secrets are exposed through legacy configuration

The current vendored `/api/config` returns `Config.as_dict()`, which includes provider credential fields. The derived frontend consumes that route and round-trips the returned configuration on save.

Acceptance:

- configuration reads never return raw stored credentials;
- secret fields expose only presence/status or an explicit masked representation that cannot reconstruct the secret;
- secret updates use write-only semantics and do not require the browser to resend an existing credential;
- clearing/replacing a secret is explicit;
- tests prove raw values do not appear in HTTP JSON responses or logs.

### 2. Provider configuration is stored in a commit-prone vendor path

VideoClaw currently writes `vendor/videoclaw-app/backend/config.yaml`. The project root ignore rules do not make that an acceptable long-term credential store.

Acceptance:

- real runtime/provider configuration moves to a UV Studio-owned machine-local configuration location outside `vendor/` source;
- provider credentials cannot become ordinary untracked files inside the vendored source tree;
- repository ignore rules defensively exclude any transitional legacy secret file;
- portable Project Store archives never contain these credentials;
- migration from an existing local legacy config is explicit and secret-safe if supported.

Do not commit a real key at any point in testing.

### 3. Wildcard CORS exposes sensitive localhost APIs to arbitrary browser origins

The upstream application currently enables wildcard CORS while mutating configuration, sandbox, pipeline and file routes are mounted.

Acceptance:

- production/local app CORS allows only deliberate UV Studio frontend origins or disables cross-origin access where the same-origin frontend proxy is sufficient;
- credentialed/wildcard combinations are not used;
- tests prove an untrusted browser origin is not granted API access by CORS headers;
- localhost binding remains the default unless a future explicit remote-access feature defines authentication and threat model.

### 4. Legacy provider execution bypasses D-017

Upstream sandbox/pipeline routes can create provider clients directly. D-017 currently protects `/api/uv` capability execution but not the whole mounted application.

Acceptance:

Choose and implement the smallest safe boundary that preserves useful compatibility:

- preferred direction: UV Studio-owned application root, with only explicitly allowed legacy compatibility routers mounted;
- legacy provider-generating routes are disabled by default, migrated behind semantic capabilities, or wrapped in an equivalent product-owned authorization gate;
- no browser/API call can contact a remote or non-free provider without the applicable UV Studio execution preparation/consent flow;
- local deterministic legacy functionality may remain available when it has no hidden remote/cost behavior;
- tests exercise the actual application route table, not only adapter units.

Do not add a second independent consent system inside VideoClaw.

## Architectural direction

Prefer this ownership shape:

```text
UV Studio FastAPI app
  -> UV Studio routers
  -> explicit compatibility routers/sub-apps when still needed
       -> safe local-only legacy route, or
       -> product authorization/capability boundary
```

rather than permanently:

```text
complete VideoClaw FastAPI app
  + UV Studio routers appended afterward
```

Do not edit the pinned vendor snapshot unless a narrowly documented compatibility fix is unavoidable. Prefer UV Studio-owned app composition/wrappers.

## Tests required

At minimum prove:

1. `GET` configuration API never emits a configured raw provider key;
2. replacing a key works without browser round-trip of the old value;
3. saving configuration does not create a credential file under the vendored source tree;
4. canonical project export does not contain machine/provider secrets;
5. untrusted CORS origin does not receive permissive access headers;
6. intended local frontend origin still works;
7. at least one representative legacy remote-generation route cannot execute without product authorization or is no longer mounted by default;
8. UV Studio-owned local/free capability execution remains frictionless;
9. existing Projects, recipes, MCP, FFmpeg extraction/reinsertion and HTTP health tests remain green;
10. Ubuntu and Windows required CI matrix stays green.

## Scope control

Do not combine this slice with:

- `RangeContinuityBrief`;
- a new VLM/video provider;
- real FFmpeg golden media work except tests necessary to prevent regression;
- full dependency-ownership cleanup;
- desktop packaging;
- broad redesign of the frontend.

A following Stage 3.5 slice will own dependency manifests/frontend dependency health. After the runtime security gate is trustworthy, Stage 4A real-media golden verification and then Stage 4B `RangeContinuityBrief` may continue in that order.

## Handoff after this slice

Expected next ordering:

```text
fix-runtime-security-boundary
  -> fix-dependency-ownership
  -> test-real-media-golden
  -> refactor/non-destructive-media-edit-core as justified by evidence
  -> stage-4-range-continuity-brief
  -> Stage 4C user workflow
```

Do not jump directly to continuity or provider generation while an application route can still expose secrets or bypass authorization.
