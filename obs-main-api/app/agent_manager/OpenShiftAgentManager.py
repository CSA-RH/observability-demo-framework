import http.client
import urllib.parse
import json
import socket

from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any

class OpenShiftAgentManager(AgentManagerInterface):

    def __init__(self):
        print("... Starting OpenShift Agent Manager")
    
    def get_agent_metrics(self, user_id, id):
        print(f"Agent {id}. Getting metrics")
        
        json_result = []
        try:
            conn = http.client.HTTPConnection(host=id, port=8080, timeout=1)
            conn.request("GET", "/metrics")
            
            response = conn.getresponse()
            data = response.read()        
            try:
                # Try to decode the response content
                result = data.decode("utf-8")
                json_result = json.loads(result)
                print("Response received successfully:")
                print(result)
            except UnicodeDecodeError:
                raise Exception("Failed to decode response content.")
                    
        except http.client.HTTPException as e:
            # Handle HTTP related errors
            print(f"HTTP error occurred: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            # Handle connection errors
            print(f"Connection error occurred: {e}")
            raise
        except Exception as e:
            # General exception handler for other potential errors
            print(f"An error occurred: {e}")
            raise
        finally:
            # Ensure the connection is closed
            conn.close()
        return json_result

    async def set_agent_metrics(self, method: str, user_id:str, payload: dict[str, Any]):
        print("set_agent_metric")
        print(payload)
        print("----------------")
        
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
            raise
            
        print(f"Agent {agent_id}. Setting metric {metricInfo['name']}[{method}]")
        
        try:
            conn = http.client.HTTPConnection(host=agent_ip, port=8080, timeout=1)
            conn.request(method, full_path)
            print(f"Requested: {method} {full_path}")
            
            response = conn.getresponse()
            data = response.read()

            try:
                # Try to decode the response content
                result = data.decode("utf-8")
                print("Response received successfully:")
                print(result)
            except UnicodeDecodeError:
                raise Exception("Failed to decode response content.")
                    
        except http.client.HTTPException as e:
            # Handle HTTP related errors
            print(f"HTTP error occurred: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            # Handle connection errors
            print(f"Connection error occurred: {e}")
            raise
        except Exception as e:
            # General exception handler for other potential errors
            print(f"An error occurred: {e}")
            raise
        finally:
            # Ensure the connection is closed
            conn.close()
    
    def kick(self, user_id, agent_id, agent_dns, kick_initial_count):
        #agent_ip = payload['ip']
        #agent_id = payload['id']
        #kick_initial_count = payload['count']
        
        agent_kick_payload = {
            "count": kick_initial_count        
        }
        json_agent_kick_payload = json.dumps(agent_kick_payload)
        try:
            conn = http.client.HTTPConnection(agent_dns, 8080, timeout=2)
            headers = {
                'Content-Type': 'application/json'
            }
            # Make the POST request, attaching the JSON body
            print(f"Agent {agent_id}[{agent_dns}] kicking (count={kick_initial_count})...")
            conn.request("POST", "/operations/order", body=json_agent_kick_payload, headers=headers)
            # Get the response
            response = conn.getresponse()
            data = response.read()

            # Print the response data
            print(data.decode("utf-8"))
        except socket.timeout:
            print("The request timed out.")
            raise

        except Exception as e:
            # Handle other possible exceptions
            print(f"Request failed: {e}")
            raise

        finally:
            # Close the connection
            conn.close()
        return True
    
    def set_agent_communication_path(self, user_id, sourceAgent, targetAgent):
        print(f"Calling POST http://{sourceAgent}:8080/agents/{targetAgent}")
        print(targetAgent)
        next_hop_address = {
            "ip": targetAgent,
            "port": 8080
        }
        json_next_hop_address = json.dumps(next_hop_address)
        try:
            conn = http.client.HTTPConnection(sourceAgent, 8080, timeout=2)
            headers = {
                'Content-Type': 'application/json'
            }
            # Make the POST request, attaching the JSON body
            conn.request("POST", "/agents/" + targetAgent, body=json_next_hop_address, headers=headers)
            # Get the response
            response = conn.getresponse()
            data = response.read()

            # Print the response data
            print(data.decode("utf-8"))
        except socket.timeout:
            print("The request timed out.")
            raise

        except Exception as e:
            # Handle other possible exceptions
            print(f"Request failed: {e}")
            raise

        finally:
            # Close the connection
            conn.close()

    async def delete_metrics_definitions(self, user_id):
        pass