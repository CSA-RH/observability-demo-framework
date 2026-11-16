import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status  # type: ignore

import dependencies as deps
from auth import get_current_user
from models import AgentKick, SimulationCreate
from operations.operation_tasks import run_simulation_create, run_simulation_delete

router = APIRouter(prefix="/api/v1/users/{user_id}/simulation", tags=["simulation"])


@router.get("")
async def get_simulation(user_id: str, current_user: dict = Depends(get_current_user)
):
    print(f"Received user from path: {user_id}")
    #TODO: REMOVE GNAPA: 
    user = user_id.removeprefix("obs-demo-")
    # Get the simulation definition from storage    
    simulation = deps.cluster_connector.retrieve_simulation(user)    
    if simulation == {}:        
        raise HTTPException(status_code=404, detail="Simulation not found")    
    # Update agent metrics     
    for item in simulation["agents"]:
        id = item["id"]
        metrics = deps.agent_manager.get_agent_metrics(
            user_id, 
            deps.cluster_connector.retrieve_hostname_from_service_id(user, id))
        for metric in metrics:
            metric["alerts"] = []
        print(f"Pod: {item['pod']}. Metrics: {metrics}")        
        item["metrics"] = metrics
    # Update alerts of the metrics.
    alerts = deps.cluster_connector.get_alert_definitions(user) 
    for alert in alerts:
        if alert["scope"] != "metricAgent":
            continue
        agent_matches = [agent for agent in simulation["agents"] if agent["id"] == alert["definition"]["agent"]]
        agent = agent_matches[0] if agent_matches else None
        if agent is None: 
            print(f"WARNING[alerts]: Agent {alert['definition']['agent']} Not found")
            continue
        metric_matches = [metric for metric in agent["metrics"] if metric["name"] == alert["definition"]["metric"]]
        metric = metric_matches[0] if metric_matches else None
        if metric is None or metric is []: 
            print(f"WARNING[alerts]: Metric {alert['definition']['metric']} for the agent {agent['id']} not found")
            continue
        # Check if the alert is already present.
        alert_matches_in_metric = [item for item in metric.get("alerts", []) if item["name"] == alert["name"]]
        alert_match = alert_matches_in_metric[0] if alert_matches_in_metric and len(alert_matches_in_metric) > 0 else None
        # If not, add to the definitions
        if alert_match is None:
            metric.setdefault("alerts", []).append(alert)
    
    return simulation

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_simulation(
    user_id: str,
    simulation: SimulationCreate,
    current_user: dict = Depends(get_current_user),
):
    payload = simulation.to_dict()
    operation_id = deps.cluster_connector.create_operation(
        "simulation-create",
        {"userId": user_id},
    )
    asyncio.create_task(run_simulation_create(deps.cluster_connector, operation_id, user_id, payload))
    return {"operationId": operation_id, "status": "pending"}

@router.delete("", status_code=status.HTTP_202_ACCEPTED)
async def delete_simulation(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    operation_id = deps.cluster_connector.create_operation(
        "simulation-delete",
        {"userId": user_id},
    )
    asyncio.create_task(run_simulation_delete(deps.cluster_connector, operation_id, user_id, deps.agent_manager))
    return {"operationId": operation_id, "status": "pending"}

@router.post("/kick/{agent_id}")
async def agent_kick(user_id: str, agent_id: str, kick: AgentKick, current_user: dict = Depends(get_current_user)):
    print(f"DNS: {kick.dns}")
    return deps.agent_manager.kick(user_id, agent_id, kick.dns, kick.count)
