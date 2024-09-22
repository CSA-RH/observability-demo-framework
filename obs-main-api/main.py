from fastapi import FastAPI                        # type: ignore  
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from kubernetes import client, config, watch       # type: ignore
from kubernetes.client.rest import ApiException    # type: ignore
import os
from typing import List, Dict, Any
import time
import json
import http.client
import socket  
import base64

app = FastAPI()
#TODO: Improve security. CORS 
origins = [
#    "http://localhost:3000",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        print("Running in-cluster. Service account loaded.")
    except config.ConfigException:
        # Fallback to local kubeconfig if running outside the cluster
        config.load_kube_config()
        print("Running out-of-cluster. Local kubeconfig loaded.")

# Initialize Kubernetes API clients
load_kube_config()
v1 = client.CoreV1Api()
api_instance = client.CustomObjectsApi()

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
        console_resource = api_instance.get_cluster_custom_object(
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
        "ConsoleURL": console_url
    }

@app.get("/obs-agents")
async def get_living_agents():
    items = v1.list_pod_for_all_namespaces(watch=False).items
    
    result = list(filter(lambda y: y["annotations"] != None and 
            "observability-demo-framework" in y["annotations"] and
            y["annotations"]["observability-demo-framework"] == "agent" , 
        [{"name": x.metadata.name, 
          "namespace": x.metadata.namespace, 
          "ip": x.status.pod_ip, 
          "annotations": x.metadata.annotations, 
          "status": x.status.phase} for x in items]))
    return result

@app.post("/agent")
async def get_living_agents():
    print("Creating a new agent")
     # Create pod manifest
    pod_manifest = {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {
            'annotations': {
                'observability-demo-framework': 'agent',
                'observabililty-framework-demo-capabilities': 'default'
            },
            'generateName': 'agent-'
        },
        'spec': {
            'containers': [{
                'name': 'core',
                'image': 'openshift/hello-openshift',
            }]            
        }
    }
    #TODO: Improve response by using HTTP codes and payload.
    response = v1.create_namespaced_pod(body=pod_manifest)
    #print(response)
    return True

def wait_for_pod_ready_and_get_ip(namespace, pod_name, timeout=300):
    """
    Wait for the Pod to be ready and retrieve its internal IP address.
    """
    w = watch.Watch()
    start_time = time.time()

    try:
        for event in w.stream(v1.list_namespaced_pod, namespace=namespace, timeout_seconds=timeout):
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
        v1.create_namespaced_secret(get_current_namespace(), secret)
        print(f"Simulation saved successfully in the cluster as secret obs-demo-fw-state.")
    except client.ApiException as e:
        print(f"Exception when saving simulation as a secret[obs-demo-fw-state]: {e}")


#TODO: Mostly happy path. Add exceptions and error handling
@app.post("/simulation")
async def create_simulation(payload: List[Dict[str, Any]]):
    #current_namespace = active_context['context'].get('namespace', 'default')
    print("Creating pods")    
    for item in payload: 
        if item["group"] == "nodes":            
            print(f'Agent: {item["data"]["id"]}')
            print("----")
            pod_manifest = {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {
                    'labels': {
                        'app': 'observability-demo-framework-agent'
                    },
                    'annotations': {
                        'observability-demo-framework': 'agent',
                        'observability-demo-framework/capabilities': 'default',
                        'observability-demo-framework/position-x': str(item["position"]["x"]),
                        'observability-demo-framework/position-y': str(item["position"]["y"])
                    },
                    'name': item["data"]["id"]
                },
                'spec': {
                    'containers': [{
                        'name': 'core',
                        'image': 'obs-client-node:latest',
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
            #TODO: Improve response by using HTTP codes and payload.
            response = v1.create_namespaced_pod(body=pod_manifest, namespace = get_current_namespace())
    print("Retrieve Pod IP")
    for item in payload: 
        if item["group"] == "nodes":
            print(f'Agent: {item["data"]["id"]}')
            internal_ip = wait_for_pod_ready_and_get_ip(get_current_namespace(), item["data"]["id"])
            if internal_ip:
                print(f"The internal IP address of Pod {item["data"]['id']} is: {internal_ip}")
                item["data"]["ip"] = internal_ip
            else:
                print(f"Failed to retrieve the IP address for Pod {item["data"]['id']}.")
                continue
    print("Udpate the edges and the apis")
    print("Retrieve Pod IP")
    for item in payload: 
        if item["group"] == "edges":
            sourceName = item["data"]["source"]
            targetName = item["data"]["target"]
            sourceAgent = get_agent_from_payload(sourceName, payload)
            targetAgent = get_agent_from_payload(targetName, payload)
            #Update next-hop in payload
            add_next_hop_to_agent(targetAgent["data"]["id"], sourceAgent)
            #Call IP 
            print(f"Calling POST http://{sourceAgent['data']['ip']}:8080/agents/{targetName} with destination ip {targetAgent["data"]["ip"]}")
            next_hop_address = {
                "ip": targetAgent["data"]["ip"],
                "port": 8080
            }
            json_next_hop_address = json.dumps(next_hop_address)
            try:
                conn = http.client.HTTPConnection(sourceAgent['data']['ip'], 8080, timeout=2)
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
    #Save the json in a secret
    save_simulation_as_secret(payload)
    print(payload)
    return payload


@app.delete("/simulation")
async def delete_simulation():
    try:
        # Delete all pods in the namespace with the specified label selector
        _ = v1.delete_collection_namespaced_pod(
            namespace=get_current_namespace(), 
            label_selector="app=observability-demo-framework-agent"
        )        
        print("Pods deleted successfully")
    except client.ApiException as e:
        print(f"Exception when deleting pods: {e}")
    # Delete secret 
    secret_name="obs-demo-fw-state"
    try:
        v1.delete_namespaced_secret(secret_name, get_current_namespace())
        print(f"Secret '{secret_name}' deleted successfully.")
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{get_current_namespace()}'.")
        else:
            print(f"Failed to delete Secret '{secret_name}': {e}")

@app.get("/simulation")
async def get_simulation():
    secret_name="obs-demo-fw-state"
    try:
        secret = v1.read_namespaced_secret(secret_name, get_current_namespace())
        if 'simulation' in secret.data:
            encoded_json_data = secret.data['simulation']
            decoded_json_data = base64.b64decode(encoded_json_data).decode('utf-8')
            
            # Convert the decoded string back into a JSON object
            json_data = json.loads(decoded_json_data)
            return json_data
        else:
            print(f"Secret '{secret_name}' does not contain 'json-file' key.")
            return []
    except client.exceptions.ApiException as e:
        if e.status == 404:
            print(f"Secret '{secret_name}' not found in namespace '{get_current_namespace()}'.")
        else:
            print(f"Failed to read Secret '{secret_name}': {e}")
        return []

    
@app.post("/kick")
async def agent_kick(payload: dict[str, Any]):
    print(payload)
    agent_ip = payload['ip']
    agent_id = payload['id']
    kick_initial_count = payload['count']
    agent_kick_payload = {
        "count": kick_initial_count        
    }
    json_agent_kick_payload = json.dumps(agent_kick_payload)
    try:
        conn = http.client.HTTPConnection(agent_ip, 8080, timeout=2)
        headers = {
            'Content-Type': 'application/json'
        }
        # Make the POST request, attaching the JSON body
        print(f"Agent {agent_id}[{agent_ip}] kicking (count={kick_initial_count})...")
        conn.request("POST", "/kick", body=json_agent_kick_payload, headers=headers)
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
    return True