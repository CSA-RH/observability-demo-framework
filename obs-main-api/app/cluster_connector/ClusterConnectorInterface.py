from abc import ABC, abstractmethod
from typing import Dict, List, Any

class ClusterConnectorInterface(ABC):    
    
    @abstractmethod
    def get_cluster_info(self) -> Dict[str, str]: 
        pass 

    @abstractmethod
    async def create_simulation_resources(self, payload: List[Dict[str, Any]]):
        pass 

    @abstractmethod
    def save_simulation(self, json_simulation):
        pass

    @abstractmethod
    def retrieve_simulation(self):
        pass

    @abstractmethod
    async def delete_simulation(self):
        pass

    @abstractmethod
    async def create_alert(self, agent_name, agent_type, metric):
        pass