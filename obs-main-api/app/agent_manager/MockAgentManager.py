from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any
import urllib.parse
from utils import JSONUtils

class MockAgentManager(AgentManagerInterface):

    PATH_METRICS_DEF="/tmp/obs-demo-fw-metrics.json"
    ROOT_METRICS_DIR="/tmp"
    METRICS_FILE_SUFFIX="obs-demo-fw-metrics.json"

    def __init__(self):
        print("... Starting Mock Agent Manager")
        self.next_hops = {}
    
    def __get_metrics_fullpath_file(self, user_id):
        return f"{self.ROOT_METRICS_DIR}/{user_id}-{self.METRICS_FILE_SUFFIX}"
    
    def __load_metrics(self, user_id):
        metrics_json = JSONUtils.load_json_from_file(self.__get_metrics_fullpath_file(user_id))
        agent_metrics = {}
        for item in metrics_json: 
            agent_metrics[item["name"]] = item["data"]
        print(agent_metrics)
        return agent_metrics
    
    def get_agent_metrics(self, user_id, id):
        agent_metrics = self.__load_metrics(user_id)
        print(f"AGENT METRICS FOR USER {user_id} - AGENT {id}")
        print("-----------------------------------------------")
        print(agent_metrics)
        print("-----------------------------------------------")
        agent_id = id.split('.')[0]
        if agent_id in agent_metrics:             
            return agent_metrics[agent_id]['metrics']
        else:
            return []

    def __save_metrics(self, user_id, dict_metrics):         
        agent_list=[]
        for agent_name, agent_data in dict_metrics.items():
            agent_info={}
            agent_info['name']=agent_name
            agent_info['data'] = agent_data
            agent_list.append(agent_info)
        JSONUtils.save_json_to_file(agent_list, self.__get_metrics_fullpath_file(user_id))
    
    async def set_agent_metrics(self, method: str, user: str, payload: dict[str, Any]):
        print(f"Method: {method}")
        print(f"User:   {user}")
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
        agent_metrics = self.__load_metrics(user)
        if agent_id not in agent_metrics:
            agent_metrics[agent_id] = {
                'name': agent_id,
                'ip': agent_ip, 
                'metrics': []
            }        
        agent = agent_metrics[agent_id]
        updated = False
        for metric in agent['metrics']:
            if metric["name"] == metricInfo["name"]:
                metric['value'] = metricInfo['value']
                if metricInfo.get('alerts'):
                    metric['alerts'] = metricInfo['alerts']
                updated = True
                break
        if not updated: 
            agent['metrics'].append(metricInfo)
        self.__save_metrics(user, agent_metrics)        
        
    def kick(self, user_id, agent_ip, agent_id: str, kick_initial_count: int):
        print("Kick")
        print(f"From user: {user_id} - Target agent: {agent_id}. IP: {agent_ip}. Count={kick_initial_count}")
        print("-------")
    
    def set_agent_communication_path(self, user_id, source_agent, target_agent):
        print(f"Source: {source_agent}")
        print(f"Target: {target_agent}")
        print("-------")
        
        # Create source entry if not created
        if user_id not in self.next_hops:
            self.next_hops[user_id] = []
        
        if source_agent not in self.next_hops[user_id]:
            self.next_hops[user_id][source_agent] = []
        # Add target agent to next hops
        self.next_hops[user_id][source_agent].append(target_agent) 
        return
    
    async def delete_metrics_definitions(self, user_id):
        metrics_file = self.__get_metrics_fullpath_file(user_id)
        JSONUtils.delete_json_file(metrics_file)