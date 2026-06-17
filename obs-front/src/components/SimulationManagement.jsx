import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { useKeycloak } from "@react-keycloak/web";
import { notifySuccess, notifyError } from '../services/NotificationService';
import { useLoading } from '../context/LoadingContext';

const SimulationManagement = ({ simulationLoaded, simulation, onSimulationCreated, onSimulationReset }) => {
    const [isCreateDisabled, setIsCreateDisabled] = useState(true);
    const [isResetDisabled, setIsResetDisabled] = useState(true);
    const { showLoading, hideLoading } = useLoading();
    const { keycloak } = useKeycloak();

    useEffect(() => {
        setIsCreateDisabled(isCreateSimuDisabled());
        setIsResetDisabled(isResetSimuDisabled());
    }, [simulation]);

    const formatOperationMessage = (operation) => {
        const statusLabel = ApiHelper.getOperationStatusLabel(operation.status);
        const detail = operation.metadata?.message;
        return detail ? `${statusLabel}: ${detail}` : statusLabel;
    };

    const handleCreate = async () => {
        showLoading('Submitting simulation...');
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(simulation?.user?.username), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${keycloak.token}`
                },
                body: JSON.stringify(simulation),
            });

            if (response.status === 202) {
                const { operationId } = await response.json();
                const operation = await ApiHelper.pollOperation(operationId, keycloak, {
                    onProgress: (currentOperation) => {
                        showLoading(formatOperationMessage(currentOperation));
                    },
                });
                notifySuccess("Simulation created");
                onSimulationCreated(operation.result);
                return;
            }

            const errorBody = await response.json();
            notifyError(`Error creating simulation: ${(errorBody?.message || errorBody?.detail || "No info available")}[${response.status}]`);
        } catch (error) {
            notifyError(`Error: ${error.message || error}`);
        } finally {
            hideLoading();
        }
    };

    const handleReset = async () => {
        showLoading('Submitting simulation reset...');
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

                if (response.status === 202) {
                    const { operationId } = await response.json();
                    await ApiHelper.pollOperation(operationId, keycloak, {
                        onProgress: (currentOperation) => {
                            showLoading(formatOperationMessage(currentOperation));
                        },
                    });
                    notifySuccess("Simulation reset successfully.");
                    onSimulationReset({ layout: [], agents: [] });
                } else {
                    const errorMessageJson = await response.json();
                    const errorMessage = errorMessageJson?.message;
                    notifyError(`Error deleting simulation[${response.status}].\n${(errorMessage || "")}`);
                }
            } else if (!simulationLoaded) {
                onSimulationReset({ layout: [], agents: [] });
            }
        } catch (error) {
            notifyError("Error: " + (error.message || error));
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
