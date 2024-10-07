import React, { createContext, useState, useContext } from 'react';

const SimulationContext = createContext();

export const SimulationProvider = ({ children }) => {
  const [simulationData, setSimulationData] = useState([]);

  return (
    <SimulationContext.Provider value={{ simulationData, setSimulationData }}>
      {children}
    </SimulationContext.Provider>
  );
};

export const useSimulation = () => useContext(SimulationContext);