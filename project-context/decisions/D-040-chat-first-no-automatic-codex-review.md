# D-040 — Chat-first development; no automatic Codex review

**Status:** accepted

## Context

UV Studio development is coordinated from Chat with GitHub as durable project memory and execution surface. The repository owner wants normal development, PR analysis and code review to consume Chat capacity only. Codex capacity is reserved for explicit manual use by the owner when they decide it is necessary.

During PR #35, comments from `chatgpt-codex-connector[bot]` showed that automatic Codex code review can be triggered by an external GitHub/Codex integration even though the UV Studio repository contains no Codex review workflow or script. That external behavior must not become part of UV Studio's development protocol or readiness gates.

## Decision

1. **Chat is the default development and review agent for UV Studio.** Repository analysis, implementation planning, diff review, architecture review and PR readiness assessment are performed through Chat plus ordinary GitHub tooling.
2. **Automatic Codex code review is excluded from the UV Studio development process.** The coordinator must not request `@codex review`, request Codex as a reviewer, add a Codex review workflow, add Codex review to required checks, or otherwise deliberately trigger Codex code review.
3. **Codex may be used only by explicit manual owner action.** A future manual Codex task/review is outside the normal UV Studio flow and occurs only when the repository owner explicitly requests or starts it.
4. **Ordinary CI is not Codex review.** GitHub Actions, unit/API/E2E/real-media tests, lint, dependency audit and build checks remain required engineering evidence.
5. **The GitHub connector remains allowed.** Chat may continue to use the GitHub connector for repository reads/writes, PR management and Actions because this is the primary Chat development path and is distinct from asking Codex to review code.
6. **External auto-review configuration is not repository authority.** If an account/repository integration independently enables Codex auto-review, that is an external configuration defect relative to this policy. It must not be treated as a required reviewer or readiness signal. Where the external product exposes a disable control, automatic review for UV Studio should be disabled while retaining the Chat GitHub connection when possible.

## Enforcement

- `project-context/ACTIVE_SLICE.json.required_checks` remains limited to the permanent non-Codex CI set validated by `tools/validate_development_context.py`.
- Repository workflows must not add Codex review automation.
- `tests/test_no_automatic_codex_review.py` scans `.github` and fails the permanent unit-test suite if a Codex review trigger/integration is added there.
- PR templates, instructions and coordinator actions must not ask Codex for automatic review.
- A Codex review result, absence, failure or usage-limit message cannot block or satisfy a UV Studio lifecycle transition.

## Consequences

UV Studio preserves Codex quota for deliberate manual use while keeping development fully operable through Chat. Review confidence comes from Chat-based code/architecture review plus reproducible CI evidence rather than an automatic Codex reviewer. If the external Codex/GitHub product cannot separate repository access from automatic review, that limitation is handled outside repository code; it does not change this project decision.
