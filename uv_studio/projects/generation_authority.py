"""Shared durable Generation ProjectReference authority.

Generation output bytes are not part of ProjectUnitOfWork JSON snapshots.  Any
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


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def generation_reference_authority(
    store: ProjectStore,
    project_id: str,
    artifact: ProjectReference,
) -> GenerationReferenceAuthority | None:
    """Validate durable Job/Attempt provenance for one Generation artifact.

    ``None`` means the ProjectReference is not a Generation artifact.  Generation
    references fail closed if any durable identity, request mapping, contract,
    output path, size or digest authority is missing or contradictory.
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
    take_id = attempt.get("take_id")
    if (
        attempt.get("status") != "succeeded"
        or attempt.get("output_reference_id") != artifact.id
        or not isinstance(take_id, str)
        or not take_id
    ):
        raise GenerationReferenceAuthorityError(
            f"Generation materialization is not durably complete: {artifact.id}"
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

    expected_name = f"generated_{attempt_id}"
    artifact_name = PurePosixPath(artifact.path).name
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

    return GenerationReferenceAuthority(
        job_id=job_id,
        attempt_id=attempt_id,
        take_id=take_id,
        shot_id=shot_id,
        size_bytes=size_bytes,
        sha256=sha256,
    )


def validate_generation_reference_bytes(
    store: ProjectStore,
    project_id: str,
    artifact: ProjectReference,
) -> GenerationReferenceAuthority | None:
    """Validate Generation provenance and the exact currently stored output bytes."""

    authority = generation_reference_authority(store, project_id, artifact)
    if authority is None:
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
    if size != authority.size_bytes:
        raise GenerationReferenceAuthorityError(
            f"Generation output size does not match persisted metadata: {artifact.id}"
        )
    if digest != authority.sha256:
        raise GenerationReferenceAuthorityError(
            f"Generation output digest does not match persisted metadata: {artifact.id}"
        )
    return authority
