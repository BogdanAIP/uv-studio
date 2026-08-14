"""Derived bounded context for linked-shot continuity review."""

from __future__ import annotations

from typing import Any

from .sequence_continuity import SequenceContinuityStore


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
        return []
    review = sequence.review(take.current_review_id)
    if require_approved and review.verdict != "approved":
        return []
    return [item.to_dict() for item in review.observations]
