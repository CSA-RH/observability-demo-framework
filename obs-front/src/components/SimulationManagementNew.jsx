import React, { useEffect, useState } from 'react';
import * as ApiHelper from '../ApiHelper';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';



const showError = (text) => {
    toast.error(text, {
        position: "top-right",
        autoClose: 3000,
        hideProgressBar: false,
        closeOnClick: true,
        width: 600,
        pauseOnHover: true,
        draggable: true,
        progress: undefined,
    });
}


const SimulationManagementNew = ({ simulation, onSimulationCreated, onSimulationReset }) => {
    const [isCreateDisabled, setIsCreateDisabled] = useState(true);
    const [isResetDisabled, setIsResetDisabled] = useState(true);
    const [loading, setLoading] = useState(false);

    // Use useEffect to trigger logic when 'simulation' prop changes
    useEffect(() => {
        setIsCreateDisabled(isCreateSimuDisabled());
        setIsResetDisabled(isResetSimuDisabled());
    }, [simulation]);

    const handleCreate = async () => {
        setLoading(true); // Start loading and show the spinner        
        try {
            const response = await fetch(ApiHelper.getSimulationUrl(), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(simulation),
            });

            const result = await response.json();
            onSimulationCreated(result);
            console.log('Success:', result);
        } catch (error) {
            //console.error('Error:', error);
            showError(`Error:${error}`, error)
        } finally {
            setLoading(false); // Stop loading and hide the spinner
        }
    };

    const handleReset = async () => {
        setLoading(true);
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
            onSimulationReset([]);
        } catch (error) {
            console.error('Error:', error);
        } finally {
            setLoading(false); // Stop loading and hide the spinner
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
        <div className="container-buttons">
            {/* Overlay and Spinner */}
            <ToastContainer></ToastContainer>
            {loading && (
                <div style={overlayStyles}>
                    <div style={spinnerStyles}></div>
                </div>
            )}
            <div>
                <button className="redhat-button" id="primary-button" disabled={isCreateDisabled} onClick={handleCreate}>
                    Create
                </button>
                <button className="redhat-button" id="primary-button" disabled={isResetDisabled} onClick={handleReset}>
                    Reset
                </button>
            </div>
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


export default SimulationManagementNew;
