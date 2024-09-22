# DESCRIPTION

## Wave 1
Front + API for create agent with custom prometheus metrics, basic logging capabilities and association for showing tracing features based on OpenTelemetry. 
- All agents on the demo will be NodeJS based. API is Python and the Observability Demo Framework Frontend is ReactJS. Create agents
- Create Prometheus metrics and expose them througn a custom Prometheus port. TODO: Define which kind of metrics we can setup. 
- Set an alert manager receiver in the Front. 

# TARGET MVP

+ Persistence handling
+ Metrics Management
+ OpenTelemetry implementation
+ Design rationalization
+ Error handling
+ Testability

## SPRINT 9: Persistence handling
- Remove panel movement from graphic.
- Remove selection option from graphic canvas.
- Create a secret with the simulation json content. 
* Remove json debug information. 
* Block form until the create simulation or reset simulation is completed. 
- Remove logging information in frontend.
* Build container image in the Cluster (obs-front)

# BACKLOG
* Detect if the cluster has User Workload monitoring enabled in the Cluster Info section.
* Detect installed operators. 
+ Add api readiness to the displayed pods. 
* Associate pods to svc or deployment?
+ Configure access to a cluster from the frontend
* Define capabilities of node client API (As annotation observabililty-framework-demo-capabilities: cap1,cap3)
* Cytoscape persistence
* Security: CORS for master API
* Add metrics management from Agent List (Add remove, configure, etc). 

# BRAINSTORMING

null

# CLOSED

## SPRINT 8: First PoC. 
- Implement kick operation in the obs-client-api-node
- Added historic Malaga football players names to agents. 
- Make structure available to the app.
- Avoid zooming in the graphic. 
- Create all simulation in the cluster. Creates client pods, 
- Create all simulation in the cluster. Add a label to the pods to easily identify them when created after simulation
+ Create all simulation in the cluster. Annotate node position in cytoscape with serialized stringfied json
+ Create all simulation in the cluster. Annotate node with next-hops 
- Create all simulation in the cluster. Send back the structure for filling the Agents table with IP, references, etc
- Implement cluster info access.
- Add built image to the pod creation (node client API).
- Identify if running on pod (service account authentication) or desktop (kubeconfig authentication)
- Call the kick operation from the AgentList React Component
- Build container image in the Cluster (obs-main-api)
- Change the React Icon 
- Change the React App title

## SPRINT 7
- Canvas for creating and associate nodes 
- Canvas delete nodes and associations
- Canvas react integration

## SPRINT 6
- Add prometheus custom metrics observability functionality to node client API
- Build container obs-client-api-node based on RH images.

## SPRINT 5
- List pod status.
- Build container image in the Cluster (obs-client-api-node)
- Add links to cluster console

## SPRINT 4
- Add option to create pod from the frontend
- Improve style in the front (list)
- Improve style in the front (button and layout)

## SPRINT 3
- Show pods matching a specific annotation (observability-demo-framework: agent). 
- Show namespace and IP in the listed pods in the frontend
- Delete pod list if the master API is not available. 
- Finalize the abstract

## SPRINT 2
- obs-main-api returns a list of pods at GET /obs-agents
- obs-front displays recurrently the modified list. 

## SPRINT 1 
- Create ReactJS framework: obs-front
- Create Python Master API: obs-main-api
- Create NodeJS Client API: obs-client-api-node