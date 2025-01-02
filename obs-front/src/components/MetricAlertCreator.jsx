import React, { useState } from "react";

const MetricAlertCreator = ({ metricName, onSubmit, onCancel }) => {
    const [selectedExpression, setSelectedExpression] = useState("<");
    const [selectedSeverity, setSelectedSeverity] = useState("Information");
    const [alertThreshold, setAlertThreshold] = useState("");

    const handleSelect = (value) => {
        setSelectedExpression(value);
    };

    const handleSelectSeverity = (value) => {
        setSelectedSeverity(value);
    }

    const handleChangeThreshold = (e) =>{
        setAlertThreshold(e.target.value);
    }

    return (

        <div className="container mt-4">
            <div className="row">
                <h5>Define alert</h5>
            </div>
            <div className="row align-items-center">

                <div className="col-3">
                    <label htmlFor="dropdown" className="form-label mb-0">
                        {metricName}
                    </label>
                </div>

                <div className="dropdown col-1">
                    <button
                        className="btn btn-secondary btn-sm dropdown-toggle"
                        type="button"
                        id="dropdownMenuButton"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                        style={{ width: "45px" }}
                    >
                        {selectedExpression}
                    </button>
                    <ul className="dropdown-menu" aria-labelledby="dropdownMenuButton">
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect("<")}
                            >
                                &lt;
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect("≤")}
                            >
                                &le;
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect("=")}
                            >
                                =
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect("≠")}
                            >
                                &ne;
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect("≥")}
                            >
                                &ge;
                            </button>
                        </li>
                        <li>
                            <button
                                className="dropdown-item"
                                onClick={() => handleSelect(">")}
                            >
                                &gt;
                            </button>
                        </li>
                    </ul>
                </div>

                {/* input */}
                <div className="col-2">
                    <input
                        type="text"
                        className="form-control"
                        placeholder="Value"
                        onChange={handleChangeThreshold}
                    />
                </div>

                {/* severity */ }
                <div className="dropdown col-4">
                    <button
                        className="btn btn-secondary btn-sm dropdown-toggle"
                        type="button"
                        id="dropdownMenuButton"
                        data-bs-toggle="dropdown"
                        aria-expanded="false"
                        style={{width: "100px"}}
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
                    <button type="button" className="agent-button" style={{ width: "40px" }} onClick={()=> onSubmit(metricName, selectedExpression, alertThreshold, selectedSeverity)}>
                        Submit
                    </button>
                </div>
                <div className="col-1">
                    <button type="button" className="agent-button" style={{ width: "40px" }} onClick={onCancel}>
                        Cancel
                    </button>
                </div>
            </div>

        </div>
    );
};

export default MetricAlertCreator;