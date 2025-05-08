from cluster_connector.ClusterConnectorInterface import ClusterConnectorInterface
from typing import Dict, List, Any
from kubernetes import config, client, watch       # type: ignore
from kubernetes.client.rest import ApiException    # type: ignore
from utils import JSONUtils

import os, time, json, http.client, socket, base64

class OpenShiftClusterConnector(ClusterConnectorInterface):

    ALERTS_CONFIGMAP = "obs-demo-fwk-alerts"

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

    def get_cluster_info(self, user) -> Dict[str, str]: 
        # Get namespace
        api_namespace = self.__get_current_namespace()
        user_namespace = f"{api_namespace}-{user}"

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
            jaegerui_route = f"{self.__get_route_url_by_selector(api_namespace, 'app.kubernetes.io/component=gateway')}/obsdemo"
            grafana_url_route = self.__get_route_url_by_selector(
                api_namespace, 
                "observability-demo-framework=grafana"
            )

        except (config.ConfigException, KeyError):
            return {"Connected": False}
        
        return {
            "Connected": True,
            "Name": cluster_name,
            "Namespace": user_namespace,
            "ConsoleURL": console_url, 
            "apiLogsURL": f"{console_url}/k8s/ns/{api_namespace}/pods/{os.getenv('HOSTNAME')}/logs", 
            "JaegerUI": jaegerui_route, 
            "GrafanaURL": grafana_url_route
        }
    
    def __get_image(self, tech_stack):
        if tech_stack == "waiter":
            return "obs-client-dotnet:latest"
        #if tech_stack == "nodejs":
        return "obs-client-node:latest"

    
    def __get_inject_annotation(self, tech_stack):
        if tech_stack == "waiter":
            return 'instrumentation.opentelemetry.io/inject-dotnet'
        #if tech_stack == "nodejs":
        return 'instrumentation.opentelemetry.io/inject-nodejs'


    def __create_deployment(self, user_namespace, image_namespace, item):
        print("DEPLOYMENT TYPE: " + item['type'])
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
                            self.__get_inject_annotation(item['type']): 'true'
                        }
                    },
                    'spec': {
                        'containers': [{
                            'name': 'core',
                            'image': f"image-registry.openshift-image-registry.svc:5000/{image_namespace}/{self.__get_image(item['type'])}",
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

        print(deployment_manifest)

        deployment_name = "." 
        try:
            deployment_name = item["id"]
            self.__apps_v1_api.create_namespaced_deployment(namespace=user_namespace, body=deployment_manifest)
            print(f"Deployment {deployment_name} successfully created.")
        except Exception as e: 
            print(f"Error creating Deployment {deployment_name}. Exception: ")            
            print(e)
            print("-------")
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
        
    async def __get_agent_pods_dictionary(self, namespace):
        try:        
            pods = self.__core_v1_api.list_namespaced_pod(
                namespace, 
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
                print(f"Waiting for pods of deployment {deployment_name} to become ready. Ready pods: {deployment.status.ready_replicas}/{deployment.spec.replicas}")
            
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
       
    def save_simulation(self, user, json_data):
        namespace=f"{self.__get_current_namespace()}-{user}"
        # Encode to base64
        encoded_data = base64.b64encode(json.dumps(json_data).encode('utf-8')).decode('utf-8')
        
        secret = client.V1Secret(
            metadata=client.V1ObjectMeta(name="obs-demo-fw-state", labels={"observability-demo-framework": "storage"}),            
            data={"simulation": encoded_data},
        )
        try:
            self.__core_v1_api.create_namespaced_secret(namespace, secret)
            print(f"Simulation saved successfully in the cluster as secret obs-demo-fw-state.")
        except client.ApiException as e:
            print(f"Exception when saving simulation as a secret[obs-demo-fw-state]: {e}")
            raise
    
    async def create_simulation_resources(self, user, agents: List[Dict[str, Any]]):
        image_namespace=self.__get_current_namespace()
        namespace = f"{image_namespace}-{user}"

        # Create all deployment and services. 
        for item in agents:
            
            print(f'Agent: {item["id"]}')
                
            # Create Deployment
            self.__create_deployment(namespace, image_namespace, item)
            print(f"Deployment for {item['id']} created.")
            
            # Create Service
            self.__create_service(namespace, item)
            print(f"Service for {item['id']} created.")
            
            # Create service monitor
            self.__create_service_monitor(namespace, item)
            print(f"ServiceMonitor for {item['id']} created.")

        # Make sure that all pods have started before adding associations
        # Wait for the Service to be ready and get its IP
        podNames = self.__get_agent_pods_dictionary(namespace)
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
    
    def __get_agent_pods_dictionary(self, namespace):
        try:
            pods = self.__core_v1_api.list_namespaced_pod(
                namespace, 
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

    def retrieve_simulation(self, user):
        # Get the secret
        secret_name="obs-demo-fw-state"
        user_namespace=f"{self.__get_current_namespace()}-{user}"
        simulation = []
        try:
            secret = self.__core_v1_api.read_namespaced_secret(secret_name, user_namespace)
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
        pods = self.__get_agent_pods_dictionary(user_namespace)
        for agent in simulation["agents"]:
            agent["pod"] = pods[agent["id"]]

        return simulation

    def __load_json_from_configmap(self, configmap_name, key, namespace):
        try:
            # Get the ConfigMap
            configmap = self.__core_v1_api.read_namespaced_config_map(configmap_name, namespace)
            # Extract the JSON string
            json_str = configmap.data.get(key, "{}")  # Default to an empty JSON object if the key is missing
            # Parse and return the JSON data
            return json.loads(json_str)
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"ConfigMap '{configmap_name}' not found in namespace '{namespace}'.")
                return []
            else:
                raise
 
    def __save_json_to_configmap(self, json_data, configmap_name, key, namespace):
        json_str = json.dumps(json_data)
        configmap_data = {
            "metadata": {
                "name": configmap_name,
                "namespace": namespace,
                "labels": {
                    "observability-demo-framework": "storage"
                }
            },
            "data": {
                key: json_str,
            },
        }
        try:
        # Check if the ConfigMap exists
            self.__core_v1_api.read_namespaced_config_map(configmap_name, namespace)
            # If it exists, update it
            self.__core_v1_api.patch_namespaced_config_map(configmap_name, namespace, configmap_data)
            print(f"Updated ConfigMap '{configmap_name}' in namespace '{namespace}'.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                # If it doesn't exist, create it
                self.__core_v1_api.create_namespaced_config_map(namespace, configmap_data)
                print(f"Created ConfigMap '{configmap_name}' in namespace '{namespace}'.")
            else:
                raise

    def save_alert_definition(self, user, alert):
        namespace = f"{self.__get_current_namespace()}-{user}"
        alerts_definition=self.__load_json_from_configmap(self.ALERTS_CONFIGMAP, "alerts", namespace)
        alerts_definition.append(alert)
        self.__save_json_to_configmap(alerts_definition, self.ALERTS_CONFIGMAP, "alerts", namespace)

    def create_alert_resource(self, user, id, name, severity, group, expression, summary):
        # Define the PrometheusRule resource
        namespace = f"{self.__get_current_namespace()}-{user}"
        prometheus_rule_body = {
            "apiVersion": "monitoring.coreos.com/v1",
            "kind": "PrometheusRule",
            "metadata": {
                "name": id,
                "namespace": namespace,
                "labels": {
                    "observability-demo-framework": "agent"
                }
            },
            "spec": {
                "groups": [
                    {
                        "name": group,
                        "rules": [
                            {
                                "alert": name,
                                "annotations": {
                                    "summary": summary
                                },
                                "expr": expression,
                                "for": "1m",
                                "labels": {
                                    "severity": severity
                                },
                            }
                        ],
                    }
                ],
            },
        }    
        
        try:
            response = self.__custom_v1_api.create_namespaced_custom_object(
                group="monitoring.coreos.com",
                version="v1",
                namespace=namespace,
                plural="prometheusrules",
                body=prometheus_rule_body,
            )
            print(f"PrometheusRule '{id}' created successfully.")
            return {"success": True}
        except client.exceptions.ApiException as e:
            print(f"Exception when creating PrometheusRule: {e}")
            return None

    async def delete_simulation(self, user):        
        label_selector = "observability-demo-framework=agent"

        namespace = f"{self.__get_current_namespace()}-{user}"
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
        # Delete prometheus rules. 
        prometheus_rules = self.__custom_v1_api.list_namespaced_custom_object(
            group="monitoring.coreos.com",
            version="v1", 
            namespace=namespace, 
            plural="prometheusrules", 
            label_selector=label_selector
        )
        for pm in prometheus_rules.get("items", []):
            print(f"Deleting PrometheusRule: {pm['metadata']['name']}")
            self.__custom_v1_api.delete_namespaced_custom_object(
                group="monitoring.coreos.com",
                version="v1",
                namespace=namespace,
                plural="prometheusrules",
                name=pm['metadata']['name']
            )

        # Delete secret 
        secret_name="obs-demo-fw-state"
        try:
            self.__core_v1_api.delete_namespaced_secret(secret_name, namespace)
            print(f"Secret '{secret_name}' deleted successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"Secret '{secret_name}' not found in namespace '{namespace}'.")
            else:
                print(f"Failed to delete Secret '{secret_name}': {e}")            
            raise 
        
        # Delete config map
        config_map = self.ALERTS_CONFIGMAP
        try:
            self.__core_v1_api.delete_namespaced_config_map(config_map, self.__get_current_namespace())
            print(f"ConfigMap '{config_map}' deleted successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"ConfigMap '{config_map}' not found in namespace '{self.__get_current_namespace()}'.")
            else:
                print(f"Failed to delete ConfigMap '{config_map}': {e}")            
                raise 

        print("All matching resources deleted successfully.")

    def delete_alert(self, user, alert_name):
        namespace = f"{self.__get_current_namespace()}-{user}"
        try:
            self.__custom_v1_api.delete_namespaced_custom_object(
                group="monitoring.coreos.com",
                version="v1",
                namespace=namespace,
                plural="prometheusrules",
                name=alert_name)
            return {"success": True}
        except client.exceptions.ApiException as e:
            if e.status == 404:
                print(f"PrometheusRule '{alert_name}' not found in namespace '{self.__get_current_namespace()}'.")                
            else:
                print(f"Failed to delete PrometheusRule '{alert_name}': {e}")
            return {"success": False, "error": e}            

    def delete_alert_definition(self, user, alert_id):
        namespace = f"{self.__get_current_namespace()}-{user}"
        try:            
            alerts = self.__load_json_from_configmap(self.ALERTS_CONFIGMAP, "alerts", namespace)            
            cleaned_alerts = [item for item in alerts if item.get("id") != alert_id]
            self.__save_json_to_configmap(cleaned_alerts, self.ALERTS_CONFIGMAP, "alerts", namespace)
            return {"success": True}
        except client.exception.ApiException as e: 
            return {"success": False, "error": e}

    
    def get_alert_definitions(self, user):
        namespace = f"{self.__get_current_namespace()}-{user}"
        alerts = self.__load_json_from_configmap(self.ALERTS_CONFIGMAP, "alerts", namespace)
        return alerts
    
    def retrieve_hostname_from_service_id(self, user, id):
        namespace = f"{self.__get_current_namespace()}-{user}"
        return f"{id}.{namespace}.svc"