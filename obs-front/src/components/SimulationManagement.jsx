import React from 'react';
import * as ApiHelper from '../ApiHelper'

const SimulationManagement = ({ simulation, onSimulationUpdated }) => {


    const handleCreate = async () => {        
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(simulation)
            });

            const result = await response.json();
            onSimulationUpdated(result, "CREATE")
            console.log('Success:', result);
        } catch (error) {
            console.error('Error:', error);
        }
    };

    const handleReset = async () => {
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(), {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(simulation)
            });

            const result = await response.json();
            console.log('Simulation reset');
            onSimulationUpdated([], "RESET");
        } catch (error) {
            console.error('Error:', error);
        }
    };

    const isCreateSimuDisabled = () => {
        console.log("Evaluating create simulation")
        return !simulation || simulation.length == 0 || (simulation.length > 0 && simulation[0].data.ip)
    }

    const isResetSimuDisabled = () => {
        console.log("Evaluating reset simulation")
        return !simulation || simulation.length == 0 || (simulation.length > 0 && !(simulation[0].data.ip))
    }

    return (
        <div>
            <div><button disabled={isCreateSimuDisabled()} onClick={handleCreate}>Create</button></div>
            <div><button disabled={isResetSimuDisabled()} onClick={handleReset}>Reset</button></div>
        </div>
    );
};

export default SimulationManagement;