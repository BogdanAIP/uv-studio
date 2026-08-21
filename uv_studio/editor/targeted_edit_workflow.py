"""Semantic targeted-edit workflow operations over existing canonical domain stores."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from uv_studio.projects.continuity_brief import RangeContinuityBrief, RangeContinuityBriefStore
from uv_studio.projects.models import ProjectReference
from uv_studio.projects.replacement_candidate import ReplacementCandidateStore
from uv_studio.projects.replacement_plan import ReplacementPlanProposal, ReplacementPlanStore
from uv_studio.projects.replacement_review import (
    ReplacementReviewAssessment,
    ReplacementReviewObservation,
    ReplacementReviewStore,
    ReviewEvidenceReference,
)
from uv_studio.projects.source_media import ProjectSourceMediaStore
from uv_studio.projects.store import ProjectStore

from .commands import EditorCommandService, SelectRangeCommand

_SAFE_VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v"})


class TargetedEditWorkflowError(RuntimeError):
    """The requested semantic targeted-edit operation is not valid for current state."""


def _requested_change(brief: RangeContinuityBrief) -> str:
    for constraint in brief.constraints:
        if constraint.constraint_id == "requested_change":
            return constraint.requirement
    if brief.constraints:
        return brief.constraints[0].requirement
    raise TargetedEditWorkflowError("current edit brief has no requested change constraint")


class TargetedEditWorkflowService:
    """Facade over existing editor/replacement domains; owns no persistent workflow state."""

    def __init__(self, project_store: ProjectStore) -> None:
        self.project_store = project_store
        self.source_media = ProjectSourceMediaStore(project_store)

    def select_target_range(
        self,
        project_id: str,
        *,
        source_id: str,
        start_us: int,
        end_us: int,
        change_request: str,
        context_before_us: int = 5_000_000,
        context_after_us: int = 5_000_000,
    ) -> dict[str, Any]:
        result = EditorCommandService(self.project_store).select_range(
            project_id,
            SelectRangeCommand(
                source_id=source_id,
                start_us=start_us,
                end_us=end_us,
                change_request=change_request,
                context_before_us=context_before_us,
                context_after_us=context_after_us,
            ),
        )
        return result.to_dict()

    def prepare_replacement(
        self,
        project_id: str,
        *,
        edit_id: str,
        replacement_source_id: str,
    ) -> dict[str, Any]:
        brief = RangeContinuityBriefStore(self.project_store).validate_project(project_id).get(edit_id)
        replacement_reference, replacement_path = self.source_media.resolve_verified(
            project_id,
            replacement_source_id,
            expected_kind="video",
        )
        if replacement_reference.path == brief.source_path:
            raise TargetedEditWorkflowError("replacement source must be different from the edited source")

        change = _requested_change(brief)
        plans = ReplacementPlanStore(self.project_store)
        previous_plan_state = plans.load(project_id)
        plan_state = plans.approve(
            project_id,
            ReplacementPlanProposal(
                edit_id=brief.edit_id,
                method_class="prepared_asset",
                goal=change,
                required_changes=(change,),
                allowed_changes=(),
                forbidden_changes=("Не изменять исходное видео вне выбранного диапазона.",),
                audio_strategy="preserve_source",
            ),
        )
        plan = plan_state.get(brief.edit_id)

        artifact_path = None
        artifact_id = f"art_{uuid.uuid4().hex}"
        candidate_id = f"cand_{uuid.uuid4().hex}"
        registered = False
        try:
            suffix = replacement_path.suffix.lower()
            if suffix not in _SAFE_VIDEO_SUFFIXES:
                raise TargetedEditWorkflowError("replacement source uses an unsupported video extension")

            relative_path = f"artifacts/{artifact_id}{suffix}"
            artifact_path = self.project_store.resolve_project_file(
                project_id,
                relative_path,
                allowed_roots=("artifacts",),
            )
            reference = ProjectReference(
                id=artifact_id,
                kind="video",
                path=relative_path,
                metadata={
                    "lifecycle": "replacement_candidate",
                    "method_class": "prepared_asset",
                    "source_asset_path": replacement_reference.path,
                },
            )

            if artifact_path.exists() or artifact_path.is_symlink():
                raise TargetedEditWorkflowError("allocated replacement candidate path already exists")
            shutil.copyfile(replacement_path, artifact_path)
            if not artifact_path.is_file() or artifact_path.is_symlink() or artifact_path.stat().st_size <= 0:
                raise TargetedEditWorkflowError("replacement candidate artifact must be a non-empty regular file")

            project = self.project_store.load_project(project_id)
            self.project_store.update_project(
                project_id,
                artifacts=(*project.artifacts, reference),
            )
            registered = True

            candidates = ReplacementCandidateStore(self.project_store)
            candidate = candidates.make_candidate(
                project_id,
                candidate_id=candidate_id,
                edit_id=brief.edit_id,
                stage="full",
                artifact_id=artifact_id,
                artifact_path=relative_path,
            )
            candidate_state = candidates.register(project_id, candidate)
            return {
                "plan": plan.to_dict(),
                "candidate": candidate.to_dict(),
                "candidate_state": candidate_state.to_dict(),
            }
        except Exception:
            if registered:
                try:
                    project = self.project_store.load_project(project_id)
                    self.project_store.update_project(
                        project_id,
                        artifacts=tuple(item for item in project.artifacts if item.id != artifact_id),
                    )
                except Exception:
                    pass
            try:
                if artifact_path is not None and artifact_path.exists() and not artifact_path.is_symlink():
                    artifact_path.unlink()
            except OSError:
                pass
            try:
                # Plan is hidden inside this composite user action. Restore the exact prior state
                # so a failed Candidate preparation cannot invalidate an older valid candidate/review.
                with self.project_store._lock:
                    plans._write(project_id, previous_plan_state)
            except Exception as rollback_exc:
                raise TargetedEditWorkflowError(
                    "replacement preparation failed and the previous plan state could not be restored"
                ) from rollback_exc
            raise

    def review_replacement(
        self,
        project_id: str,
        *,
        candidate_id: str,
        verdict: str,
        observations: Sequence[Mapping[str, Any]],
        assessments: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        domain_observations = tuple(
            ReplacementReviewObservation(
                observation_id=str(item["observation_id"]),
                kind=str(item["kind"]),
                statement=str(item["statement"]),
                confidence=str(item["confidence"]),
                evidence=tuple(
                    ReviewEvidenceReference(
                        kind=str(reference["kind"]),
                        ref_id=str(reference["ref_id"]),
                    )
                    for reference in item["evidence"]
                ),
            )
            for item in observations
        )
        domain_assessments = tuple(
            ReplacementReviewAssessment(
                target_id=str(item["target_id"]),
                outcome=str(item["outcome"]),
                observation_ids=tuple(str(value) for value in item["observation_ids"]),
            )
            for item in assessments
        )
        review_id = f"review_{uuid.uuid4().hex}"
        state = ReplacementReviewStore(self.project_store).create_review(
            project_id,
            review_id=review_id,
            candidate_id=candidate_id,
            verdict=verdict,
            observations=domain_observations,
            assessments=domain_assessments,
        )
        return state.get(review_id).to_dict()

    def accept_replacement(self, project_id: str, *, review_id: str) -> dict[str, Any]:
        state = ReplacementReviewStore(self.project_store).accept_review(project_id, review_id)
        return state.to_dict()
