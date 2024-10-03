from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any
import urllib.parse

class MockAgentManager(AgentManagerInterface):

    def __init__(self):
        print("... Starting Mock Agent Manager")
        self.agent_metrics = {}

    def get_agent_metrics(self, id):
        if id in self.agent_metrics: 
            return self.agent_metrics[id]['metrics']
        else:
            return []    
    
    async def set_agent_metrics(self, method: str, payload: dict[str, Any]):
        print(f"Method: {method}")
        print(payload)
        print("-------")
    
        full_path = ""
        try:
            agent_ip = payload['ip']
            agent_id = payload['id']
            metricInfo = payload['metric']

            path = "/metrics/" + metricInfo['name']
            params = {
                "name": metricInfo['name'],
                "value": metricInfo['value']
            }
            
            query_string = urllib.parse.urlencode(params)

            full_path = f"{path}?{query_string}"        
        except Exception as e:
            # General exception handler for other potential errors
            print(f"An error occurred: {e}")
            
        print(f"Agent {agent_id}. Setting metric {metricInfo['name']}[{method}]")

        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = {
                'name': agent_id,
                'ip': agent_ip, 
                'metrics': []
            }
        agent = self.agent_metrics[agent_id]
        updated = False
        for metric in agent['metrics']:
            if metric["name"] == metricInfo["name"]:
                metric['value'] = metricInfo['value']
                updated = True
                break
        if not updated: 
            agent['metrics'].append(metricInfo)
        
    def kick(self, payload: dict[str, Any]):
        print("Kick")
        print(payload)
        print("-------")
    
    def set_agent_communication_path(self, sourceAgent, targetAgent):
        print(f"Source: {sourceAgent}")
        print(f"Target: {targetAgent}")
        print("-------")
        return  