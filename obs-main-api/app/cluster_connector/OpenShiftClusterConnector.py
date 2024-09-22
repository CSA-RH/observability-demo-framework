from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict, List, Any
from kubernetes import config, client, watch       # type: ignore
from kubernetes.client.rest import ApiException    # type: ignore

import os, time, json, http.client, socket, base64

class OpenShiftClusterConnector(ClusterConnectorInterface):    
        
    def __init__(self):        
        # Load Kubernetes configuration depending on the environment        
        try:
            # Try to load the in-cluster configuration
            config.load_incluster_config()
            print("... Running in-cluster. Service account loaded.")
        except config.ConfigException:
            # Fallback to local kubeconfig if running outside the cluster
            config.load_kube_config()
            print("... Running out-of-cluster. Local kubeconfig loaded.")
        
        self.__core_v1_api = client.CoreV1Api()
        self.__apps_v1_api = client.AppsV1Api()
        self.__custom_v1_api = client.CustomObjectsApi()        
    
    def __get_current_namespace(self, context: str = None) -> str | None:
        ns_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        if os.path.exists(ns_path):
            with open(ns_path) as f:
                return f.read().strip()
        try:
            contexts, active_context = config.list_kube_config_contexts()
            if context is None:
                return active_context["context"]["namespace"]
            selected_context = next(ctx for ctx in contexts if ctx["name"] == context)
            return selected_context["context"]["namespace"]
        except (KeyError, StopIteration):
            return "default"
        
    def __get_route_url_by_selector(self, namespace, selector):

        # Get the route using the OpenShift API group, version, and resource
        api_group = "route.openshift.io"
        api_version = "v1"
        resource = "routes"

        # List routes in the specified namespace using the label selector
        routes = self.__custom_v1_api.list_namespaced_custom_object(
            group=api_group,
            version=api_version,
            namespace=namespace,
            plural=resource,
            label_selector=selector
        )

        # If routes are found, extract the route details (e.g., the host and TLS information)
        for route in routes.get("items", []):
            route_name = route.get("metadata", {}).get("name")
            host = route.get("spec", {}).get("host")
            tls = route.get("spec", {}).get("tls")
            
            # Determine if the route uses https (if TLS is present) or http
            scheme = "https" if tls else "http"
            
            # Build the full URL
            url = f"{scheme}://{host}"
            
            print(f"Route Name: {route_name}, URL: {url}")
            return url

        # If no route matches the selector
        return None, None

    def get_cluster_info(self) -> Dict[str, str]: 
        # Get current namespace
        current_namespace = self.__get_current_namespace()

        # Get cluster name and console link
        try:
            # OpenShift API group, version, and resource to retrieve the Console
            group = "config.openshift.io"
            version = "v1"
            plural = "consoles"
            name = "cluster"  # The Console resource name is always 'cluster'

            # Fetching the Console resource, which contains the cluster name (URL-based)
            console_resource = self.__custom_v1_api.get_cluster_custom_object(
                group=group,
                version=version,
                plural=plural,
                name=name
            )

            # Extract cluster URL and parse to use as the cluster name
            console_url = console_resource['status']['consoleURL']
            cluster_name = console_url.split('.')[2]  # Cluster name typically part of the URL
            jaegerui_route = self.__get_route_url_by_selector(
                self.__get_current_namespace(), 
                "app.kubernetes.io/component=query-frontend")

        except (config.ConfigException, KeyError):
            return {"Connected": False}
        
        return {
            "Connected": True,
            "Name": cluster_name,
            "Namespace": current_namespace,
            "ConsoleURL": console_url, 
            "apiLogsURL": f"{console_url}/k8s/ns/{current_namespace}/pods/{os.getenv("HOSTNAME")}/logs", 
            "JaegerUI": jaegerui_route
        }
    
    def __create_deployment(self, namespace, item):    
        deployment_manifest = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': item["id"], 
                'labels': {
                    "app": item["id"], 
                    'observability-demo-framework': 'agent'
                }
            },
            'spec': {
                'replicas': 1,
                'selector': {
                    'matchLabels': {
                        'app': item["id"]
                    }
                },
                'template': {
                    'metadata': {
                        'labels': {
                            'app': item["id"], 
                            'observability-demo-framework': 'agent'                    
                        }, 
                        'annotations': {
                            'instrumentation.opentelemetry.io/inject-nodejs': 'true'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': 'core',
                            'image': 'obs-client-node:latest',
                            'ports': [{
                                'containerPort': 8080
                            }],
                            'readinessProbe': {
                                'httpGet': {
                                    'path': '/',
                                    'port': 8080
                                },
                                'initialDelaySeconds': 3,
                                'periodSeconds': 3
                            }
                        }]
                    }
                }
            }
        }

        deployment_name = "." 
        try:
            deployment_name = item["id"]
            self.__apps_v1_api.create_namespaced_deployment(namespace=namespace, body=deployment_manifest)
            print(f"Deployment {deployment_name} successfully created.")
        except Exception as e: 
            print(f"")
            raise        
    
    def __create_service(self, namespace, item):
        service_manifest = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': item["id"],
                'labels': {
                    "app": item["id"], 
                    'observability-demo-framework': 'agent'
                }
            },
            'spec': {
                'selector': {
                    'app': item["id"]
                },
                'ports': [{
                    'protocol': 'TCP',
                    'port': 8080,
                    'targetPort': 8080, 
                    'name': 'api'
                }, 
                {
                    'protocol': 'TCP',
                    'port': 8081,
                    'targetPort': 8081,
                    'name': 'metrics'
                }]
            }
        }
        service_name = "."
        try:
            service_name = item["id"]
            self.__core_v1_api.create_namespaced_service(namespace=namespace, body=service_manifest)
            print(f"Service {service_name} created successfully.")
        except Exception as e: 
            print(f"Error creating Service {service_name}. Exception: ")            
            print(e)
            print("-------")
            raise
        
    async def __get_agent_pods_dictionary(self):
        try:        
            pods = self.__core_v1_api.list_namespaced_pod(
                namespace = self.__get_current_namespace(), 
                label_selector = 'observability-demo-framework=agent')
        except Exception as e: 
            print(f"Exception when retrieving pods: {e}")
            raise
        
        pods_dict = {}
        for item in pods.items:
            name_parts = item.metadata.name.split("-")
            deployment_name = "-".join(name_parts[:-2])
            pods_dict[deployment_name]=item.metadata.name
        return pods_dict

    def __wait_for_service_ready_and_get_ip(self, namespace, service_name, timeout=300):
        w = watch.Watch()
        start_time = time.time()

        try:
            for event in w.stream(
                    self.__core_v1_api.list_namespaced_service, 
                    namespace=namespace, 
                    timeout_seconds=timeout):
                service = event['object']
                if service.metadata.name == service_name:
                    print(f"Service {service_name} status: Available")
                    service_ip = service.spec.cluster_ip
                    if service_ip:
                        print(f"Service {service_name} IP: {service_ip}")
                        w.stop()
                        return service_ip

                if time.time() - start_time > timeout:
                    print(f"Timeout waiting for Service {service_name} to be ready.")
                    w.stop()

        except ApiException as e:
            print(f"Exception when waiting for Service: {e}")
            raise

        return None
        
    def __wait_for_deployment_ready(self, deployment_name, namespace, timeout=300, interval=5):
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            # Get the deployment status
            deployment = self.__apps_v1_api.read_namespaced_deployment(
                name=deployment_name, 
                namespace=namespace)
            
            # Check if the number of ready replicas matches the desired replicas
            if deployment.status.ready_replicas == deployment.spec.replicas:
                print(f"All pods for deployment '{deployment_name}' are ready.")
                return True
            else:
                print(f"Waiting for pods to become ready. Ready pods: {deployment.status.ready_replicas}/{deployment.spec.replicas}")
            
            # Sleep for the defined interval before checking again
            time.sleep(interval)

        # If we exceed the timeout and not all pods are ready
        print(f"Timeout: Not all pods for deployment '{deployment_name}' are ready after {timeout} seconds.")
        return False
    
    def __create_service_monitor(self, namespace, item):
        # Define the ServiceMonitor specification
        service_monitor_body = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "ServiceMonitor",
            "metadata": {
                "name": item["id"],
                "labels": {
                    "app": item["id"],
                    'observability-demo-framework': 'agent'
                }
            },
            "spec": {
                "selector": {
                    "matchLabels": {
                        "app": item["id"]
                    }
                },
                "endpoints": [
                    {
                        "port": "metrics",
                        "interval": "30s"
                    }
                ]
            }
        }
        
        service_monitor_name = "."
        try:
            service_monitor_name = item["id"]
            self.__custom_v1_api.create_namespaced_custom_object(
                group="monitoring.coreos.com",
                version="v1",
                namespace=namespace,
                plural="servicemonitors",
                body=service_monitor_body
            )
            print(f"ServiceMonitor {service_monitor_name} created successfully.")
        except client.exceptions.ApiException as e:
            print(f"Exception when creating ServiceMonitor {service_monitor_name}")
            print(e)
            print("--------")
            raise
       
    def save_simulation(self, json_data):
        # Encode to base64
        encoded_data = base64.b64encode(json.dumps(json_data).encode('utf-8')).decode('utf-8')
        
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name="obs-demo-fw-state"),
            data={"simulation": encoded_data},
        )
        try:
            self.__core_v1_api.create_namespaced_secret(self.__get_current_namespace(), secret)
            print(f"Simulation saved successfully in the cluster as secret obs-demo-fw-state.")
        except client.ApiException as e:
            print(f"Exception when saving simulation as a secret[obs-demo-fw-state]: {e}")
            raise
    
    async def create_simulation_resources(self, agents: List[Dict[str, Any]]):
        namespace = self.__get_current_namespace()  # Assuming you have a function to get the current namespace

        # Create all deployment and services. 
        for item in agents:
            
            print(f'Agent: {item["id"]}')
                
            # Create Deployment
            self.__create_deployment(namespace, item)
            print(f"Deployment for {item['id']} created.")
            
            # Create Service
            self.__create_service(namespace, item)
            print(f"Service for {item['id']} created.")
            
            # Create service monitor
            self.__create_service_monitor(namespace, item)
            print(f"ServiceMonitor for {item['id']} created.")

        # Make sure that all pods have started before adding associations
        # Wait for the Service to be ready and get its IP
        podNames = self.__get_agent_pods_dictionary()
        for item in agents:            
            service_ip = self.__wait_for_service_ready_and_get_ip(namespace, item["id"])
            if service_ip:
                print(f"The Service IP address of {item['id']} is: {service_ip}")
                item["ip"] = service_ip
            else:
                print(f"Failed to retrieve the Service IP address for {item['id']}.")
                continue
            
            # Wait for the Service to be ready and get its IP
            self.__wait_for_deployment_ready(item['id'], namespace)
            item["pod"] = podNames[item['id']]            
        
        # Show result
        print(agents)
        return agents
    
    def __get_agent_pods_dictionary(self):
        try:
            pods = self.__core_v1_api.list_namespaced_pod(
                namespace=self.__get_current_namespace(), 
                label_selector='observability-demo-framework=agent')
            pods_dict = {}
        except Exception as e:             
            print(f"Error retrieving pods: {e}")
            raise

        for item in pods.items:
            name_parts = item.metadata.name.split("-")
            deployment_name = "-".join(name_parts[:-2])
            pods_dict[deployment_name]=item.metadata.name
        return pods_dict

    def retrieve_simulation(self):
        # Get the secret
        secret_name="obs-demo-fw-state"
        simulation = []
        try:
            secret = self.__core_v1_api.read_namespaced_secret(secret_name, self.__get_current_namespace())
            if 'simulation' in secret.data:
                encoded_json_data = secret.data['simulation']
                decoded_json_data = base64.b64decode(encoded_json_data).decode('utf-8')
                print(decoded_json_data)
                
                # Convert the decoded string back into a JSON object
                simulation = json.loads(decoded_json_data)
            else:
                message = f"Secret '{secret_name}' does not contain 'json-file' key."
                print(message)
                raise RuntimeError(message)
                
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"Secret '{secret_name}' not found in namespace '{self.__get_current_namespace()}'.")
            else:
                message = f"Failed to read Secret '{secret_name}': {e}"
                print(message)
                raise RuntimeError(message)
            return {}
        # Update agent pod name
        pods = self.__get_agent_pods_dictionary()
        for agent in simulation["agents"]:
            agent["pod"] = pods[agent["id"]]

        return simulation
            
    async def delete_simulation(self):
        label_selector = "observability-demo-framework=agent"

        namespace = self.__get_current_namespace()
        # Delete Deployments matching the selector
        deployments = self.__apps_v1_api.list_namespaced_deployment(namespace=namespace, label_selector=label_selector)
        for deployment in deployments.items:
            print(f"Deleting Deployment: {deployment.metadata.name}")
            self.__apps_v1_api.delete_namespaced_deployment(name=deployment.metadata.name, namespace=deployment.metadata.namespace)

        # Delete Services matching the selector
        services = self.__core_v1_api.list_namespaced_service(namespace=namespace, label_selector=label_selector)
        for service in services.items:
            print(f"Deleting Service: {service.metadata.name}")
            self.__core_v1_api.delete_namespaced_service(name=service.metadata.name, namespace=service.metadata.namespace)

        # Delete ServiceMonitors matching the selector
        # Assuming ServiceMonitors are custom resources from the Prometheus operator
        service_monitors = self.__custom_v1_api.list_namespaced_custom_object(
            group="monitoring.coreos.com",
            version="v1",
            namespace=namespace,
            plural="servicemonitors",
            label_selector=label_selector
        )
        for sm in service_monitors.get("items", []):
            print(f"Deleting ServiceMonitor: {sm['metadata']['name']}")
            self.__custom_v1_api.delete_namespaced_custom_object(
                group="monitoring.coreos.com",
                version="v1",
                namespace=namespace,
                plural="servicemonitors",
                name=sm['metadata']['name']
            )
        # Delete secret 
        secret_name="obs-demo-fw-state"
        try:
            self.__core_v1_api.delete_namespaced_secret(secret_name, self.__get_current_namespace())
            print(f"Secret '{secret_name}' deleted successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"Secret '{secret_name}' not found in namespace '{self.__get_current_namespace()}'.")
            else:
                print(f"Failed to delete Secret '{secret_name}': {e}")            
            raise 
        print("All matching resources deleted successfully.")