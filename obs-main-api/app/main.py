from agent_manager.OpenShiftAgentManager         import OpenShiftAgentManager
from agent_manager.MockAgentManager              import MockAgentManager
from cluster_connector.OpenShiftClusterConnector import OpenShiftClusterConnector
from cluster_connector.MockClusterConnector      import MockClusterConnector

from fastapi import FastAPI, HTTPException, Request     # type: ignore
from fastapi.responses import JSONResponse              # type: ignore
from fastapi.middleware.cors import CORSMiddleware      # type: ignore
from typing import List, Dict, Any

import os
from utils import JSONUtils


from pprint import pprint

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
    agent_manager.delete_metrics_definitions()    

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
        for metric in metrics:
            metric["alerts"] = []
        print(f"Pod: {item["pod"]}. Metrics: {metrics}")        
        item["metrics"] = metrics
    # Update alerts of the metrics.
    alerts = cluster_connector.get_alert_definitions() 
    for alert in alerts:
        if alert["scope"] != "metricAgent":
            continue
        agent_matches = [agent for agent in simulation["agents"] if agent["id"] == alert["definition"]["agent"]]
        agent = agent_matches[0] if agent_matches else None
        if agent is None: 
            print(f"WARNING[alerts]: Agent {alert["definition"]["agent"]} Not found")
            continue
        metric_matches = [metric for metric in agent["metrics"] if metric["name"] == alert["definition"]["metric"]]
        metric = metric_matches[0] if metric_matches else None
        if metric is None or metric is []: 
            print(f"WARNING[alerts]: Metric {alert["definition"]["metric"]} for the agent {agent["id"]} not found")
            continue
        # Check if the alert is already present.
        alert_matches_in_metric = [item for item in metric.get("alerts", []) if item["name"] == alert["name"]]
        alert_match = alert_matches_in_metric[0] if alert_matches_in_metric and len(alert_matches_in_metric) > 0 else None
        # If not, add to the definitions
        if alert_match is None:
            metric.setdefault("alerts", []).append(alert)
    
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

def __map_expression_to_alert(expression):
    """
    Maps a comparison expression to a semantic alert label.

    :param expression: A string representing the comparison operator 
                    (e.g., "<", "<=", "!=", ">", ">=").
    :return: A string representing the semantic alert label.
    """
    mapping = {
        "<": "StrictlyTooLow",
        "≤": "TooLow",
        ">": "StrictlyTooHigh",
        "≥": "TooHigh",
        "≠": "Distinct",
        "=": "Equals",
    }
    
    return mapping.get(expression, "Unknown")

def __map_expression_operator_to_comparison_operator(expression_operator):
    mapping = {
        "<": "<",
        "≤": "<=",
        ">": ">",
        "≥": ">=",
        "≠": "!=",
        "=": "==",
    }
    return mapping.get(expression_operator, "Unknown")

def __extract_alert_details(alert_data):
    definition = alert_data['definition']
    agent_name = definition['agent']
    metric_name = definition['metric']
    expression_operator = definition['expression']
    semantic_expression_label = __map_expression_to_alert(expression_operator)
    return agent_name, metric_name, semantic_expression_label

def __get_alert_name(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = __extract_alert_details(alert_data)
        return f"{agent_name}_{metric_name}_{semantic_expression_label}"
    else:
        return alert_data['name']

def __get_alert_id(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = __extract_alert_details(alert_data)
        alert_id = f"{agent_name}_{metric_name}_{semantic_expression_label}_{alert_data['scope']}"
        return alert_id.replace("_", "-").lower()
    else:
        return f"{alert_data['name']}_{alert_data['scope']}".replace("_", "-").lower()

def __get_alert_summary(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, semantic_expression_label = __extract_alert_details(alert_data)
        alert_name = f"{agent_name}_{metric_name}_{semantic_expression_label}"
        return f"Alert {alert_name} {semantic_expression_label} on {agent_name}"
    else:
        return alert_data['definition']['summary']    

def __get_alert_expression(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, metric_name, _ = __extract_alert_details(alert_data)
        threshold = alert_data['definition']['value']
        comparison_operator = __map_expression_operator_to_comparison_operator(alert_data['definition']['expression'])
        return f"{metric_name}{{job=\"{agent_name}\"}}{comparison_operator}{threshold}"
    else:
        return alert_data['definition']['expression']
    
def __get_alert_group(alert_data):
    if alert_data['scope'] == "metricAgent":
        agent_name, _, _ = __extract_alert_details(alert_data)
        return agent_name
    else:
        return "custom"
    

@app.post("/alerts")
async def create_alert(payload: dict[str, Any]):
    print("Creating alert: ")   
    
    #Create the alert in the cluster
    scope = payload['scope']
    severity = payload['severity']
    definition= payload['definition']
    print("Alert information: ")
    print(f" - Alert scope: {scope}.")
    print(f" - Severity: {severity}")
    print(" - Alert Definition:")
    print(definition)
    print(" ****** ")
    
    alert_id = __get_alert_id(payload)             
    alert_name = __get_alert_name(payload)  
    group = __get_alert_group(payload)
    summary = __get_alert_summary(payload)  
    expression = __get_alert_expression(payload)
        
    result = cluster_connector.create_alert_resource(alert_id, alert_name, severity, group, expression, summary)
    if result is None: 
        raise HTTPException(status_code=400, detail="Error creating resource in the cluster. See logs for more information.")
    print("-----")
    print(result)
    print("-----")

    #Persist alert definition 
    #TODO: Error handling (HTTP 400, 409, 422)
    payload['id'] = alert_id
    payload['name'] = alert_name
    cluster_connector.save_alert_definition(payload)

    response_data = {
        "id": alert_id,
        "name": alert_name
    }
    return JSONResponse(content=response_data)
    
def print_red(str):
    print(f"\033[91m{str}\033[0m")

def __print_exception(e):
    print_red("ERROR INFORMATION:")
    print(f"- HTTP status: {e.status}")
    print(f"- Reason: {e.reason} ")
    print("- Body: -->>>")
    JSONUtils.print_pretty_json(e.body)
    print("<<<--")
    print_red("\033[91m-----\033[0m")

@app.delete("/alerts")
def delete_alert(payload: dict[str, Any]):
    alert_name=payload['alert']
    print(f"Delete alert: {alert_name}")
    
    #Delete alert from the cluster
    #TODO: Error handling (HTTP 400, 404)
    errors = ""
    resource_deletion_result = cluster_connector.delete_alert(alert_name)
    if not resource_deletion_result['success']:
        errors += "Error deleting OpenShift alert resource. "                
        __print_exception(resource_deletion_result['error'])
    definition_deletion_result = cluster_connector.delete_alert_definition(alert_name)
    if not definition_deletion_result['success']:
        errors += "Error deleting OpenShift alert definition. "        
        __print_exception(definition_deletion_result["error"])
    
    if errors != "":
        raise HTTPException(status_code=400, detail=errors)

    return None

@app.get("/alerts")
def get_alerts():
    alerts = []
    alert_data=cluster_connector.get_alert_definitions()    
    for alert in alert_data:
        alerts.append({
            "id": alert['id'],
            "name":  alert['name'], 
            "severity": alert['severity'], 
            "scope": alert['scope'], 
            "evaluation": "1m", 
            "promQL": __get_alert_expression(alert), 
            "summary": __get_alert_summary(alert)
        })
    return alerts


from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import jwt
from jose.exceptions import JWTError
import requests
from typing import Dict

# Keycloak Configuration
KEYCLOAK_ISSUER = "http://127.0.0.1:8080/realms/csa"
KEYCLOAK_AUDIENCE = "account"
KEYCLOAK_CERTS_URL = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

# Security Dependency
security = HTTPBearer()

# Fetch Keycloak Public Keys
def get_public_key(kid: str):
    try:
        response = requests.get(KEYCLOAK_CERTS_URL)
        response.raise_for_status()
        jwks = response.json()
        for key in jwks["keys"]:
            if key["kid"] == kid:
                # Return the key directly (RSA public key in JSON Web Key format)
                return key
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching public keys: {e}")
    raise HTTPException(status_code=401, detail="Public key not found")

# Decode and Verify JWT
def decode_token(token: str) -> Dict:
    try:
        # Get the unverified header to extract 'kid'
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="Token header missing 'kid'")
        
        # Fetch the public key from Keycloak using 'kid'
        public_key = get_public_key(kid)

        # Decode the token using the public key
        payload = jwt.decode(
            token,
            public_key,  # This is now the public key directly, no need for from_jwk
            algorithms=["RS256"],
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Error decoding token: {e}")

# Dependency for Secured Endpoints
def get_current_user(authorization: str = Depends(security)):
    try:
        token = authorization.credentials
        return decode_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unauthorized: {e}")

# Example Endpoints
app = FastAPI()

@app.get("/secured")
async def secured_endpoint(current_user: dict = Depends(get_current_user)):
    return {"message": "Welcome to the secured endpoint!", "user": current_user}

@app.get("/public")
async def public_endpoint():
    return {"message": "Welcome to the public endpoint!"}
