import React, { useState } from "react";

const MetricAlertCreator = ({ metricName, availableOperators, onSubmit, onCancel }) => {
    const [selectedExpression, setSelectedExpression] = useState(availableOperators[0]);
    const [selectedSeverity, setSelectedSeverity] = useState("Information");
    const [alertThreshold, setAlertThreshold] = useState("");
    const [error, setError] = useState("");

    const handleSelect = (value) => {
        setSelectedExpression(value);
    };

    const handleSelectSeverity = (value) => {
        setSelectedSeverity(value);
    }

    const isNumber = (n) => {
        return !isNaN(n) && n.trim() !== "";
    }

    const handleChangeThreshold = (e) => {
        setAlertThreshold(e.target.value);
        if (!isNumber(e.target.value)) {
            setError("Threshold is not a number");
        }
        else {
            setError("");
        }
    }

    const handleSubmitInformation = (metric, expression, threshold, severity) => {
        // Validation
        if (!isNumber(threshold)) {
            setError("Threshold is not a number");
            return;
        }
        setError("");
        // Submit to the parent
        onSubmit(metric, expression, threshold, severity);
    }

    return (
        <div className="container mt-4 border rounded mb-3">
            <div className="row">
                <h5>Define alert</h5>
            </div>
            <div className="row align-items-center mb-3">
                <div className="col-3 text-end">
                    <label htmlFor="dropdown" className="label form-label mb-0 text-end">
                        {metricName}
                    </label>
                </div>
                <div className="dropdown col-1">
                    <button
                        className="btn label btn-sm dropdown-toggle"
                        type="button"
                        id="dropdownMenuButton"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                        style={{ width: "45px" }}
                    >
                        {selectedExpression}
                    </button>
                    <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton">
                        {availableOperators.map((op) => (
                            <li key={op}>
                                <button
                                    className="dropdown-item"
                                    onClick={() => handleSelect(op)}
                                >
                                    {op}
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* input */}
                <div className="col-2">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Threshold"
                        onChange={handleChangeThreshold}
                    />
                </div>

                {/* severity */}
                <div className="dropdown col-4">
                    <button
                        className="btn label btn-sm dropdown-toggle"
                        type="button"
                        id="dropdownMenuButton"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                        style={{ width: "100px" }}
                    >
                        {selectedSeverity}
                    </button>
                    <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton">
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelectSeverity("Information")}
                            >
                                Information
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelectSeverity("Warning")}
                            >
                                Warning
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelectSeverity("Error")}
                            >
                                Error
                            </button>
                        </li>
                    </ul>
                </div>
                {/* button */}
                <div className="col-1">
                    <button type="button" className="agent-button" style={{ width: "40px" }} onClick={() => handleSubmitInformation(metricName, selectedExpression, alertThreshold, selectedSeverity)}>
                        Submit
                    </button>
                </div>
                <div className="col-1">
                    <button type="button" className="agent-button" style={{ width: "40px" }} onClick={onCancel}>
                        Cancel
                    </button>
                </div>
            </div>
            {/* Validation Error Message */}
            {error && (
                <div className="alert alert-danger" role="alert">{error}</div>
            )}

        </div>
    );
};

export default MetricAlertCreator;