"""Derived bounded context for linked-shot continuity review."""

from __future__ import annotations

from typing import Any

from .sequence_continuity import SequenceContinuityError, SequenceContinuityStore


def build_sequence_timeline_context(
    service: SequenceContinuityStore,
    project_id: str,
    *,
    sequence_id: str,
    take_id: str,
    window_us: int = 1_500_000,
    samples: int = 3,
) -> dict[str, Any]:
    """Return bounded media context enriched with current observed review facts.

    Canonical state stays in SequenceContinuityStore. This function only derives a
    compact inspection view for a concrete current take/plan binding.
    """

    payload = service.timeline_context(
        project_id,
        sequence_id=sequence_id,
        take_id=take_id,
        window_us=window_us,
        samples=samples,
    )
    state = service.load(project_id)
    sequence = state.sequence(sequence_id)
    candidate = sequence.take(take_id)

    payload["candidate"]["observations"] = _current_observations(sequence, candidate.take_id)
    anchor = payload.get("anchor")
    if anchor is not None:
        payload["anchor"]["observations"] = _current_observations(
            sequence,
            anchor["take_id"],
            require_approved=True,
        )
    return payload


def _current_observations(
    sequence,
    take_id: str,
    *,
    require_approved: bool = False,
) -> list[dict[str, Any]]:
    take = sequence.take(take_id)
    if take.current_review_id is None:
        if require_approved:
            raise SequenceContinuityError("accepted anchor requires a current approved review")
        return []
    review = sequence.review(take.current_review_id)
    plan = sequence.plan(take.shot_id)
    current_binding = (
        review.take_id == take.take_id
        and review.shot_id == take.shot_id
        and review.take_sha256 == take.artifact_sha256
        and review.plan_revision_sha256 == take.plan_revision_sha256
        and review.plan_revision_sha256 == plan.revision_sha256
        and review.anchor_take_id == plan.anchor_take_id
        and review.anchor_take_sha256 == plan.anchor_take_sha256
    )
    expected_ids = {item.target_id for item in plan.review_targets}
    actual_ids = {item.target_id for item in review.results}
    targets_current = expected_ids == actual_ids and len(review.results) == len(actual_ids)
    required_pass = all(
        not target.required
        or next(
            (item.outcome for item in review.results if item.target_id == target.target_id),
            None,
        )
        == "pass"
        for target in plan.review_targets
    )
    approved_current = (
        current_binding and targets_current and required_pass and review.verdict == "approved"
    )
    if require_approved and not approved_current:
        raise SequenceContinuityError(
            "accepted anchor current review is stale or inconsistent with its shot plan"
        )
    if not current_binding or not targets_current:
        return []
    return [item.to_dict() for item in review.observations]
