import React, { useState, useEffect } from 'react';
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

  function handleCanvasChange(simulation) {
    // For propagating the canvas change to other components.
    setSimulation(simulation);
  }

  function handleSimulationChange(graphData, action) {
    switch (action) {
      case 'CREATE':
        setSimulation(graphData);
        setCanvasLocked(true);
        break;
      case 'RESET':
        console.log('Reset clicked!');
        setSimulation([]);
        setCanvasLocked(false);
        setSelectedAgentData(null);
        break;
      default:
        console.log(`Action ${action} not recognized.`);
    }
  }

  useEffect(() => {
    const fetchData = async () => {
        try {
            console.log("Loading data")
            const response = await fetch(ApiHelper.getSimulationUrl());
            const result = await response.json();
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
      <h1>OpenShift Observability Demo Framework</h1>
      <h2>Cluster Info</h2>
      <ClusterInfo></ClusterInfo>
      <h2>Communications</h2>
      <AgentCanvas
        onAgentSelect={setSelectedAgentData}
        locked={canvasLocked}
        simulation={simulation}
        onSimulationUpdated={handleCanvasChange}></AgentCanvas>
      <SimulationManagement
        simulation={simulation}
        onSimulationUpdated={handleSimulationChange}></SimulationManagement>
      <h2>Selected Element Info</h2>
      <AgentInfo agent={selectedAgentData}></AgentInfo>
      <h2>Agents</h2>
      <AgentList simulation={simulation}></AgentList>
    </div>
  );
}

export default App;
