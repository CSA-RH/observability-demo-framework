from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict, List, Any
from utils import JSONUtils
from operations.operation_store import new_operation, utc_now_iso

import secrets, os, json 

class MockClusterConnector(ClusterConnectorInterface):
    
    PATH_SIMULATION_DEF="/tmp/obs-demo-fw-sim.json"    
    PATH_ALERTS_DEF="/tmp/obs-demo-fw-alerts.json"
    PATH_USERS_DEF="/tmp/obs-demo-fw-users.json"
    PATH_OPERATIONS_DEF="/tmp/obs-demo-fw-operations.json"

    def __init__(self): 
        print("... Starting Mock Cluster connector.")
        if not os.path.exists(self.PATH_USERS_DEF):
            JSONUtils.save_json_to_file([], self.PATH_USERS_DEF)
        if not os.path.exists(self.PATH_OPERATIONS_DEF):
            JSONUtils.save_json_to_file({}, self.PATH_OPERATIONS_DEF)

    def get_cluster_info(self, user) -> Dict[str, str]:
        return {
            "Connected": True,
            "Name": "Fake Cluster",
            "Namespace": f"fake-namespace-{user}",
            "ConsoleURL": "https://redhat.com", 
            "apiLogsURL": "https://redhat.com", 
            "JaegerUI": "https://redhat.com", 
            "GrafanaURL": "https://ibm.com"
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
    
    async def create_simulation_resources(self, user, payload: List[Dict[str, Any]]):
        print("create simulation resources")
        for item in payload:            
                item["ip"] = "1.2.3.4"
                item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()                
        return payload

    def save_simulation(self, user, json_simulation):
        print("save simulation")
        JSONUtils.save_json_to_file(json_simulation, self.PATH_SIMULATION_DEF)    
    
    def retrieve_simulation(self, user):
        print("retrieve simulation")
        json_data = JSONUtils.load_json_from_file(self.PATH_SIMULATION_DEF)
        print(json_data)

        if not json_data:
            return {}
        # Add pod name
        for item in json_data["agents"]:            
            item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()

        return json_data
    
    async def delete_simulation(self, user):
        print("Delete simulation")
        JSONUtils.delete_json_file(self.PATH_ALERTS_DEF)
        JSONUtils.delete_json_file(self.PATH_SIMULATION_DEF)
    
    def create_alert_resource(self, user, stack, id, name, severity, group, expression, summary):
        print("Mocked alert:")
        print(f"- user:       {user}")
        print(f"- stack:      {stack}")
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

    def get_alert_definitions(self, user):
        return JSONUtils.load_json_from_file(self.PATH_ALERTS_DEF)

    
    def update_users_json(self, users):
        JSONUtils.save_json_to_file(users, self.PATH_USERS_DEF)

    def get_users_json(self):
        return JSONUtils.load_json_from_file(self.PATH_USERS_DEF) or []
    
    def sync_users(self): 
        return True

    def __load_operations(self) -> Dict[str, Any]:
        operations = JSONUtils.load_json_from_file(self.PATH_OPERATIONS_DEF)
        return operations if isinstance(operations, dict) else {}

    def __save_operations(self, operations: Dict[str, Any]):
        JSONUtils.save_json_to_file(operations, self.PATH_OPERATIONS_DEF)

    def create_operation(self, operation_type: str, metadata: Dict[str, Any] | None = None) -> str:
        operations = self.__load_operations()
        operation = new_operation(operation_type, metadata)
        operations[operation["id"]] = operation
        self.__save_operations(operations)
        return operation["id"]

    def get_operation(self, operation_id: str) -> Dict[str, Any] | None:
        return self.__load_operations().get(operation_id)

    def update_operation(
        self,
        operation_id: str,
        status: str | None = None,
        error: str | None = None,
        result: Any = None,
    ):
        operations = self.__load_operations()
        operation = operations.get(operation_id)
        if operation is None:
            raise KeyError(f"Operation '{operation_id}' not found")
        if status is not None:
            operation["status"] = status
        if error is not None:
            operation["error"] = error
        if result is not None:
            operation["result"] = result
        operation["updatedAt"] = utc_now_iso()
        operations[operation_id] = operation
        self.__save_operations(operations)