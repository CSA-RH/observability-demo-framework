from abc import ABC, abstractmethod
from typing import Dict, List, Any

class ClusterConnectorInterface(ABC):    
    
    @abstractmethod
    def get_cluster_info(self, user) -> Dict[str, str]: 
        pass 

    @abstractmethod
    async def create_simulation_resources(self, user, payload: List[Dict[str, Any]]):
        pass 

    @abstractmethod
    def save_simulation(self, user, json_simulation):
        pass

    @abstractmethod
    def retrieve_simulation(self, user):
        pass

    @abstractmethod
    async def delete_simulation(self, user):
        pass    

    @abstractmethod 
    def create_alert_resource(self, user, id, name, severity, group, expression, summary):
        pass       

    @abstractmethod
    def save_alert_definition(self, user, alert):
        pass

    @abstractmethod
    def delete_alert(self, user, alert_name):
        pass

    @abstractmethod
    def delete_alert_definition(self, user, alert_name):
        pass

    @abstractmethod
    def get_alert_definitions(self, user):
        pass
    
    @abstractmethod
    def retrieve_hostname_from_service_id(self, user, id):
        pass