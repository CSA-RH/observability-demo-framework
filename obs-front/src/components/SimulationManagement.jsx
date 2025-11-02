import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { notifySuccess, notifyError } from '../services/NotificationService';
import { useLoading } from '../context/LoadingContext';

const SimulationManagement = ({ simulationLoaded, simulation, onSimulationCreated, onSimulationReset }) => {
    const [isCreateDisabled, setIsCreateDisabled] = useState(true);
    const [isResetDisabled, setIsResetDisabled] = useState(true);
    const { showLoading, hideLoading } = useLoading();
    const { keycloak, initialized } = useKeycloak();


    // Use useEffect to trigger logic when 'simulation' prop changes
    useEffect(() => {
        setIsCreateDisabled(isCreateSimuDisabled());
        setIsResetDisabled(isResetSimuDisabled());
    }, [simulation]);

    const handleCreate = async () => {
        showLoading(); // Start loading and show the spinner
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(simulation?.user?.username), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${keycloak.token}`
                },
                body: JSON.stringify(simulation),
            });

            const agentsUpdated = await response.json();
            if (response.status <= 299) {
                notifySuccess("Simulation created");
            }
            else
            {
                notifyError(`Error creating simulation: ${(agentsUpdated?.message || "No info available")}[${response.status}]`);
            }
            onSimulationCreated(agentsUpdated);
        } catch (error) {
            notifyError(`Error:${error}`);
        } finally {
            hideLoading(); // Stop loading and hide the spinner
        }
    };

    const handleReset = async () => {
        showLoading();
        try {
            if (simulationLoaded) {
                const response = await fetch(ApiHelper.getSimulationUrl(simulation?.user?.username), {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        Authorization: `Bearer ${keycloak.token}`
                    },
                    body: JSON.stringify(simulation),
                });
                if (response.status != 204) {
                    const errorMessageJson = await response.json();
                    const errorMessage = errorMessageJson?.message;
                    notifyError(`Error deleting simulation[${response.status}].\n${(errorMessage || "")}`);

                }
                else {
                    notifySuccess("Simulation reset successfully.");
                }
            }
            onSimulationReset({ layout: [], agents: [] });
        } catch (error) {
            notifyError("Error: " + error);
        } finally {
            hideLoading();
        }
    };

    const isCreateSimuDisabled = () => {
        return !simulation || simulation?.layout.length === 0 || simulationLoaded;
    };

    const isResetSimuDisabled = () => {
        return !simulation || simulation.length === 0;
    };

    return (

        <div className="d-flex justify-content-center">
            <button className="btn btn-primary me-2 mb-2" id="primary-button" disabled={isCreateDisabled} onClick={handleCreate}>
                Create
            </button>
            <button className="btn btn-secondary me-2 mb-2" id="primary-button" disabled={isResetDisabled} onClick={handleReset}>
                Reset
            </button>
        </div>
    );
};

export default SimulationManagement;
