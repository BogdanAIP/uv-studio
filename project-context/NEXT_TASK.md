# Next Task

<!-- uv-next-slice: fix-dependency-ownership -->

Updated: 2026-08-12

## Primary target

Make UV Studio own its **core runtime dependency contract** after the application security boundary is closed.

The current repository still installs the complete vendored VideoClaw backend requirements before `requirements-uv.txt`, and `requirements-uv.txt` itself declares only MCP. As a result FastAPI/Uvicorn/Pydantic and multiple provider SDKs are still obtained incidentally from the vendor dependency set.

The next slice is:

```text
fix-dependency-ownership
  -> explicit UV Studio core dependencies
  -> optional provider/runtime extras
  -> development setup uses product-owned dependency groups
  -> frontend dependency/lint audit
  -> CI verifies the declared baseline independently
```

## Required outcomes

### 1. UV Studio owns its core Python runtime requirements

Inventory imports under `uv_studio/`, tests and product launch tools and define the smallest justified core runtime set with bounded versions/constraints appropriate for reproducible development.

Acceptance:

- a clean environment can import and run the UV Studio-owned server/tests using product-owned requirements rather than relying on the vendor requirements file to provide missing packages;
- FastAPI/Uvicorn/Pydantic and other actual UV Studio core imports are declared explicitly;
- dependency choices are documented rather than copied wholesale from VideoClaw.

### 2. Optional provider/runtime dependencies are truly optional

Separate provider/runtime extras such as Edge TTS and future provider SDKs from the baseline.

Acceptance:

- baseline development does not install OpenAI, DashScope, Playwright, Edge TTS or another provider stack solely because VideoClaw contains it;
- an unavailable optional adapter reports clear `configuration_required`/`unavailable` state rather than breaking server startup;
- the existing optional Edge TTS path remains installable through its explicit extra requirement.

### 3. Vendor compatibility dependencies are isolated

If retained legacy compatibility code still requires a subset of VideoClaw packages, model that as an explicit compatibility dependency group or documented temporary boundary rather than making `vendor/videoclaw-app/backend/requirements.txt` the implicit product baseline.

Do not modify the pinned vendor snapshot to solve dependency ownership.

### 4. Frontend dependency health is brought under control

Audit the current Next/React/ESLint dependency graph and the advisories reported by `npm ci`.

Acceptance:

- Next/ESLint configuration versions are mutually compatible;
- `npm run lint` succeeds without blanket ignores over product source;
- each high-severity advisory is either removed by a justified dependency update or recorded as a narrow accepted residual risk with package/path/reason;
- frontend lint becomes an actual CI gate for subsequent product slices.

### 5. CI proves the new dependency boundary

Acceptance:

- at least one CI job installs UV Studio core requirements without first installing the full vendored backend requirements and successfully imports/compiles/tests product-owned code;
- compatibility/app-baseline jobs may install an explicit compatibility group only where still required;
- Ubuntu and Windows remain first-class;
- existing capability, MCP, project and range tests stay green.

## Scope control

Do not combine this slice with:

- new providers;
- `RangeContinuityBrief`;
- real FFmpeg golden fixtures;
- non-destructive timeline refactor;
- desktop installer/packaging;
- broad frontend redesign.

## Handoff after this slice

Next intended order:

```text
fix-dependency-ownership
  -> test-real-media-golden
  -> refactor/non-destructive-media-edit-core if evidence justifies it
  -> stage-4-range-continuity-brief
  -> Stage 4C targeted-range user workflow
```
