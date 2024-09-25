import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';

const SimulationManagement = ({ simulation, onSimulationUpdated }) => {
    const [isCreateDisabled, setIsCreateDisabled] = useState(true);
    const [isResetDisabled, setIsResetDisabled] = useState(true);

    // Use useEffect to trigger logic when 'simulation' prop changes
    useEffect(() => {
        setIsCreateDisabled(isCreateSimuDisabled());
        setIsResetDisabled(isResetSimuDisabled());
    }, [simulation]);

    const handleCreate = async () => {        
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(simulation),
            });

            const result = await response.json();
            onSimulationUpdated(result, "CREATE");
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
                body: JSON.stringify(simulation),
            });

            const result = await response.json();
            console.log('Simulation reset', result);
            onSimulationUpdated([], "RESET");
        } catch (error) {
            console.error('Error:', error);
        }
    };

    const isCreateSimuDisabled = () => {
        console.log("Evaluating create simulation");
        return !simulation || simulation.length === 0 || (simulation.length > 0 && simulation[0].data.ip);
    };

    const isResetSimuDisabled = () => {
        console.log("Evaluating reset simulation");
        return !simulation || simulation.length === 0 || (simulation.length > 0 && !(simulation[0].data.ip));
    };

    return (
        <div>
            <div>
                <button disabled={isCreateDisabled} onClick={handleCreate}>
                    Create
                </button>
            </div>
            <div>
                <button disabled={isResetDisabled} onClick={handleReset}>
                    Reset
                </button>
            </div>
        </div>
    );
};

export default SimulationManagement;
