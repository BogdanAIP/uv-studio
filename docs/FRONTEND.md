# UV Studio Frontend

UV Studio's user-facing frontend lives at top-level `frontend/`.

It started as an exact derived copy of the pinned VideoClaw frontend, but it is now **UV Studio-owned product source** and is expected to diverge as projects, recipes and editing workflows are added.

## Source provenance

The initial frontend baseline came from:

- repository: `HITsz-TMG/VideoClaw`
- pinned commit: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`
- source subtree: `video-claw/video-claw/frontend`
- license: MIT

The exact initial source digest and file count are stored in:

```text
frontend/.uv-derived.json
```

The upstream MIT license is preserved in:

```text
frontend/UPSTREAM_LICENSE
```

The untouched comparison snapshot remains under:

```text
vendor/videoclaw-app/frontend/
```

## Promotion/reset tool

`tools/promote_frontend.py` exists to reproduce the original pinned frontend baseline.

Safe inspection:

```text
python tools/promote_frontend.py --check
```

This does not change files.

### Important: resetting is destructive

Once `frontend/` exists, this command intentionally fails:

```text
python tools/promote_frontend.py
```

Replacing the existing UV Studio frontend requires an explicit destructive flag:

```text
python tools/promote_frontend.py --force
```

`--force` deletes current UV Studio frontend changes and restores the pinned upstream-derived baseline. It should not be used as part of ordinary development.

The GitHub workflow `Reset frontend to pinned baseline` is therefore manual-only (`workflow_dispatch`) and also performs an explicit forced reset.

## Product boundary

The backend and frontend use different upstream strategies:

```text
Pinned backend runtime
    vendor/videoclaw-app/backend
          │
          ▼
    UV Studio wrappers/APIs

Pinned frontend snapshot
    vendor/videoclaw-app/frontend
          │ one-time derivation
          ▼
    frontend/   ← product source
```

The backend is kept close to upstream and wrapped where possible. The user-facing frontend is expected to change substantially, so continuously patching the immutable vendor snapshot would be counterproductive.

## Current UV Studio additions

The first product-owned frontend additions are:

- `/projects` — canonical project list/create screen;
- `/projects/[projectId]` — canonical project shell using stable UV Studio project IDs;
- `lib/projectsApi.ts` — client for `/api/uv/projects`;
- `/api/uv/*` Next.js proxy route;
- UV Studio metadata/title;
- a link from the existing production workspace to the canonical Projects screen.

The old production workspace remains available at `/` while it is migrated gradually.

## Identity rule

UV Studio `project_id` and legacy VideoClaw session IDs are different identifiers.

Do not silently map or substitute one for the other. Future Recipe Registry/workflow binding must model that relationship explicitly.

## Current migration policy

Do not rewrite all existing UI at once.

Prefer:

1. establish canonical UV Studio project/workflow surfaces;
2. keep useful existing production screens reachable;
3. move or adapt screens when a product requirement needs them;
4. remove obsolete upstream UI only after replacement behavior is verified.
