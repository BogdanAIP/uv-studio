from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from uv_studio.api.projects import get_project_store
from uv_studio.projects.dubbing_review import DubbingReviewStore
from uv_studio.projects.dubbing_review_current import CurrentReviewStore
from uv_studio.projects.store import ProjectNotFound, ProjectStore

router = APIRouter(prefix="/api/uv/projects", tags=["UV Studio Dubbing Review"])


@router.get("/{project_id}/dubbing-reviews/current")
def current_dubbing_reviews(project_id: str, store: ProjectStore = Depends(get_project_store)) -> dict:
    try:
        history = DubbingReviewStore(store).load_reviews(project_id)
        pointers = CurrentReviewStore(store)
        current: dict[str, str] = {}
        ambiguous: list[str] = []
        for take_id in sorted({item.take_id for item in history.reviews}):
            review_id = pointers.resolve_current(project_id, take_id, history.reviews)
            if review_id is None:
                ambiguous.append(take_id)
            else:
                current[take_id] = review_id
        return {"current_by_take": current, "ambiguous_legacy_take_ids": ambiguous}
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
