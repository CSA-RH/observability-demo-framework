import http.client
import urllib.parse
import json
import socket

from agent_manager.AgentManagerInterface import AgentManagerInterface
from typing import Any
import logging

log = logging.getLogger(__name__)


class AgentRequestError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


class OpenShiftAgentManager(AgentManagerInterface):

    def __init__(self):
        log.info("Starting OpenShift Agent Manager")
    
    def get_agent_metrics(self, user_id, id):
        log.info(f"Agent {id}. Getting metrics")
        
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
                log.info("Response received successfully:")
                log.debug(result)
            except UnicodeDecodeError:
                raise Exception("Failed to decode response content.")
                    
        except http.client.HTTPException as e:
            # Handle HTTP related errors
            log.error(f"HTTP error occurred: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            # Handle connection errors
            log.error(f"Connection error occurred: {e}")
            raise
        except Exception as e:
            # General exception handler for other potential errors
            log.error(f"An error occurred: {e}")
            raise
        finally:
            # Ensure the connection is closed
            conn.close()
        return json_result

    def set_agent_metrics(self, method: str, user_id:str, payload: dict[str, Any]):
        log.info("set_agent_metric")
        log.debug(payload)
        
        full_path = ""
        try:
            agent_dns = payload['dns']
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
            log.error(f"An error occurred: {e}")
            raise
            
        log.info(f"Agent {agent_id}. Setting metric {metricInfo['name']}[{method}]")

        result = self.__request_agent_metric(agent_dns, method, full_path)
        if method == "PUT" and result["status"] == 404:
            log.warning(f"Metric {metricInfo['name']} not found on agent; creating with POST instead.")
            result = self.__request_agent_metric(agent_dns, "POST", full_path)

        if result["status"] >= 400:
            raise AgentRequestError(result["status"], result["body"])

        return result["body"]

    def __request_agent_metric(self, agent_dns: str, method: str, full_path: str) -> dict:
        conn = http.client.HTTPConnection(host=agent_dns, port=8080, timeout=1)
        try:
            conn.request(method, full_path)
            log.info(f"Requested: {method} {full_path}")

            response = conn.getresponse()
            data = response.read()

            try:
                body = data.decode("utf-8")
            except UnicodeDecodeError:
                raise Exception("Failed to decode response content.")

            log.info("Response received successfully:")
            log.debug(body)
            return {"status": response.status, "body": body}
        except http.client.HTTPException as e:
            log.error(f"HTTP error occurred: {e}")
            raise
        except (ConnectionError, TimeoutError) as e:
            log.error(f"Connection error occurred: {e}")
            raise
        except Exception as e:
            log.error(f"An error occurred: {e}")
            raise
        finally:
            conn.close()
    
    def kick(self, user_id, agent_id, agent_dns, kick_initial_count):
        #agent_dns = payload['ip']
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
            log.info(f"Agent {agent_id}[{agent_dns}] kicking (count={kick_initial_count})...")
            conn.request("POST", "/operations/order", body=json_agent_kick_payload, headers=headers)
            # Get the response
            response = conn.getresponse()
            data = response.read()

            # Print the response data
            log.debug(data.decode("utf-8"))
        except socket.timeout:
            log.error("The request timed out.")
            raise

        except Exception as e:
            # Handle other possible exceptions
            log.error(f"Request failed: {e}")
            raise

        finally:
            # Close the connection
            conn.close()
        return True
    
    def set_agent_communication_path(self, user_id, sourceAgent, targetAgent):
        log.info(f"Calling POST http://{sourceAgent}:8080/agents/{targetAgent}")
        log.debug(targetAgent)
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
            log.debug(data.decode("utf-8"))
        except socket.timeout:
            log.error("The request timed out.")
            raise

        except Exception as e:
            # Handle other possible exceptions
            log.error(f"Request failed: {e}")
            raise

        finally:
            # Close the connection
            conn.close()

    async def delete_metrics_definitions(self, user_id):
        pass