import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'
import LayoutCanvas from '../components/LayoutCanvas';
import SimulationManagement from '../components/SimulationManagement';
import AgentList from '../components/AgentList';
import AgentInfo from '../components/AgentInfo';
import AgentTypePicker from '../components/AgentTypePicker';
import AlertManagement from '../components/AlertManagement';
import { useKeycloak } from "@react-keycloak/web";


const SimulationPage = ({ selectedUser }) => {

  const agentTypes = [
    { type: "customer", image: "logo-customer.svg", enabled: true },
    { type: "waiter", image: "logo-waiter.svg", enabled: true },
    //{ type: "java", image: "logo-java.png", enabled: false },
    { type: "cook", image: "logo-cook.svg", enabled: true }
  ]
    
  const [layout, setLayout] = useState([])
  const [agents, setAgents] = useState([])
  const [alerts, setAlerts] = useState([])
  const [selectedAgent, setSelectedAgent] = useState({});
  const [selectedAgenType, setSelectedAgentType] = useState(agentTypes[0]);
  const [simulationLoaded, setSimulationLoaded] = useState(false);
  const { keycloak, initialized } = useKeycloak();
  const [currentNamespaceLoaded, setCurrentNamespaceLoaded] = useState("");


  const agentsRef = useRef([]);
  const layoutRef = useRef([]);

  // Keep refs updated (cytoscape inside a closure)
  useEffect(() => {
    agentsRef.current = agents;
    layoutRef.current = layout;    
  }, [agents, layout]);

  function handleCreateSimulation(updatedAgents) {
    // Set agent list information.     
    setAgents(updatedAgents);
    // All simulation information has been saved
    setSimulationLoaded(true);
  }

  function handleResetSimulation() {
    // Clean canvas
    setLayout([]);
    // Clean agents
    setAgents([]);
    // Clean agent Id selected
    setSelectedAgent({});
    // Unload the simulation
    setSimulationLoaded(false);
    // Set agent type to first one
    setSelectedAgentType(agentTypes[0]);
  }

  // Selected from layout canvas
  const onNodeSelected = useCallback((node) => {
    if (!node) {
      setSelectedAgent({});
      return;
    }
    const agent = agentsRef.current.find(a => a.id === node.id);
    setSelectedAgent(agent);
  }, []);

  // Selected from agent list
  const onAgentSelected = useCallback((agent) => {
    if (!agent) {
      setSelectedAgent({})
      return
    }
    setSelectedAgent(agent)
  })

  function handleLayoutUpdate(updatedLayout) {
    // update layout in state.
    const structure = updatedLayout.map((element) => {
      if (element.isNode()) {
        return {
          group: 'nodes',
          data: element.data(),
          position: element.position(),
        };
      } else if (element.isEdge()) {
        return {
          group: 'edges',
          data: element.data(),
        };
      }
    });
    setLayout(structure);
    // Reconcile agent information.
    const updatedAgents = []
    //   create nodes
    structure.forEach(element => {
      if (element["group"] === "nodes") {
        updatedAgents.push({
          id: element["data"]["id"],
          type: element["data"]["styleType"],
          metrics: [],
          nextHop: []
        })
      }
    });
    //   create edges
    structure.forEach(element => {
      if (element["group"] === "edges") {
        const agent = updatedAgents.find(e => e.id === element["data"].source)
        agent.nextHop.push(element["data"].target)
      }
    });
    setAgents(updatedAgents)
  }

  function handleAgentTypeChanged(selectedIndex) {    
    setSelectedAgentType(agentTypes[selectedIndex])
  };

  function handleAgentUpdated(agent) {

    // Make a shallow copy of the agents array to ensure a new reference
    const updatedAgents = [...agents];

    // If necessary, update the specific agent's data within the simulation array
    const agentIndex = updatedAgents.findIndex(a => a.id === agent.id);
    if (agentIndex !== -1) {
      updatedAgents[agentIndex] = { ...updatedAgents[agentIndex], metrics: agent.metrics };
    }

    // Update the simulation state with the new array reference
    setAgents(updatedAgents);

    // Update alerts

    fetchAlerts();
  }

  const fetchAlerts = async () => {
    try {
      const alertListResponse = await fetch(ApiHelper.getClusterAlertDefinitionUrl(), {
        method: "GET",
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${keycloak.token}` 
       }});
      if (alertListResponse.status > 299) {
        setAlerts([]);
      }
      else {
        const alerts_json = await alertListResponse.json();
        setAlerts(alerts_json);
      }
    } catch(error) {
      //TODO: Global error handling
      console.error("Error fetching alerts", error);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      const apiUrl = ApiHelper.getSimulationUrl(selectedUser?.username);
      
      try {
        const requestResponse = await fetch(apiUrl, {
          method: "GET", 
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${keycloak.token}` 
          }
        });
        if (requestResponse.status > 299) {
          console.log("No simulation available", apiUrl);
          setAgents([]);
          setLayout([]);
          setSimulationLoaded(false)
        }
        else {          
          const simulation_json = await requestResponse.json();
          setAgents(simulation_json.agents);
          setLayout(simulation_json.layout);
          setSimulationLoaded(simulation_json.layout.length)
          setCurrentNamespaceLoaded(selectedUser?.username);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
    fetchAlerts();
  }, [keycloak.token, keycloak.authenticated, selectedUser]);

  return (
    <div className="container">      
      <div className="row">
        <div className="col-12">
          <h2>Communications<code>[{selectedUser?.monitoringType}]</code></h2>
          {!simulationLoaded && (
            <AgentTypePicker
              nodeTypes={agentTypes}
              onSelectionChange={handleAgentTypeChanged}
              selectedAgent={selectedAgent}></AgentTypePicker>
          )}
          <LayoutCanvas
            readOnly={simulationLoaded}
            layout={layout}
            onLayoutChanged={handleLayoutUpdate}
            nodeIdSelected={selectedAgent?.id}
            onNodeSelected={onNodeSelected}
            nodeType={selectedAgenType.type}
          />
          <SimulationManagement
            simulationLoaded={simulationLoaded}
            simulation={{ layout: layout, agents: agents, user: selectedUser}}
            onSimulationCreated={handleCreateSimulation}
            onSimulationReset={handleResetSimulation} />
        </div>
      </div>
      {simulationLoaded && (
        <div>
          <div className='row'>
            <div className="col-12 col-xl-6 border rounded mt-3">
              <h2>Agents</h2>
              <AgentList
                agents={agents}
                selectedAgentId={selectedAgent?.id}
                onAgentSelected={onAgentSelected} />
            </div>
            <div className="col-12 col-xl-6 border rounded mt-3">
              <AgentInfo agent={selectedAgent} onAgentUpdated={handleAgentUpdated} />
            </div>
          </div>
          <div className="row mt-3">
            <AlertManagement alerts={alerts} onAlertsUpdated={fetchAlerts}></AlertManagement>
          </div>
        </div>
      )}

    </div>
  );
}

export default SimulationPage;