# D-024 — Runtime trust and real-media evidence gate later product intelligence

Status: accepted  
Date: 2026-08-12

## Decision

UV Studio inserts a Stage 3.5 Runtime Independence & Security gate before further provider/intelligence growth, and Stage 4 completion is split into mechanical editing, edit intelligence and user workflow gates.

Security, dependency ownership and representative real-media verification are progressive prerequisites. They are not deferred wholesale to final desktop packaging.

## Context

A full repository audit after PR #20 found that the product-owned domain architecture is materially stronger than the currently mounted application/runtime boundary.

The UV Studio-owned capability path already provides provider-neutral selection and D-017 execution authorization, but the running server still mounts UV Studio routers onto the complete VideoClaw FastAPI application. The derived frontend also continues to use legacy VideoClaw configuration, sandbox and pipeline routes.

Concrete audit findings include:

- legacy `/api/config` returns the complete upstream configuration object containing provider credential fields;
- VideoClaw writes configuration into `vendor/videoclaw-app/backend/config.yaml`, which is inside the Git checkout and is not an acceptable credential store;
- the upstream app enables wildcard CORS while exposing mutating configuration, file, sandbox and pipeline APIs on localhost;
- legacy provider routes can invoke upstream clients outside the UV Studio D-017 preparation/consent path;
- `requirements-uv.txt` does not yet own the full UV Studio runtime dependency contract, so development installation still receives core and provider dependencies from the vendored backend requirement set;
- FFmpeg range tests strongly verify command contracts but do not yet prove the mechanical path against representative real encoded fixtures on both Windows and Linux;
- the current Stage 4 reinsertion correctness foundation re-encodes a complete lossless intermediate and therefore should not become the permanent repeated-edit state model;
- frontend/project UI maturity is behind backend/domain maturity, so backend capability existence must not be treated as the Stage 4 user outcome.

## Consequences

1. `fix-runtime-security-boundary` precedes `RangeContinuityBrief` and any new provider integration.
2. A following Stage 3.5 slice owns UV Studio dependency declarations and frontend dependency/lint health.
3. Stage 4A must add real FFmpeg/FFprobe golden verification before the mechanical path is called production-proven.
4. Stage 4B owns provider-neutral bounded evidence/continuity intelligence.
5. Stage 4C owns the complete user-facing timeline → preview → accept/reject → export path with browser E2E.
6. Stage 9 remains Windows productization/release hardening rather than the first time core security or media evidence is addressed.
7. Stage completion distinguishes an engineering gate from a user-outcome gate.
8. Product-wide claims such as "remote/non-free execution passes D-017" are not considered true while mounted legacy routes can bypass that boundary.
9. Canonical durable feature state should increasingly use typed/versioned models instead of relying on free-form project extension dictionaries for critical invariants.

## Non-decision

This decision does not discard VideoClaw, rewrite the application from scratch, replace the existing Project/Recipe/Capability architecture, or require immediate removal of all legacy routes. Useful compatibility may remain when it is explicitly mounted behind a safe UV Studio-owned boundary.

It also does not replace D-021/D-022 mechanics; those remain the correctness foundation for targeted range editing.
