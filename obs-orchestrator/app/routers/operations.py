from fastapi import APIRouter, Depends, HTTPException  # type: ignore

import dependencies as deps
from auth import get_current_user

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])


@router.get("/{operation_id}")
def get_operation_status(operation_id: str, current_user: dict = Depends(get_current_user)):
    operation = deps.cluster_connector.get_operation(operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="Operation not found")
    return operation
