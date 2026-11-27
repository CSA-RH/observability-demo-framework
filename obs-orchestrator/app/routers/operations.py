from fastapi import APIRouter, Depends, HTTPException  # type: ignore

import dependencies as deps
from auth import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


def _visible_to(operation: dict, current_user: CurrentUser) -> bool:
    """Admins see every operation; users only their own simulation operations (`userId`).
    User management operations (`user-create`, `user-delete`) are admin-only."""
    if current_user.is_admin:
        return True
    owner = (operation.get("metadata") or {}).get("userId")
    return owner is not None and owner == current_user.username


@router.get("/{operation_id}")
def get_operation_status(operation_id: str, current_user: CurrentUser = Depends(get_current_user)):
    operation = deps.operations.get(operation_id)
    # Someone else's operation is reported as missing: operation ids are not leaked.
    if operation is None or not _visible_to(operation, current_user):
        raise HTTPException(status_code=404, detail="Operation not found")
    return operation
