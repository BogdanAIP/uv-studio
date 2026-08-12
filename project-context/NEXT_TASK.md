# Next Task

<!-- uv-next-slice: stage-4-range-edit-user-workflow -->

Updated: 2026-08-12

## Expected handoff

After the replacement review gate is merged, continue with Stage 4C as `stage-4-range-edit-user-workflow`.

The next slice should turn the completed Stage 4 domain chain into the first complete user-facing targeted existing-video edit workflow rather than adding another backend-only gate.

## Required direction

```text
open existing-video project
  -> preview source
  -> choose exact range on a microsecond-backed timeline
  -> inspect bounded context / Brief / approved Plan
  -> prepare or select ReplacementCandidate
  -> inspect review verdict and evidence
  -> explicitly accept approved candidate or continue revision
  -> explicit final render/export
```

Requirements:

- add a UV Studio-owned range-edit workspace under the project UI rather than routing the user back to legacy production tools;
- source preview and range selection must preserve integer-microsecond backend identity even if the browser UI uses human-readable time;
- show bounded before/requested/after context and current Brief/Plan state without exposing provider/runtime secrets;
- support deterministic/prepared candidate paths and optional generated candidates through existing capability/authorization APIs;
- surface sample-first state and charge/remote consent before optional external generation;
- display candidate review targets, observations/evidence and `approved` / `rejected` / `needs_revision` verdicts;
- only expose acceptance for a current approved review; never recreate the removed caller-controlled replacement-path bypass;
- preview the accepted decision in context before explicit final render/export;
- keep original source immutable and canonical edit state non-destructive;
- add frontend component/unit/accessibility coverage and browser E2E for the permanent 5–10 second targeted-edit regression scenario;
- do not begin dubbing, music-video mode or desktop packaging in this slice.
