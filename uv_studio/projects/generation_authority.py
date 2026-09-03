"""Shared durable Generation ProjectReference authority.

Generation output bytes are not part of ProjectUnitOfWork JSON snapshots. Any
code that preserves or restores a Generation ProjectReference must therefore
reconnect the historical reference to its durable Job/Attempt provenance and to
the exact output size/SHA-256 before trusting the binary payload.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .models import ProjectReference
from .store import ProjectStore, ProjectStoreError


class GenerationReferenceAuthorityError(RuntimeError):
    """A Generation ProjectReference no longer has one exact durable authority."""


@dataclass(frozen=True)
class GenerationReferenceAuthority:
    job_id: str
    attempt_id: str
    take_id: str
    shot_id: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class GenerationMaterializationAuthority:
    """Immutable Generation output authority before/after local reconciliation.

    A legacy or crash-split attempt may already own exact durable output bytes while
    its Job record is still RUNNING/FAILED/CANCELLED and therefore has no completed
    Take/output fields yet. That state is sufficient to preserve or explicitly Redo
    the exact bytes, but it is not sufficient for archive/success authority.
    """

    job_id: str
    attempt_id: str
    attempt_status: str
    output_reference_id: str | None
    take_id: str | None
    shot_id: str
    size_bytes: int
    sha256: str


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def generation_materialization_authority(
    store: ProjectStore,
    project_id: str,
    artifact: ProjectReference,
) -> GenerationMaterializationAuthority | None:
    """Validate immutable Job/Attempt provenance for one Generation output.

    Unlike ``generation_reference_authority()``, this permits the bounded legacy
    terminal-split states recovery already supports: exact artifact metadata/bytes
    can be durable while the owning attempt has not yet been reconciled to success.
    It never treats that incomplete state as successful Generation authority.
    """

    generation = artifact.metadata.get("generation")
    if not isinstance(generation, dict):
        return None

    job_id = generation.get("job_id")
    attempt_id = generation.get("attempt_id")
    if not isinstance(job_id, str) or not job_id or not isinstance(attempt_id, str) or not attempt_id:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact has incomplete durable provenance: {artifact.id}"
        )

    project_dir = store.project_directory(project_id)
    job_path = project_dir / "tasks" / f"{job_id}.json"
    if job_path.is_symlink() or not job_path.is_file():
        raise GenerationReferenceAuthorityError(
            f"Generation artifact has no safe durable Job record: {artifact.id}"
        )
    try:
        raw = json.loads(job_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenerationReferenceAuthorityError(
            f"Generation Job record is unreadable for artifact: {artifact.id}"
        ) from exc
    if not isinstance(raw, dict) or raw.get("record_type") != "generation_job":
        raise GenerationReferenceAuthorityError(
            f"Generation artifact points to a non-generation task record: {artifact.id}"
        )
    if raw.get("job_id") != job_id:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact job_id disagrees with durable Job: {artifact.id}"
        )

    attempts = raw.get("attempts")
    if not isinstance(attempts, list):
        raise GenerationReferenceAuthorityError(
            f"Generation Job has invalid attempt history for artifact: {artifact.id}"
        )
    matching_attempts = [
        attempt
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("attempt_id") == attempt_id
    ]
    if len(matching_attempts) != 1:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact does not resolve to one durable attempt: {artifact.id}"
        )
    attempt = matching_attempts[0]
    attempt_status = attempt.get("status")
    if attempt_status not in {"running", "succeeded", "failed", "cancelled"}:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact has invalid durable attempt status: {artifact.id}"
        )
    output_reference_id = attempt.get("output_reference_id")
    if output_reference_id is not None:
        if not isinstance(output_reference_id, str) or not output_reference_id:
            raise GenerationReferenceAuthorityError(
                f"Generation attempt has invalid output reference identity: {artifact.id}"
            )
        if output_reference_id != artifact.id:
            raise GenerationReferenceAuthorityError(
                f"Generation attempt output reference disagrees with artifact: {artifact.id}"
            )
    take_id = attempt.get("take_id")
    if take_id is not None and (not isinstance(take_id, str) or not take_id):
        raise GenerationReferenceAuthorityError(
            f"Generation attempt has invalid Take identity: {artifact.id}"
        )

    request = raw.get("request")
    mapping = request.get("execution_mapping") if isinstance(request, dict) else None
    contract = request.get("generation_contract") if isinstance(request, dict) else None
    shot_id = request.get("shot_id") if isinstance(request, dict) else None
    if not isinstance(shot_id, str) or not shot_id:
        raise GenerationReferenceAuthorityError(
            f"Generation Job lost shot authority for artifact: {artifact.id}"
        )

    authority = {
        "job_id": job_id,
        "attempt_id": attempt_id,
        "model_id": request.get("model_id") if isinstance(request, dict) else None,
        "capability_id": mapping.get("capability_id") if isinstance(mapping, dict) else None,
        "offer_id": mapping.get("offer_id") if isinstance(mapping, dict) else None,
        "adapter_id": mapping.get("adapter_id") if isinstance(mapping, dict) else None,
        "request_digest": raw.get("request_digest"),
    }
    for field_name, expected_value in authority.items():
        if not isinstance(expected_value, str) or not expected_value:
            raise GenerationReferenceAuthorityError(
                f"Generation Job lost {field_name} authority for artifact: {artifact.id}"
            )
        if generation.get(field_name) != expected_value:
            raise GenerationReferenceAuthorityError(
                f"Generation artifact {field_name} disagrees with durable Job: {artifact.id}"
            )
    if not isinstance(contract, dict) or generation.get("contract") != contract:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact contract disagrees with durable Job: {artifact.id}"
        )

    continuation_reference = contract.get("continuation_source_reference_id")
    if continuation_reference is None:
        expected_lineage = None
    elif isinstance(continuation_reference, str) and continuation_reference:
        expected_lineage = {
            "kind": "continuation",
            "source_reference_id": continuation_reference,
        }
    else:
        raise GenerationReferenceAuthorityError(
            f"Generation Job has invalid continuation authority for artifact: {artifact.id}"
        )
    if generation.get("lineage") != expected_lineage:
        raise GenerationReferenceAuthorityError(
            f"Generation artifact lineage disagrees with durable Job: {artifact.id}"
        )

    path_parts = PurePosixPath(artifact.path).parts
    if len(path_parts) != 2 or path_parts[0] != "artifacts":
        raise GenerationReferenceAuthorityError(
            f"Generation artifact path is outside the canonical artifacts root: {artifact.id}"
        )
    expected_name = f"generated_{attempt_id}"
    artifact_name = path_parts[1]
    if not (artifact_name == expected_name or artifact_name.startswith(expected_name + ".")):
        raise GenerationReferenceAuthorityError(
            f"Generation artifact path disagrees with durable attempt: {artifact.id}"
        )

    size_bytes = artifact.metadata.get("size_bytes")
    sha256 = artifact.metadata.get("sha256")
    if (
        isinstance(size_bytes, bool)
        or not isinstance(size_bytes, int)
        or size_bytes <= 0
        or not isinstance(sha256, str)
        or len(sha256) != 64
        or any(ch not in "0123456789abcdef" for ch in sha256)
    ):
        raise GenerationReferenceAuthorityError(
            f"Generation artifact has invalid size/digest authority: {artifact.id}"
        )

    return GenerationMaterializationAuthority(
        job_id=job_id,
        attempt_id=attempt_id,
        attempt_status=attempt_status,
        output_reference_id=output_reference_id,
        take_id=take_id,
        shot_id=shot_id,
        size_bytes=size_bytes,
        sha256=sha256,
    )


def generation_reference_authority(
    store: ProjectStore,
    project_id: str,
    artifact: ProjectReference,
) -> GenerationReferenceAuthority | None:
    """Validate complete durable Job/Attempt provenance for one Generation artifact.

    ``None`` means the ProjectReference is not a Generation artifact. Generation
    references fail closed if any durable identity, request mapping, contract,
    output path, size or digest authority is missing or contradictory.
    """

    materialization = generation_materialization_authority(store, project_id, artifact)
    if materialization is None:
        return None
    if (
        materialization.attempt_status != "succeeded"
        or materialization.output_reference_id != artifact.id
        or materialization.take_id is None
    ):
        raise GenerationReferenceAuthorityError(
            f"Generation materialization is not durably complete: {artifact.id}"
        )
    return GenerationReferenceAuthority(
        job_id=materialization.job_id,
        attempt_id=materialization.attempt_id,
        take_id=materialization.take_id,
        shot_id=materialization.shot_id,
        size_bytes=materialization.size_bytes,
        sha256=materialization.sha256,
    )


def merge_reference_variants(
    store: ProjectStore,
    project_id: str,
    references: tuple[ProjectReference, ...],
    *,
    label: str,
) -> tuple[ProjectReference, ...]:
    """Merge redo/live reference versions without confusing metadata evolution with ABA.

    ProjectReference metadata is allowed to evolve through canonical commands (for
    example ``production.accept_take`` appends ``production_acceptances``). Stable
    ownership identity is the reference ID + path + kind. A Generation reference
    additionally must resolve to the same immutable durable Generation
    materialization authority in every historical variant. Completion/Take authority
    remains a stricter caller-level check where successful Generation is required.
    """

    by_id: dict[str, ProjectReference] = {}
    by_path: dict[str, str] = {}
    generation_by_id: dict[str, GenerationMaterializationAuthority | None] = {}
    merged: list[ProjectReference] = []
    for reference in references:
        try:
            generation_authority = generation_materialization_authority(
                store,
                project_id,
                reference,
            )
        except GenerationReferenceAuthorityError:
            raise

        path_owner = by_path.get(reference.path)
        if path_owner is not None and path_owner != reference.id:
            raise GenerationReferenceAuthorityError(
                f"{label} reference path is ambiguous: {reference.path}"
            )

        existing = by_id.get(reference.id)
        if existing is not None:
            if existing.path != reference.path or existing.kind != reference.kind:
                raise GenerationReferenceAuthorityError(
                    f"{label} reference identity changed path/kind: {reference.id}"
                )
            if generation_by_id[reference.id] != generation_authority:
                raise GenerationReferenceAuthorityError(
                    f"{label} Generation authority changed across history: {reference.id}"
                )
            continue

        by_id[reference.id] = reference
        by_path[reference.path] = reference.id
        generation_by_id[reference.id] = generation_authority
        merged.append(reference)
    return tuple(merged)


def validate_generation_reference_bytes(
    store: ProjectStore,
    project_id: str,
    artifact: ProjectReference,
) -> GenerationReferenceAuthority | None:
    """Validate exact Generation bytes, including bounded incomplete materialization.

    A non-Generation reference returns ``None``. A complete Generation reference
    returns its strict success authority. A recovery-compatible incomplete
    RUNNING/FAILED/CANCELLED materialization also returns ``None`` after its immutable
    Job/Attempt provenance and exact bytes have been proven; callers that require a
    successful Take must separately call ``generation_reference_authority()``.
    """

    materialization = generation_materialization_authority(store, project_id, artifact)
    if materialization is None:
        return None
    try:
        output = store.resolve_project_file(
            project_id,
            artifact.path,
            must_exist=True,
            allowed_roots=("artifacts",),
        )
    except ProjectStoreError as exc:
        raise GenerationReferenceAuthorityError(
            f"Generation reference does not resolve to safe output bytes: {artifact.id}"
        ) from exc
    if output.is_symlink() or not output.is_file():
        raise GenerationReferenceAuthorityError(
            f"Generation reference does not resolve to regular output bytes: {artifact.id}"
        )
    try:
        size = output.stat().st_size
        digest = _sha256_file(output)
    except OSError as exc:
        raise GenerationReferenceAuthorityError(
            f"Generation output bytes are unreadable: {artifact.id}"
        ) from exc
    if size != materialization.size_bytes:
        raise GenerationReferenceAuthorityError(
            f"Generation output size does not match persisted metadata: {artifact.id}"
        )
    if digest != materialization.sha256:
        raise GenerationReferenceAuthorityError(
            f"Generation output digest does not match persisted metadata: {artifact.id}"
        )
    if materialization.attempt_status != "succeeded":
        return None
    return generation_reference_authority(store, project_id, artifact)
