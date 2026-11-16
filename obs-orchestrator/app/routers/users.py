import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

import dependencies as deps
from auth import get_current_user
from operations.operation_tasks import run_user_create, run_user_delete
from validators import validate_username

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("")
def get_users(current_user: dict = Depends(get_current_user)):
    return deps.cluster_connector.get_users_json()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def post_user(
    user_payload: dict[str, Any],
    current_user: dict = Depends(get_current_user),
):
    username_error = validate_username(user_payload.get("username"))
    if username_error:
        raise HTTPException(status_code=400, detail=username_error)

    operation_id = deps.cluster_connector.create_operation(
        "user-create",
        {"username": user_payload.get("username")},
    )
    asyncio.create_task(run_user_create(deps.cluster_connector, operation_id, user_payload))
    return {"operationId": operation_id, "status": "pending"}


@router.delete("/{user_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not user_id:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    operation_id = deps.cluster_connector.create_operation(
        "user-delete",
        {"username": user_id},
    )
    asyncio.create_task(run_user_delete(deps.cluster_connector, operation_id, user_id))
    return {"operationId": operation_id, "status": "pending"}
