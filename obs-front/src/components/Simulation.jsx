import { useSimulation } from './SimulationContext'
import SimulationCanvasNew from './SimulationCanvasNew';
import SimulationManagementNew from './SimulationManagementNew';


const Simulation = ({onAgentSelected} ) => {

    const { simulationData, setSimulationData } = useSimulation();

    console.log(simulationData)
    
    return (
        <div>
            <h2>Communications</h2>
            <SimulationCanvasNew
                simulation={simulationData}                
                readOnly={false} 
                agentSelected={{}}
                onAgentSelected={()=>{}}/>
            <SimulationManagementNew
                simulation={simulationData}
                onSimulationCreated={() => { }}
                onSimulationReset={() => { }} />
        </div>

    )

}

export default Simulation;