from abc import ABC, abstractmethod
from typing import Dict

class ClusterConnectorInterface(ABC): 

    @abstractmethod
    def load_kube_config(self):
        pass

    @abstractmethod
    def get_current_namespace(self) -> str: 
        pass

    @abstractmethod
    def get_console_info(self) -> Dict[str, str]:
        pass
