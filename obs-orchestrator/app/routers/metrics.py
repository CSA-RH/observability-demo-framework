import inspect
from typing import Any

from fastapi import APIRouter, Depends, HTTPException  # type: ignore

import dependencies as deps
from agent_manager.OpenShiftAgentManager import AgentRequestError
from auth import get_current_user
from models import AgentMetric

router = APIRouter(prefix="/api/v1/users/{user_id}/simulation/metrics", tags=["metrics"])


async def _invoke_set_agent_metrics(method: str, user_id: str, payload: dict[str, Any]):
    result = deps.agent_manager.set_agent_metrics(method, user_id, payload=payload)
    if inspect.isawaitable(result):
        result = await result
    return result


@router.post("")
async def create_agent_metric(user_id: str, metric: AgentMetric, current_user: dict = Depends(get_current_user)):
    try:
        message = await _invoke_set_agent_metrics("POST", user_id, metric.to_dict())
        return {"message": message or "Metric created"}
    except AgentRequestError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.put("")
async def modify_agent_metric(user_id: str, metric: AgentMetric, current_user: dict = Depends(get_current_user)):
    try:
        message = await _invoke_set_agent_metrics("PUT", user_id, metric.to_dict())
        return {"message": message or "Metric updated"}
    except AgentRequestError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
