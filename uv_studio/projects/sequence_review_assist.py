"""Ephemeral provider-neutral VLM review assistance for linked-shot continuity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .sequence_context import build_sequence_timeline_context
from .sequence_continuity import (
    MAX_OBSERVATIONS_PER_REVIEW,
    SequenceContinuityError,
    SequenceContinuityStore,
    SequenceNotFound,
    SequenceObservation,
    SequenceReviewNotFound,
    SequenceReviewResult,
    SequenceShotNotFound,
    SequenceTakeNotFound,
)

SEQUENCE_REVIEW_ASSIST_SCHEMA_VERSION = 1
SEQUENCE_REVIEW_ASSIST_CAPABILITY_ID = "media.understand"
_SUGGESTION_VERDICTS = frozenset({"approved", "needs_revision", "rejected"})


class SequenceReviewAssistError(SequenceContinuityError):
    """Invalid, stale or unsafe review-assist data."""


@dataclass(frozen=True)
class SequenceReviewAssistBinding:
    sequence_id: str
    shot_id: str
    take_id: str
    plan_revision_sha256: str
    take_sha256: str
    anchor_take_id: str | None
    anchor_take_sha256: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "shot_id": self.shot_id,
            "take_id": self.take_id,
            "plan_revision_sha256": self.plan_revision_sha256,
            "take_sha256": self.take_sha256,
            "anchor_take_id": self.anchor_take_id,
            "anchor_take_sha256": self.anchor_take_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SequenceReviewAssistBinding":
        if not isinstance(data, Mapping):
            raise SequenceReviewAssistError("review-assist binding must be an object")
        allowed = {
            "sequence_id",
            "shot_id",
            "take_id",
            "plan_revision_sha256",
            "take_sha256",
            "anchor_take_id",
            "anchor_take_sha256",
        }
        unknown = set(data).difference(allowed)
        missing = allowed.difference(data)
        if unknown or missing:
            raise SequenceReviewAssistError(
                f"invalid review-assist binding fields; missing={sorted(missing)!r}, "
                f"unknown={sorted(unknown)!r}"
            )
        return cls(**{key: data[key] for key in allowed})


@dataclass(frozen=True)
class SequenceReviewAssistPackage:
    binding: SequenceReviewAssistBinding
    capability_input: dict[str, Any]
    schema_version: int = SEQUENCE_REVIEW_ASSIST_SCHEMA_VERSION
    capability_id: str = SEQUENCE_REVIEW_ASSIST_CAPABILITY_ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "binding": self.binding.to_dict(),
            "capability_input": self.capability_input,
            "requires_human_confirmation": True,
            "canonical_state_mutated": False,
        }


@dataclass(frozen=True)
class SequenceReviewAssistSuggestion:
    binding: SequenceReviewAssistBinding
    verdict: str
    results: tuple[SequenceReviewResult, ...]
    observations: tuple[SequenceObservation, ...]
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": self.binding.to_dict(),
            "verdict": self.verdict,
            "results": [item.to_dict() for item in self.results],
            "observations": [item.to_dict() for item in self.observations],
            "note": self.note,
            "requires_human_confirmation": True,
            "canonical_state_mutated": False,
        }


def build_sequence_review_assist(
    service: SequenceContinuityStore,
    project_id: str,
    *,
    sequence_id: str,
    take_id: str,
    window_us: int = 1_500_000,
    samples: int = 3,
) -> SequenceReviewAssistPackage:
    """Build an ephemeral VLM-ready package without changing canonical project state."""

    try:
        context = build_sequence_timeline_context(
            service,
            project_id,
            sequence_id=sequence_id,
            take_id=take_id,
            window_us=window_us,
            samples=samples,
        )
    except (SequenceNotFound, SequenceShotNotFound, SequenceTakeNotFound, SequenceReviewNotFound):
        raise
    except SequenceContinuityError as exc:
        raise SequenceReviewAssistError(str(exc)) from exc
    state = service.load(project_id)
    sequence = state.sequence(sequence_id)
    take = sequence.take(take_id)
    if take.status != "prepared":
        raise SequenceReviewAssistError("review assist is only available for a prepared take")
    plan = sequence.plan(take.shot_id)
    if take.plan_revision_sha256 != plan.revision_sha256:
        raise SequenceReviewAssistError("take plan binding is stale")

    binding = SequenceReviewAssistBinding(
        sequence_id=sequence.sequence_id,
        shot_id=plan.shot_id,
        take_id=take.take_id,
        plan_revision_sha256=plan.revision_sha256,
        take_sha256=take.artifact_sha256,
        anchor_take_id=plan.anchor_take_id,
        anchor_take_sha256=plan.anchor_take_sha256,
    )
    media = [_assist_media(context["candidate"])]
    if context["anchor"] is not None:
        media.insert(0, _assist_media(context["anchor"]))

    capability_input = {
        "task": "sequence_continuity_take_review",
        "binding": binding.to_dict(),
        "media": media,
        "context": {
            "shot_intent": plan.intent,
            "locks": [item.to_dict() for item in plan.locks],
            "allowed_changes": [item.to_dict() for item in plan.allowed_changes],
            "review_targets": [item.to_dict() for item in plan.review_targets],
            "anchor_observations": (
                [] if context["anchor"] is None else context["anchor"]["observations"]
            ),
        },
        "requested_output": {
            "verdict": ["approved", "needs_revision", "rejected"],
            "results": [
                {
                    "target_id": target.target_id,
                    "outcome": ["pass", "fail", "uncertain"],
                    "note": "optional concise evidence note",
                }
                for target in plan.review_targets
            ],
            "observations": {
                "max_items": MAX_OBSERVATIONS_PER_REVIEW,
                "kind": ["observation", "inference"],
                "category": [
                    "visual",
                    "motion",
                    "audio",
                    "timing",
                    "content",
                    "technical",
                    "style",
                ],
                "confidence": ["low", "medium", "high"],
            },
            "note": "optional overall note",
        },
        "instructions": (
            "Inspect only the bounded anchor-tail and candidate-head evidence supplied here. "
            "Return a structured suggestion matching requested_output. Do not claim acceptance, "
            "change project state, or infer facts outside the supplied evidence."
        ),
    }
    return SequenceReviewAssistPackage(binding=binding, capability_input=capability_input)


def normalize_sequence_review_suggestion(
    service: SequenceContinuityStore,
    project_id: str,
    *,
    sequence_id: str,
    take_id: str,
    payload: Mapping[str, Any],
) -> SequenceReviewAssistSuggestion:
    """Validate a VLM suggestion against current bindings without applying it."""

    if not isinstance(payload, Mapping):
        raise SequenceReviewAssistError("review-assist suggestion must be an object")
    allowed = {"binding", "verdict", "results", "observations", "note"}
    unknown = set(payload).difference(allowed)
    missing = allowed.difference(payload)
    if unknown or missing:
        raise SequenceReviewAssistError(
            f"invalid review-assist suggestion fields; missing={sorted(missing)!r}, "
            f"unknown={sorted(unknown)!r}"
        )

    current = build_sequence_review_assist(
        service,
        project_id,
        sequence_id=sequence_id,
        take_id=take_id,
    )
    supplied_binding = SequenceReviewAssistBinding.from_dict(payload["binding"])
    if supplied_binding != current.binding:
        raise SequenceReviewAssistError(
            "review-assist suggestion is stale or bound to a different take/plan/anchor"
        )

    verdict = payload["verdict"]
    if not isinstance(verdict, str) or verdict not in _SUGGESTION_VERDICTS:
        raise SequenceReviewAssistError(
            "review-assist verdict must be approved, needs_revision, or rejected"
        )
    results_raw = payload["results"]
    observations_raw = payload["observations"]
    if not isinstance(results_raw, list) or not isinstance(observations_raw, list):
        raise SequenceReviewAssistError("review-assist results/observations must be lists")

    state = service.load(project_id)
    sequence = state.sequence(sequence_id)
    plan = sequence.plan(sequence.take(take_id).shot_id)
    if len(results_raw) != len(plan.review_targets):
        raise SequenceReviewAssistError(
            "review-assist results must cover each current review target exactly once"
        )
    if len(observations_raw) > MAX_OBSERVATIONS_PER_REVIEW:
        raise SequenceReviewAssistError(
            f"review-assist observations must contain at most {MAX_OBSERVATIONS_PER_REVIEW} items"
        )

    results = tuple(SequenceReviewResult.from_dict(item) for item in results_raw)
    observations = tuple(SequenceObservation.from_dict(item) for item in observations_raw)
    expected_ids = {item.target_id for item in plan.review_targets}
    actual_ids = {item.target_id for item in results}
    if expected_ids != actual_ids or len(results) != len(actual_ids):
        raise SequenceReviewAssistError(
            "review-assist results must cover each current review target exactly once"
        )
    by_id = {item.target_id: item for item in results}
    if verdict == "approved":
        failing_required = [
            target.target_id
            for target in plan.review_targets
            if target.required and by_id[target.target_id].outcome != "pass"
        ]
        if failing_required:
            raise SequenceReviewAssistError(
                "approved review-assist suggestion requires pass for all required targets: "
                f"{sorted(failing_required)!r}"
            )

    note = payload["note"]
    if note is not None:
        if not isinstance(note, str) or not note.strip():
            raise SequenceReviewAssistError("review-assist note must be a non-empty string or null")
        if len(note.strip()) > 4000:
            raise SequenceReviewAssistError("review-assist note must be <= 4000 characters")
        note = note.strip()

    return SequenceReviewAssistSuggestion(
        binding=supplied_binding,
        verdict=verdict,
        results=results,
        observations=observations,
        note=note,
    )


def _assist_media(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": value["role"],
        "project_reference": value["reference_path"],
        "sha256": value["sha256"],
        "window_start_us": value["window_start_us"],
        "window_end_us": value["window_end_us"],
        "sample_times_us": list(value["sample_times_us"]),
        "observations": list(value.get("observations", [])),
    }
