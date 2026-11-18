import asyncio

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

import dependencies as deps
from auth import get_current_user
from models import UserCreate
from operations.operation_tasks import run_user_create, run_user_delete
from validators import validate_username

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _find_user(username: str):
    return next((u for u in deps.tenants.get_users() if u.get("username") == username), None)


@router.get("")
def get_users(current_user: dict = Depends(get_current_user)):
    return deps.tenants.get_users()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def post_user(
    user: UserCreate,
    current_user: dict = Depends(get_current_user),
):
    username_error = validate_username(user.username)
    if username_error:
        raise HTTPException(status_code=400, detail=username_error)
    if _find_user(user.username) is not None:
        raise HTTPException(status_code=409, detail=f"User {user.username} already exists")
    user_payload = user.to_dict()

    operation_id = deps.operations.create(
        "user-create",
        {"username": user.username},
    )
    asyncio.create_task(run_user_create(deps.operations, deps.tenants, operation_id, user_payload))
    return {"operationId": operation_id, "status": "pending"}


@router.delete("/{user_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    if _find_user(user_id) is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")

    operation_id = deps.operations.create(
        "user-delete",
        {"username": user_id},
    )
    asyncio.create_task(run_user_delete(deps.operations, deps.tenants, operation_id, user_id))
    return {"operationId": operation_id, "status": "pending"}
