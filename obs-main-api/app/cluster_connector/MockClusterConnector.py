from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict, List, Any
from utils import JSONUtils

import secrets, os, json 

class MockClusterConnector(ClusterConnectorInterface):
    
    PATH_SIMULATION_DEF="/tmp/obs-demo-fw-sim.json"    
    PATH_ALERTS_DEF="/tmp/obs-demo-fw-alerts.json"

    def __init__(self): 
        print("... Starting Mock Cluster connector.")

    def get_cluster_info(self) -> Dict[str, str]:
        return {
            "Connected": True,
            "Name": "Fake Cluster",
            "Namespace": "fake-namespace",
            "ConsoleURL": "https://redhat.com", 
            "apiLogsURL": "https://redhat.com", 
            "JaegerUI": "https://redhat.com"
        }

    def __generate_pod_suffix(self):
        # Generate a random 9-hex character part
        first_part = secrets.token_hex(4)  # 4 bytes -> 8 hex characters
        first_part += secrets.token_hex(1)[0]  # Add 1 more hex character

        # Generate a random 5-hex character part
        second_part = secrets.token_hex(3)[:5]  # 3 bytes -> 6 hex characters, but only take 5

        # Combine the parts with a dash
        pod_suffix = f"{first_part}-{second_part}"
        return pod_suffix
    
    async def create_simulation_resources(self, payload: List[Dict[str, Any]]):
        print("create simulation resources")
        for item in payload:            
                item["ip"] = "1.2.3.4"
                item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()                
        return payload

    def save_simulation(self, json_simulation):
        print("save simulation")
        JSONUtils.save_json_to_file(json_simulation, self.PATH_SIMULATION_DEF)    
    
    def retrieve_simulation(self):
        print("retrieve simulation")
        json_data = JSONUtils.load_json_from_file(self.PATH_SIMULATION_DEF)
        print(json_data)

        if not json_data:
            return {}
        # Add pod name
        for item in json_data["agents"]:            
            item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()

        return json_data
    
    async def delete_simulation(self):
        print("Delete simulation")
        JSONUtils.delete_json_file(self.PATH_ALERTS_DEF)
        JSONUtils.delete_json_file(self.PATH_SIMULATION_DEF)
    
    def create_alert_resource(self, id, name, severity, group, expression, summary):
        print("Mocked alert:")
        print(f"- id:         {id}")
        print(f"- name:       {name}")
        print(f"- severity    {severity}")
        print(f"- group:      {group}")
        print(f"- expression: {expression}")
        print(f"- summary:    {summary}")
        return id   

    
    def save_alert_definition(self, alert):    
        alerts_definition=JSONUtils.load_json_from_file(self.PATH_ALERTS_DEF)
        alerts_definition.append(alert)
        JSONUtils.save_json_to_file(alerts_definition, self.PATH_ALERTS_DEF)
    
    def delete_alert(self, alert_name):
        print("Delete alert in Mock. Nothing to do")
        return {"success": True}

    def delete_alert_definition(self, alert_name):
        alerts = JSONUtils.load_json_from_file(self.PATH_ALERTS_DEF)   
        cleaned_alerts = [item for item in alerts if item.get("id") != alert_name]
        print(cleaned_alerts)
        JSONUtils.save_json_to_file(cleaned_alerts, self.PATH_ALERTS_DEF)
        return {"success": True}

    def get_alert_definitions(self):
        return JSONUtils.load_json_from_file(self.PATH_ALERTS_DEF)
