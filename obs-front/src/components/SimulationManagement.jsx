import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { notifySuccess, notifyError } from '../services/NotificationService';

const SimulationManagement = ({ simulationLoaded, simulation, onSimulationCreated, onSimulationReset }) => {
    const [isCreateDisabled, setIsCreateDisabled] = useState(true);
    const [isResetDisabled, setIsResetDisabled] = useState(true);
    const [loading, setLoading] = useState(false);
    const { keycloak, initialized } = useKeycloak();

    // Use useEffect to trigger logic when 'simulation' prop changes
    useEffect(() => {
        setIsCreateDisabled(isCreateSimuDisabled());
        setIsResetDisabled(isResetSimuDisabled());
    }, [simulation]);

    const handleCreate = async () => {
        setLoading(true); // Start loading and show the spinner
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
            setLoading(false); // Stop loading and hide the spinner
        }
    };

    const handleReset = async () => {
        setLoading(true);
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
            setLoading(false); // Stop loading and hide the spinner
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
            {loading && (
                <div style={overlayStyles}>
                    <div style={spinnerStyles}></div>
                </div>
            )}

            <button className="btn btn-primary me-2 mb-2" id="primary-button" disabled={isCreateDisabled} onClick={handleCreate}>
                Create
            </button>
            <button className="btn btn-secondary me-2 mb-2" id="primary-button" disabled={isResetDisabled} onClick={handleReset}>
                Reset
            </button>
        </div>
    );
};

// Styles for the overlay and spinner
const overlayStyles = {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0, 0, 0, 0.5)", // semi-transparent background
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    zIndex: 1000, // Ensure it overlays everything
};

const spinnerStyles = {
    border: "16px solid #f3f3f3", // Light gray
    borderTop: "16px solid #3498db", // Blue
    borderRadius: "50%",
    width: "120px",
    height: "120px",
    animation: "spin 2s linear infinite", // Create the spinning animation
};

// CSS for the spinning animation
const styleSheet = document.styleSheets[0];
styleSheet.insertRule(`
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  `, styleSheet.cssRules.length);


export default SimulationManagement;
