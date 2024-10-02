from agent_manager.OpenShiftAgentManager import OpenShiftAgentManager
from agent_manager.MockAgentManager import MockAgentManager
from cluster_connector.OpenShiftClusterConnector import OpenShiftClusterConnector
from cluster_connector.MockClusterConnector import MockClusterConnector

from fastapi import FastAPI                        # type: ignore  
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from typing import List, Dict, Any

from kubernetes import client, config, watch       # type: ignore
from kubernetes.client.rest import ApiException    # type: ignore

import os, types, time, json, base64, socket, http.client

app = FastAPI()

#TODO: Improve security. CORS 
origins = [
#    "http://localhost:3000",
    "*"
]

def get_current_namespace(context: str = None) -> str | None:
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

# Load Kubernetes configuration depending on the environment
def load_kube_config():
    try:
        # Try to load the in-cluster configuration
        config.load_incluster_config()
        print("... Running in-cluster. Service account loaded.")
    except config.ConfigException:
        # Fallback to local kubeconfig if running outside the cluster
        config.load_kube_config()
        print("... Running out-of-cluster. Local kubeconfig loaded.")

def is_running_in_openshift():
    # Check for Kubernetes environment variable
    return 'KUBERNETES_SERVICE_HOST' in os.environ

def is_using_fake_cluster_connector():
    value = os.environ.get('CLUSTER_CONNECTOR')
    if value is None:
        return False
    else:
        return value == 'mock'
    
def is_using_fake_agent_manager():
    value = os.environ.get('AGENT_MANAGER')
    if value is None:
        return False
    else:
        return value == 'mock'

agent_manager = types.SimpleNamespace()
cluster_connector = types.SimpleNamespace()

if is_using_fake_cluster_connector():
    cluster_connector = OpenShiftClusterConnector()
else:
    cluster_connector = MockClusterConnector()

if is_using_fake_agent_manager():
    agent_manager = MockAgentManager()
else:
    agent_manager = OpenShiftAgentManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Initialize Kubernetes API clients TODO: Move to interface
load_kube_config()
core_v1_api = client.CoreV1Api()
apps_v1_api = client.AppsV1Api()
custom_v1_api = client.CustomObjectsApi()


@app.get("/info")
async def get_info():
    # Get current namespace
    current_namespace = get_current_namespace()

    # Get cluster name and console link
    try:
        # OpenShift API group, version, and resource to retrieve the Console
        group = "config.openshift.io"
        version = "v1"
        plural = "consoles"
        name = "cluster"  # The Console resource name is always 'cluster'

        # Fetching the Console resource, which contains the cluster name (URL-based)
        console_resource = custom_v1_api.get_cluster_custom_object(
            group=group,
            version=version,
            plural=plural,
            name=name
        )

        # Extract cluster URL and parse to use as the cluster name
        console_url = console_resource['status']['consoleURL']
        cluster_name = console_url.split('.')[2]  # Cluster name typically part of the URL

    except (config.ConfigException, KeyError):
        return {"Connected": False}
    
    return {
        "Connected": True,
        "Name": cluster_name,
        "Namespace": current_namespace,
        "ConsoleURL": console_url, 
        "apiLogsURL": f"{console_url}/k8s/ns/{current_namespace}/pods/{os.getenv("HOSTNAME")}/logs"        
    }

def wait_for_pod_ready_and_get_ip(namespace, pod_name, timeout=300):
    """
    Wait for the Pod to be ready and retrieve its internal IP address.
    """
    w = watch.Watch()
    start_time = time.time()

    try:
        for event in w.stream(core_v1_api.list_namespaced_pod, namespace=namespace, timeout_seconds=timeout):
            pod = event['object']
            pod_status = pod.status.phase
            if pod.metadata.name == pod_name:
                print(f"Pod {pod_name} status: {pod_status}")

                # Check if the Pod is running and ready
                conditions = pod.status.conditions or []
                for condition in conditions:
                    if condition.type == "Ready" and condition.status == "True":
                        print(f"Pod {pod_name} is ready!")
                        internal_ip = pod.status.pod_ip
                        w.stop()  # Stop the watch once the Pod is ready
                        return internal_ip

            # Timeout condition
            if time.time() - start_time > timeout:
                print(f"Timeout waiting for Pod {pod_name} to be ready.")
                w.stop()
                return None

    except ApiException as e:
        print(f"Exception when waiting for Pod: {e}")
        return None
    
    return None

def get_agent_from_payload(name, payload):
    for item in payload:
        if item["group"] == "nodes" and item["data"]["id"] == name:
            return item
    return None
            
def add_next_hop_to_agent(name, agent):
    if "nextHop" in agent:
        agent["nextHop"].append(name)
    else:
        # If the key doesn't exist, create a new list with the string
        agent["nextHop"] = [name]

def save_simulation_as_secret(json_data):
    # Encode to base64
    encoded_data = base64.b64encode(json.dumps(json_data).encode('utf-8')).decode('utf-8')
    
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name="obs-demo-fw-state"),
        data={"simulation": encoded_data},
    )
    try:
        core_v1_api.create_namespaced_secret(get_current_namespace(), secret)
        print(f"Simulation saved successfully in the cluster as secret obs-demo-fw-state.")
    except client.ApiException as e:
        print(f"Exception when saving simulation as a secret[obs-demo-fw-state]: {e}")

def create_deployment(namespace, item):    
    deployment_manifest = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {
            'name': item["data"]["id"], 
            'labels': {
                "app": item["data"]["id"], 
                'observability-demo-framework': 'agent'
            }
        },
        'spec': {
            'replicas': 1,
            'selector': {
                'matchLabels': {
                    'app': item["data"]["id"]
                }
            },
            'template': {
                'metadata': {
                    'labels': {
                        'app': item["data"]["id"], 
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

    response = apps_v1_api.create_namespaced_deployment(namespace=namespace, body=deployment_manifest)    
    return response

# Function to create the service
def create_service(namespace, item):
    service_manifest = {
        'apiVersion': 'v1',
        'kind': 'Service',
        'metadata': {
            'name': item["data"]["id"],
            'labels': {
                "app": item["data"]["id"], 
                'observability-demo-framework': 'agent'
            }
        },
        'spec': {
            'selector': {
                'app': item["data"]["id"]
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

    response = core_v1_api.create_namespaced_service(namespace=namespace, body=service_manifest)
    return response

# Function to wait for the service and retrieve the Service IP
def wait_for_service_ready_and_get_ip(namespace, service_name, timeout=300):
    w = watch.Watch()
    start_time = time.time()

    try:
        for event in w.stream(core_v1_api.list_namespaced_service, namespace=namespace, timeout_seconds=timeout):
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
                return None

    except ApiException as e:
        print(f"Exception when waiting for Service: {e}")
        return None
    
    return None

def create_service_monitor(namespace, item):
    # Define the ServiceMonitor specification
    service_monitor_body = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": item["data"]["id"],
            "labels": {
                "app": item["data"]["id"],
                'observability-demo-framework': 'agent'
            }
        },
        "spec": {
            "selector": {
                "matchLabels": {
                    "app": item["data"]["id"]
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
    try:
        custom_v1_api.create_namespaced_custom_object(
            group="monitoring.coreos.com",
            version="v1",
            namespace=namespace,
            plural="servicemonitors",
            body=service_monitor_body
        )
        print("ServiceMonitor created successfully.")
    except client.exceptions.ApiException as e:
        print(f"Exception when creating ServiceMonitor: {e}")

# Function to check if all pods of a deployment are ready
def wait_for_deployment_ready(deployment_name, namespace, timeout=300, interval=5):
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        # Get the deployment status
        deployment = apps_v1_api.read_namespaced_deployment(name=deployment_name, namespace=namespace)
        
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

@app.post("/simulation")
async def create_simulation(payload: List[Dict[str, Any]]):
    namespace = get_current_namespace()  # Assuming you have a function to get the current namespace

    # Create all deployment and services. 
    for item in payload:
        if item["group"] == "nodes":
            print(f'Agent: {item["data"]["id"]}')
            
            # Create Deployment
            create_deployment(namespace, item)
            print(f"Deployment for {item['data']['id']} created.")
            
            # Create Service
            create_service(namespace, item)
            print(f"Service for {item['data']['id']} created.")
            
            # Create service monitor
            create_service_monitor(namespace, item)
            print(f"ServiceMonitor for {item['data']['id']} created.")

    # Make sure that all pods have started before adding associations
    # Wait for the Service to be ready and get its IP
    podNames = await get_agent_pods_dictionary()
    for item in payload:
        if item["group"] == "nodes":
            service_ip = wait_for_service_ready_and_get_ip(namespace, item["data"]["id"])
            if service_ip:
                print(f"The Service IP address of {item['data']['id']} is: {service_ip}")
                item["data"]["ip"] = service_ip
            else:
                print(f"Failed to retrieve the Service IP address for {item['data']['id']}.")
                continue
            
            # Wait for the Service to be ready and get its IP
            wait_for_deployment_ready(item['data']['id'], namespace)
            item["pod"] = podNames[item['data']['id']]

    
    # Add assotiations. 
    for item in payload: 
        if item["group"] == "edges":
            sourceName = item["data"]["source"]
            targetName = item["data"]["target"]
            sourceAgent = get_agent_from_payload(sourceName, payload)
            targetAgent = get_agent_from_payload(targetName, payload)
            #Update next-hop in payload
            add_next_hop_to_agent(targetAgent["data"]["id"], sourceAgent)
            #Call IP 
            print(f"Calling POST http://{sourceAgent['data']['id']}:8080/agents/{targetName}")
            print(targetAgent)
            next_hop_address = {
                "ip": targetAgent["data"]["id"],
                "port": 8080
            }
            json_next_hop_address = json.dumps(next_hop_address)
            try:
                conn = http.client.HTTPConnection(sourceAgent['data']['id'], 8080, timeout=2)
                headers = {
                    'Content-Type': 'application/json'
                }
                # Make the POST request, attaching the JSON body
                conn.request("POST", "/agents/" + targetName, body=json_next_hop_address, headers=headers)
                # Get the response
                response = conn.getresponse()
                data = response.read()

                # Print the response data
                print(data.decode("utf-8"))
            except socket.timeout:
                print("The request timed out.")

            except Exception as e:
                # Handle other possible exceptions
                print(f"Request failed: {e}")

            finally:
                # Close the connection
                conn.close()
        
    # Save the json in a secret
    save_simulation_as_secret(payload)
    # Show result
    print(payload)
    return payload

@app.delete("/simulation")
async def delete_simulation():
    label_selector = "observability-demo-framework=agent"

    namespace = get_current_namespace()
    # Delete Deployments matching the selector
    deployments = apps_v1_api.list_namespaced_deployment(namespace=namespace, label_selector=label_selector)
    for deployment in deployments.items:
        print(f"Deleting Deployment: {deployment.metadata.name}")
        apps_v1_api.delete_namespaced_deployment(name=deployment.metadata.name, namespace=deployment.metadata.namespace)

    # Delete Services matching the selector
    services = core_v1_api.list_namespaced_service(namespace=namespace, label_selector=label_selector)
    for service in services.items:
        print(f"Deleting Service: {service.metadata.name}")
        core_v1_api.delete_namespaced_service(name=service.metadata.name, namespace=service.metadata.namespace)

    # Delete ServiceMonitors matching the selector
    # Assuming ServiceMonitors are custom resources from the Prometheus operator
    service_monitors = custom_v1_api.list_namespaced_custom_object(
        group="monitoring.coreos.com",
        version="v1",
        namespace=namespace,
        plural="servicemonitors",
        label_selector=label_selector
    )
    for sm in service_monitors.get("items", []):
        print(f"Deleting ServiceMonitor: {sm['metadata']['name']}")
        custom_v1_api.delete_namespaced_custom_object(
            group="monitoring.coreos.com",
            version="v1",
            namespace=namespace,
            plural="servicemonitors",
            name=sm['metadata']['name']
        )
    # Delete secret 
    secret_name="obs-demo-fw-state"
    try:
        core_v1_api.delete_namespaced_secret(secret_name, get_current_namespace())
        print(f"Secret '{secret_name}' deleted successfully.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{get_current_namespace()}'.")
        else:
            print(f"Failed to delete Secret '{secret_name}': {e}")
    print("All matching resources deleted successfully.")

#TODO: Error handling
async def get_agent_pods_dictionary():
    pods = core_v1_api.list_namespaced_pod(namespace=get_current_namespace(), label_selector='observability-demo-framework=agent')
    pods_dict = {}
    for item in pods.items:
        name_parts = item.metadata.name.split("-")
        deployment_name = "-".join(name_parts[:-2])
        pods_dict[deployment_name]=item.metadata.name
    return pods_dict

@app.get("/simulation")
async def get_simulation():
    # Get the secret
    secret_name="obs-demo-fw-state"
    items = []
    try:
        secret = core_v1_api.read_namespaced_secret(secret_name, get_current_namespace())
        if 'simulation' in secret.data:
            encoded_json_data = secret.data['simulation']
            decoded_json_data = base64.b64decode(encoded_json_data).decode('utf-8')
            print(decoded_json_data)
            
            # Convert the decoded string back into a JSON object
            items = json.loads(decoded_json_data)
        else:
            print(f"Secret '{secret_name}' does not contain 'json-file' key.")
            return []
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{get_current_namespace()}'.")
        else:
            print(f"Failed to read Secret '{secret_name}': {e}")
        return []
    # Update agent metrics and pod name
    pods = await get_agent_pods_dictionary()
    for item in items:
        if item['group'] != "nodes":
            continue
        ip = item['data']['ip']
        id = item['data']["id"]
        metrics = agent_manager.get_agent_metrics(id)
        print(f"Pod: {pods[id]}. Metrics: {metrics}")
        item["pod"] = pods[id]
        item["metrics"] = metrics
    return items

#TODO: Error handling
@app.post("/kick")
async def agent_kick(payload: dict[str, Any]):
    print(payload)
    return agent_manager.kick(payload)

@app.post("/metrics")
async def create_agent_metric(payload: dict[str, Any]):
    await agent_manager.set_agent_metrics("POST", payload=payload)


@app.patch("/metrics")
async def modify_agent_metric(payload: dict[str, Any]):
    await agent_manager.set_agent_metrics("PATCH", payload=payload)