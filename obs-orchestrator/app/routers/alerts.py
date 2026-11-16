import logging

from fastapi import APIRouter, Depends, HTTPException  # type: ignore
from fastapi.responses import JSONResponse  # type: ignore

import alert_rules
import dependencies as deps
from auth import get_current_user
from models import AlertCreate
from utils import print_exception

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users/{user_id}/simulation/alerts", tags=["alerts"])


@router.post("")
async def create_alert(user_id: str, alert: AlertCreate, current_user: dict = Depends(get_current_user)):
    payload = alert.to_dict()
    log.info("Creating alert: ")   
    
    #Create the alert in the cluster
    scope = payload['scope']
    severity = payload['severity']
    definition= payload['definition']
    stack = payload['observabilityStack']
    log.info("Alert information: ")
    log.info(f" - Stack: {stack}")
    log.info(f" - Alert scope: {scope}.")
    log.info(f" - Severity: {severity}")
    log.info(" - Alert Definition:")
    log.debug(definition)
    
    alert_id = alert_rules.get_alert_id(payload)             
    alert_name = alert_rules.get_alert_name(payload)  
    group = alert_rules.get_alert_group(payload)
    summary = alert_rules.get_alert_summary(payload)  
    expression = alert_rules.get_alert_expression(payload)
        
    result = deps.cluster_connector.create_alert_resource(user_id, stack, alert_id, alert_name, severity, group, expression, summary)
    if result is None: 
        raise HTTPException(status_code=400, detail="Error creating resource in the cluster. See logs for more information.")
    log.debug(result)

    #Persist alert definition 
    #TODO: Error handling (HTTP 400, 409, 422)
    payload['id'] = alert_id
    payload['name'] = alert_name
    deps.cluster_connector.save_alert_definition(user_id, payload)

    response_data = {
        "id": alert_id,
        "name": alert_name
    }
    return JSONResponse(content=response_data)
    
@router.delete("/{alert_id}")
def delete_alert(user_id, alert_id: str, current_user: dict = Depends(get_current_user)):
    alert_name=alert_id
    log.info(f"Delete alert: {alert_name}")
    
    #Delete alert from the cluster
    #TODO: Error handling (HTTP 400, 404)
    errors = ""
    resource_deletion_result = deps.cluster_connector.delete_alert(user_id, alert_name)
    if not resource_deletion_result['success']:
        errors += "Error deleting OpenShift alert resource. "                
        print_exception(resource_deletion_result['error'])
    definition_deletion_result = deps.cluster_connector.delete_alert_definition(user_id, alert_name)
    if not definition_deletion_result['success']:
        errors += "Error deleting OpenShift alert definition. "        
        print_exception(definition_deletion_result["error"])
    
    if errors != "":
        raise HTTPException(status_code=400, detail=errors)

    return None

@router.get("")
def get_alerts(user_id: str, current_user: dict = Depends(get_current_user)):
    alerts = []
    alert_data=deps.cluster_connector.get_alert_definitions(user_id)
    for alert in alert_data:
        alerts.append({
            "id": alert['id'],
            "name":  alert['name'], 
            "severity": alert['severity'], 
            "scope": alert['scope'], 
            "evaluation": "1m", 
            "promQL": alert_rules.get_alert_expression(alert), 
            "summary": alert_rules.get_alert_summary(alert)
        })
    return alerts
