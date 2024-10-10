import React, { useState, useEffect, useRef, useCallback } from 'react';

import * as ApiHelper from './ApiHelper'
import './App.css'

import Banner from './components/Banner'
import ClusterInfo from './components/ClusterInfo';
import LayoutCanvas from './components/LayoutCanvas';
import SimulationManagement from './components/SimulationManagement';
import AgentList from './components/AgentList';
import AgentInfo from './components/AgentInfo';



function App() {
  const [layout, setLayout] = useState([])
  const [agents, setAgents] = useState([])
  const [selectedAgent, setSelectedAgent] = useState({});
  const [simulationLoaded, setSimulationLoaded] = useState(false)

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

  function handleResetSimulation(simulation) {    
    // Clean canvas
    setLayout([]);
    // Clean agents
    setAgents([]);
    // Clean agent Id selected
    setSelectedAgent({});
    // Unload the simulation
    setSimulationLoaded(false);
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

  function handleAgentUpdated(agent) {
    console.log("Agent updated:", agent);

    // Make a shallow copy of the agents array to ensure a new reference
    const updatedAgents = [...agents];

    // If necessary, update the specific agent's data within the simulation array
    const agentIndex = updatedAgents.findIndex(a => a.id === agent.id);
    if (agentIndex !== -1) {
      updatedAgents[agentIndex] = { ...updatedAgents[agentIndex], metrics: agent.metrics };
    }

    // Update the simulation state with the new array reference
    setAgents(updatedAgents);
  }

  useEffect(() => {    
    const fetchData = async () => {
      try {        
        const requestResponse = await fetch(ApiHelper.getSimulationUrl());        
        if (requestResponse.status > 299) {
          console.log("No simulation available")
          setAgents([]);
          setLayout([]);
          setSimulationLoaded(false)  
        } 
        else {
          const simulation_json = await requestResponse.json();        
          setAgents(simulation_json.agents);
          setLayout(simulation_json.layout);
          setSimulationLoaded(simulation_json.layout.length > 0)
        }        
      } catch (error) {
        console.error('Error fetching data:', error);
      }      
    };

    fetchData();
  }, []); // Empty dependency array to run once on component mount

  return (
    <div className="App">
      <Banner title="Observability Demo Framework" />
      <ClusterInfo />
      <h2>Communications</h2>
      <LayoutCanvas
        readOnly={simulationLoaded}
        layout={layout}
        onLayoutChanged={handleLayoutUpdate}
        nodeIdSelected={selectedAgent?.id}
        onNodeSelected={onNodeSelected}
      />
      <SimulationManagement
        simulationLoaded={simulationLoaded}
        simulation={{ layout: layout, agents: agents }}
        onSimulationCreated={handleCreateSimulation}
        onSimulationReset={handleResetSimulation} />
      {simulationLoaded && (
        <div>
          <h2>Agents</h2>
          <AgentList 
            agents={agents} 
            selectedAgentId={selectedAgent?.id}
            onAgentSelected={onAgentSelected} />
          <h2>Selected Agent</h2>
          <AgentInfo agent={selectedAgent} onAgentUpdated={handleAgentUpdated} />
        </div>
      )}
    </div>
  );
}

export default App;