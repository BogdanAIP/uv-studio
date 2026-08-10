# Next Task

**Primary target:** create a reproducible upstream import baseline for the modern VideoClaw application.

## Do first

1. Add a machine-readable lock/manifest for upstream VideoClaw commit `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`.
2. Add a deterministic vendoring/import tool that downloads that exact source revision and extracts only `video-claw/video-claw` into a controlled destination.
3. Preserve upstream MIT license/provenance next to imported source.
4. Add automated tests for path filtering, lock parsing and safe destination handling.
5. Add CI that runs the import-tool tests without requiring paid API credentials.

## Expected files

- `UPSTREAM.md`
- `upstream/video-claw.lock.json`
- `tools/vendor_videoclaw.py`
- `tests/test_vendor_videoclaw.py`
- `.github/workflows/ci.yml`
- `THIRD_PARTY_NOTICES.md`

## Acceptance criteria

- upstream revision is pinned by SHA, never `main`;
- importer cannot write outside its requested destination;
- importer extracts only the modern app subtree;
- repeated import produces the same logical file set for the same pin;
- tests run without any model/API key;
- CI executes the tests on Windows and Linux;
- repository context files are updated after completion.

## Explicitly out of scope for this slice

- Project Store implementation;
- Recipe Registry implementation;
- OpenClaw integration;
- music-video logic;
- UI redesign;
- provider migrations;
- cleanup/refactor of imported VideoClaw code before baseline is captured.

Keep this task narrow: establish reproducible provenance and baseline first.