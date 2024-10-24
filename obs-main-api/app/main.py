from agent_manager.OpenShiftAgentManager         import OpenShiftAgentManager
from agent_manager.MockAgentManager              import MockAgentManager
from cluster_connector.OpenShiftClusterConnector import OpenShiftClusterConnector
from cluster_connector.MockClusterConnector      import MockClusterConnector

from fastapi import FastAPI, HTTPException, Request     # type: ignore
from fastapi.responses import JSONResponse              # type: ignore
from fastapi.middleware.cors import CORSMiddleware      # type: ignore
from typing import List, Dict, Any

import os, types

def is_using_fake_cluster_connector():
    value = os.environ.get('CLUSTER_CONNECTOR')
    if value is None:
        return False
    else:
        return value == 'mock'
    
def is_using_fake_agent_manager():
    value = os.environ.get('AGENT_MANAGER')
    if value is None:
        return False
    else:
        return value == 'mock'

#TODO: Improve security. CORS 
app = FastAPI()
origins = [
#    "http://localhost:3000",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if is_using_fake_cluster_connector():
    cluster_connector = MockClusterConnector()
else:
    cluster_connector = OpenShiftClusterConnector()    

if is_using_fake_agent_manager():
    agent_manager = MockAgentManager()
else:
    agent_manager = OpenShiftAgentManager()

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"Handling exception for request: {request} ")
    return JSONResponse(status_code=500, content={"message": "Internal server error", "details": str(exc)})

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    print(f"Handling HTTP exception for request: {request} ")
    return JSONResponse(status_code=exc.status_code, content={"message": exc.detail})

#TODO: Error handling
@app.get("/info")
async def get_info():
    return cluster_connector.get_cluster_info()

def get_agent_from_payload(name, payload):
    for item in payload:
        if item["group"] == "nodes" and item["data"]["id"] == name:
            return item
    return None

def add_next_hop_to_agent(name, agent):
    if "nextHop" in agent:
        agent["nextHop"].append(name)
    else:
        # If the key doesn't exist, create a new list with the string
        agent["nextHop"] = [name]

@app.post("/simulation")
async def create_simulation(payload: Dict[str, Any]):    
    # Create resources in cluster
    try:        
        json_agents = await cluster_connector.create_simulation_resources(payload["agents"])

    except Exception as e:
        raise HTTPException(status_code=500, detail=e.args)
    
    for source_agent_data in payload["agents"]: 
        for target_agent_id in source_agent_data["nextHop"]:
            agent_manager.set_agent_communication_path(source_agent_data["id"], target_agent_id)

    # Save simulation
    cluster_connector.save_simulation(payload)

    return json_agents

@app.delete("/simulation")
async def delete_simulation():
    await cluster_connector.delete_simulation()

@app.get("/simulation")
async def get_simulation():
    # Get the simulation definition from storage    
    simulation = cluster_connector.retrieve_simulation()    
    if simulation == {}:        
        raise HTTPException(status_code=404, detail="Simulation not found")    
    # Update agent metrics     
    for item in simulation["agents"]:
        id = item["id"]
        metrics = agent_manager.get_agent_metrics(id)
        print(f"Pod: {item["pod"]}. Metrics: {metrics}")        
        item["metrics"] = metrics
    
    return simulation

#TODO: Error handling
@app.post("/kick")
async def agent_kick(payload: dict[str, Any]):    
    return agent_manager.kick(payload)

@app.post("/metrics")
async def create_agent_metric(payload: dict[str, Any]):
    await agent_manager.set_agent_metrics("POST", payload=payload)

@app.put("/metrics")
async def modify_agent_metric(payload: dict[str, Any]):
    await agent_manager.set_agent_metrics("PUT", payload=payload)