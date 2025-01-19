from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any
import urllib.parse
from utils import JSONUtils

class MockAgentManager(AgentManagerInterface):

    PATH_METRICS_DEF="/tmp/obs-demo-fw-metrics.json"

    def __init__(self):
        print("... Starting Mock Agent Manager")
        self.agent_metrics = {}
        self.agent_next_hops = {}
        #Loading metrics
        self.__load_metrics()        
        if id in self.agent_metrics:        
            print("------> " + id) 
    
    def get_agent_metrics(self, id):
        print("--Metrics")
        print("  " + id)
        print(self.agent_metrics.get(id, [])) 
        print("---------")        
        if id in self.agent_metrics:             
            return self.agent_metrics[id]['metrics']
        
        else:
            return []
    
    def __load_metrics(self):
        metrics_json = JSONUtils.load_json_from_file(self.PATH_METRICS_DEF)
        print(metrics_json)
        for item in metrics_json: 
            self.agent_metrics[item["name"]] = item["data"]

    def __save_metrics(self, dict_metrics): 
        print(dict_metrics)
        agent_list=[]
        for agent_name, agent_data in dict_metrics.items():
            agent_info={}
            agent_info['name']=agent_name
            agent_info['data'] = agent_data
            agent_list.append(agent_info)
        JSONUtils.save_json_to_file(agent_list, self.PATH_METRICS_DEF)           
    
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
                if metricInfo['alert']:
                    metric['alert'] = metricInfo['alert']
                updated = True
                break
        if not updated: 
            agent['metrics'].append(metricInfo)
        self.__save_metrics(self.agent_metrics)        
        
    def kick(self, payload: dict[str, Any]):
        print("Kick")
        print(payload)
        print("-------")
    
    def set_agent_communication_path(self, source_agent, target_agent):
        print(f"Source: {source_agent}")
        print(f"Target: {target_agent}")
        print("-------")
        
        # Create source entry if not created
        if source_agent not in self.agent_next_hops:
            self.agent_next_hops[source_agent] = []
        # Add target agent to next hops
        self.agent_next_hops[source_agent].append(target_agent) 
        return
    
    def delete_metrics_definitions(self):
        JSONUtils.delete_json_file(self.PATH_METRICS_DEF)