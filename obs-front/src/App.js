import React, { useState, useEffect, useRef } from 'react';
import AgentList from './components/AgentList';
import SimulationManagement from './components/SimulationManagement'
import ClusterInfo from './components/ClusterInfo';
import AgentCanvas from './components/AgentCanvas';
import AgentInfo from './components/AgentInfo';
import * as ApiHelper from './ApiHelper'

import './App.css'

function App() {
  const [selectedAgentData, setSelectedAgentData] = useState(null);
  const [simulation, setSimulation] = useState([]);
  const [canvasLocked, setCanvasLocked] = useState(false);
  const simulationContext = useRef([]);

  function handleCanvasChange(graphData) {
    // For propagating the canvas change to other components.
    console.log("handleCanvasChange")
    setSimulation(graphData);
  }

  function handleSimulationChange(simulation, action) {
    switch (action) {
      case 'CREATE':
        simulationContext.current = simulation;
        setSimulation(simulation);
        setCanvasLocked(true);
        break;
      case 'RESET':
        console.log('Reset clicked!');
        simulationContext.current = [];
        setSimulation([]);
        setCanvasLocked(false);
        setSelectedAgentData(null);
        break;
      default:
        console.log(`Action ${action} not recognized.`);
    }
  }

  function handleSelectedAgent(agent) {
    console.log("handleSelectedAgent")
    let agentData = null;
    if (agent) {
      agentData = simulationContext.current?.find(a => a.data.id === agent.id);
    }
    console.log(agentData);
    setSelectedAgentData(agentData);
  }

  function handleAgentUpdated(agent) {
    console.log("Agent updated:", agent);

    // Make a shallow copy of the simulation array to ensure a new reference
    const updatedSimulation = [...simulation];

    // If necessary, update the specific agent's data within the simulation array
    const agentIndex = updatedSimulation.findIndex(a => a.data.id === agent.data.id);
    if (agentIndex !== -1) {
      updatedSimulation[agentIndex] = { ...updatedSimulation[agentIndex], metrics: agent.metrics };
    }

    // Update the simulation state with the new array reference
    setSimulation(updatedSimulation);

  }

  useEffect(() => {
    const fetchData = async () => {
      try {
        console.log("Loading data")
        const response = await fetch(ApiHelper.getSimulationUrl());
        const result = await response.json();
        simulationContext.current = result;
        setSimulation(result);
        setCanvasLocked(result.length > 0)
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, []); // Empty dependency array to run once on component mount

  return (
    <div className="App">
      <h1>Observability Demo Framework</h1>
      <ClusterInfo></ClusterInfo>
      <h2>Communications</h2>
      <AgentCanvas
        onAgentSelect={handleSelectedAgent}
        locked={canvasLocked}
        simulation={simulation}
        onSimulationUpdated={handleCanvasChange}></AgentCanvas>
      <SimulationManagement
        simulation={simulation}
        onSimulationUpdated={handleSimulationChange}></SimulationManagement>
      {simulationContext.current != null && simulationContext.current.length > 0 && (
        <div>
          <h2>Agents</h2>
          <AgentList simulation={simulation} agent={selectedAgentData}></AgentList>
          <h2>Selected Agent</h2>
          <AgentInfo
            agent={selectedAgentData}
            onAgentUpdated={handleAgentUpdated}></AgentInfo>          
        </div>
      )}
    </div>
  );
}

export default App;
