from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict

class MockClusterConnector(ClusterConnectorInterface):
    
    def load_kube_config(self):
        print("")
    
    def get_current_namespace(self) -> str: 
        print("")

    def get_console_info(self) -> Dict[str, str]:
        print("")