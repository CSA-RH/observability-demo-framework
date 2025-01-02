from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict, List, Any

import secrets, os, json

class MockClusterConnector(ClusterConnectorInterface):
    
    def __init__(self): 
        print("... Starting Mock Cluster connector.")

    def get_cluster_info(self) -> Dict[str, str]:
        return {
            "Connected": True,
            "Name": "Fake Cluster",
            "Namespace": "fake-namespace",
            "ConsoleURL": "https://redhat.com", 
            "apiLogsURL": "https://redhat.com", 
            "JaegerUI": "https://redhat.com"
        }

    def __generate_pod_suffix(self):
        # Generate a random 9-hex character part
        first_part = secrets.token_hex(4)  # 4 bytes -> 8 hex characters
        first_part += secrets.token_hex(1)[0]  # Add 1 more hex character

        # Generate a random 5-hex character part
        second_part = secrets.token_hex(3)[:5]  # 3 bytes -> 6 hex characters, but only take 5

        # Combine the parts with a dash
        pod_suffix = f"{first_part}-{second_part}"
        return pod_suffix
    
    async def create_simulation_resources(self, payload: List[Dict[str, Any]]):
        print("create simulation resources")
        for item in payload:            
                item["ip"] = "1.2.3.4"
                item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()                
        return payload
    
    def __save_json_to_file(self, payload, file_path='/tmp/obs-demo-fw-sim.json'):
        try:
            # Ensure the /tmp directory exists (it should, but just in case)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Open the file in write mode ('w') and save the JSON payload
            with open(file_path, 'w') as json_file:
                json.dump(payload, json_file, indent=4)  # Optionally, you can use indent for formatting

            print(f"JSON data successfully saved to {file_path}")
        except Exception as e:
            print(f"Failed to save JSON: {str(e)}")

    def save_simulation(self, json_simulation):
        print("save simulation")
        self.__save_json_to_file(json_simulation)
        
    def __load_json_from_file(self, file_path="/tmp/obs-demo-fw-sim.json"):
        try:
            # Open the file in read mode ('r') and load the JSON data
            with open(file_path, 'r') as json_file:
                payload = json.load(json_file)

            print(f"JSON data successfully loaded from {file_path}")
            return payload
        except FileNotFoundError:
            print(f"File {file_path} not found.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {str(e)}")
            return None
        except Exception as e:
            print(f"Failed to load JSON: {str(e)}")
            return None
    
    def retrieve_simulation(self):
        print("retrieve simulation")
        json_data = self.__load_json_from_file()
        print(json_data)

        if not json_data:
            return {}
        # Add pod name
        for item in json_data["agents"]:            
            item["pod"] = item["id"] + "-" + self.__generate_pod_suffix()

        return json_data
    
    def __delete_json_file(self, file_path="/tmp/obs-demo-fw-sim.json"):
        try:
            # Check if the file exists
            if os.path.exists(file_path):
                # Delete the file
                os.remove(file_path)
                print(f"File {file_path} successfully deleted.")
            else:
                print(f"File {file_path} does not exist.")
        except Exception as e:
            print(f"Failed to delete the file: {str(e)}")

    async def delete_simulation(self):
        print("delete simulation")
        self.__delete_json_file()
    
    async def create_alert(self, agent_name, agent_type, metric):
        print("Created alert: ")
        print(f" - Agent name: {agent_name}")
        print(f" - Agent type: {agent_type}")
        print(" - metric info: ")
        print(metric)
        print(" ****** ")
        return self.__create_prometheus_rule(agent_name, agent_type, metric['name'], metric['alert'])#, self.__get_current_namespace())

    def __map_expression_to_alert(self, expression):
        """
        Maps a comparison expression to a semantic alert label.

        :param expression: A string representing the comparison operator 
                        (e.g., "<", "<=", "!=", ">", ">=").
        :return: A string representing the semantic alert label.
        """
        mapping = {
            "<": "StrictlyTooLow",
            "≤": "TooLow",
            ">": "StrictlyTooHigh",
            "≥": "TooHigh",
            "≠": "Distinct",
            "=": "Equals",
        }
        
        return mapping.get(expression, "Unknown")

    def __map_expression_operator_to_comparison_operator(self, expression_operator):
        mapping = {
            "<": "<",
            "≤": "<=",
            ">": ">",
            "≥": ">=",
            "≠": "!=",
            "=": "==",
        }
        return mapping.get(expression_operator, "unknown")

    def __create_prometheus_rule(self, agent_name, agent_type, metric_name, alert, namespace="observability-demo"):
        expression_operator = alert['expression']
        semantic_expression_label = self.__map_expression_to_alert(expression_operator)
        
        alert_name_crd = f"{agent_name}_{metric_name}_{semantic_expression_label}"
        alert_name_openshift = f"{metric_name}{semantic_expression_label}"
        summary = f"Alert {semantic_expression_label} on {agent_name}"
        threshold = alert['value'];        
        expression = f"{metric_name}{{job=\"{agent_name}\"}}{self.__map_expression_operator_to_comparison_operator(expression_operator)}{threshold}"
        # Define the PrometheusRule resource
        prometheus_rule_body = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": alert_name_crd,
                "namespace": namespace,
            },
            "spec": {
                "groups": [
                    {
                        "name": agent_name,
                        "rules": [
                            {
                                "alert": alert_name_openshift,
                                "annotations": {
                                    "summary": summary
                                },
                                "expr": expression,
                                "for": "1m",
                                "labels": {
                                    "severity": alert['severity'],
                                    "alertType": agent_type,
                                },
                            }
                        ],
                    }
                ],
            },
        }

        print(prometheus_rule_body)

        # Load Kubernetes configuration
        #config.load_kube_config()

        # Create the CustomObjectsApi instance
        #api_instance = client.CustomObjectsApi()

        # Create the PrometheusRule resource
        #try:
        #    response = api_instance.create_namespaced_custom_object(
        #        group="monitoring.coreos.com",
        #        version="v1",
        #        namespace=namespace,
        #        plural="prometheusrules",
        #        body=prometheus_rule_body,
        #    )
        #    print(f"PrometheusRule '{agent_name}' created successfully.")
        #    return response
        #except client.exceptions.ApiException as e:
        #    print(f"Exception when creating PrometheusRule: {e}")
        #    return None



