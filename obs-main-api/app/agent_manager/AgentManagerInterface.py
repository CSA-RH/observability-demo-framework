from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AgentManagerInterface(ABC): 

    @abstractmethod
    def get_agent_metrics(self, user_id, id): 
        pass

    @abstractmethod 
    async def set_agent_metrics(self, method: str, user: str, payload: dict[str, Any]):
        pass

    @abstractmethod
    def kick(self, user_id, agent_id, agent_dns, kick_initial_count):
        pass

    @abstractmethod
    def set_agent_communication_path(self, user_id: str, sourceAgent, targetAgent):
        pass

    @abstractmethod
    def delete_metrics_definitions(self, user_id: str):
        pass