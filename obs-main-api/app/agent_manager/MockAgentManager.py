from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any
import urllib.parse
from utils import JSONUtils
import fcntl
import json
import random

class MockAgentManager(AgentManagerInterface):

    ROOT_METRICS_DIR="/tmp"
    METRICS_FILE_SUFFIX="obs-demo-fw-metrics.json"
    COMMS_FILE_SUFFIX="obs-demo-fw-comms.json"

    def __init__(self):
        print("... Starting Mock Agent Manager")
    
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
    
    def set_agent_communication_path(self, user_id, source_agent_dns, target_agent):
        """
        Retrieves the current communication graph for a user from a file,
        adds a new path, and saves it back to the file.
        
        The data is stored in: /tmp/{user_id}-obs-demo-fw-comms.json
        """
        
        # Define the user-specific file path
        file_path = f"/tmp/{user_id}-obs-demo-fw-comms.json"
        
        source_agent = source_agent_dns.split('.')[0]
        print(f"Reading/Writing communications for {user_id} at {file_path}")
        print(f"Source: {source_agent}")
        print(f"Target: {target_agent}")
        print("-------")

        user_comms = {}

        try:
            # Open the file in 'a+' mode:
            # 'a': Append mode (creates file if it doesn't exist)
            # '+': Allows reading as well
            with open(file_path, 'a+') as f:
                
                # --- 1. Acquire Lock ---
                # Acquire an exclusive lock on the file.
                # If another process is writing, this line will wait.
                # This prevents race conditions.
                fcntl.flock(f, fcntl.LOCK_EX)

                # --- 2. Read Data ---
                # 'a+' starts the pointer at the end, so seek to the beginning
                f.seek(0)
                try:
                    # Try to load the JSON data
                    user_comms = json.load(f)
                except json.JSONDecodeError:
                    # File was empty or corrupt, start with a new dict
                    print(f"File was empty or corrupt. Starting fresh for {user_id}.")
                    user_comms = {}

                # --- 3. Modify Data ---
                # This is your original logic, applied to the data from the file
                
                # Create source entry if not created
                if source_agent not in user_comms:
                    user_comms[source_agent] = []
                
                # Add target agent to next hops (checking for duplicates)
                if target_agent not in user_comms[source_agent]:
                    user_comms[source_agent].append(target_agent)
                else:
                    print(f"Target {target_agent} already exists for {source_agent}.")

                # --- 4. Write Data ---
                # Go back to the beginning to overwrite the entire file
                f.seek(0)
                # Clear the file's contents
                f.truncate()
                # Dump the updated dictionary back as pretty JSON
                json.dump(user_comms, f, indent=4)

                # --- 5. Release Lock ---
                # The lock is automatically released when the 'with' block ends,
                # but fcntl.flock(f, fcntl.LOCK_UN) could also be called.
        except (IOError, PermissionError) as e:
            print(f"CRITICAL ERROR: Could not read or write to file {file_path}. Error: {e}")
            # You might want to re-raise the exception to stop the operation
            raise
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise
        return
    
    def kick(self, user_id, agent_id, agent_dns: str, kick_initial_count: int):
        """
        Performs a random traversal of the communication graph for a user.
        It loads the graph from /tmp/{user_id}-obs-demo-fw-comms.json.
        """
        print("Kick")
        print(f"From user: {user_id} - Starting at agent: {agent_id}. DNS: {agent_dns}. Max steps={kick_initial_count}")
        print("-------")

        # --- 1. Load the communication graph from the file ---
        file_path = f"/tmp/{user_id}-obs-demo-fw-comms.json"
        user_comms = {}
        try:
            # Open for reading ('r')
            with open(file_path, 'r') as f:
                # Acquire a shared lock (LOCK_SH) for safe reading
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    user_comms = json.load(f)
                except json.JSONDecodeError:
                    print(f"Could not parse JSON from {file_path}. Assuming no comms.")
                    user_comms = {}
                # Lock is released automatically when 'with' block ends
        except FileNotFoundError:
            print(f"Communication file {file_path} not found. No next hops available.")
            user_comms = {}
        except (IOError, PermissionError) as e:
            print(f"CRITICAL ERROR: Could not read file {file_path}. Error: {e}")
            raise # Re-raise to stop execution
        except Exception as e:
            print(f"An unexpected error occurred while reading file: {e}")
            raise

        # --- 2. Initialize traversal state ---
        count = kick_initial_count
        current_agent = agent_id

        # --- 3. Start the traversal loop ---
        while (count > 0):
            print(f"--- Step (Remaining: {count}) ---")
            
            # Get the list of next hops for the current agent
            # .get() is safer than direct access, returns [] if current_agent has no entry
            next_hops_list = user_comms.get(current_agent, [])
            
            print(f"  Current agent: {current_agent}")
            print(f"  Next hops available: {next_hops_list}")

            if next_hops_list:
                # A. Hops are available: choose one and continue
                chosen_next_agent = random.choice(next_hops_list)
                print(f"  Decision: Randomly chose {chosen_next_agent}")
                
                # Update the current agent for the *next* iteration
                current_agent = chosen_next_agent
            
            else:
                # B. No hops available: stop the traversal
                print("  Decision: No next hops available from this agent. Traversal stops.")
                break # Exit the while loop
            
            # Decrement the count for the next loop
            count = count - 1

        print("-------")
        print("Kick simulation finished.")
        return
    
    async def delete_metrics_definitions(self, user_id):
        metrics_file = self.__get_metrics_fullpath_file(user_id)
        JSONUtils.delete_json_file(metrics_file)
        JSONUtils.delete_json_file(f"/tmp/{user_id}-obs-demo-fw-comms.json")