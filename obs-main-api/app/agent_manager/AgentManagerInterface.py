from abc import ABC, abstractmethod
from typing import List, Dict, Any

class AgentManagerInterface(ABC): 

    @abstractmethod
    def get_agent_metrics(self, id): 
        pass

    @abstractmethod 
    async def set_agent_metrics(self, method: str, payload: dict[str, Any]):
        pass

    @abstractmethod
    def kick(self, payload: dict[str, Any]):
        pass