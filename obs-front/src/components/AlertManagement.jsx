import React, { useState } from 'react';
import * as ApiHelper from '../ApiHelper.js'
import { useKeycloak } from "@react-keycloak/web";
import { notifyError, notifySuccess } from '../services/NotificationService.jsx';

const AlertManagement = ({ alerts, user, onAlertsUpdated }) => {

    const [addNewAlert, setAddNewAlert] = useState(false)
    const [validationError, setValidationError] = useState("");
    const [formData, setFormData] = useState({
        name: "",
        severity: "Information",
        evaluation: "1m",
        expression: "",
        summary: "",
    });
    const { keycloak, initialized } = useKeycloak();

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
        setValidationError(""); // Clear validation error on input change
    };


    const validateForm = () => {
        const nameRegex = /^[a-zA-Z_:][a-zA-Z0-9_:]*$/;
        if (!nameRegex.test(formData.name)) {
            return "Name must match the pattern [a-zA-Z_:][a-zA-Z0-9_:]*.";
        }
        if (formData.expression.trim() === "") {
            return "Expression field cannot be empty.";
        }
        return "";
    };

    async function saveAlert(alert) {
        try {
            console.log("TEST")
            const response = await fetch(ApiHelper.getClusterAlertDefinitionUrl(user?.username), {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${keycloak.token}`
                },
                body: JSON.stringify(alert)
            });
            if (response.status == 200){
                notifySuccess("Alert saved");
            }
            else {
                const responsePayload = response.json();
                notifyError(`Error saving alert[${response.status}]. ` + responsePayload?.message);
            }
        } catch (error) {
            notifyError('Error:', error);
        }
    }

    async function deleteAlert(alertName) {
        try {
            const response = await fetch(ApiHelper.getClusterAlertDefinitionUrl(user?.username), {
                method: "DELETE",
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${keycloak.token}`
                },
                body: JSON.stringify({
                    alert: alertName
                })
            });
            if (response.status == 200) {
                notifySuccess("Alert deleted.");
            }
            else {
                const responsePayload = response.json();
                notifyError(`Error deleting alert[${response.status}].` + responsePayload?.message);
            }
            return response;
        } catch (error) {
            notifyError('Error:', error);
        }
    }

    const handleNewAlertSubmit = async (e) => {        
        e.preventDefault();
        console.log("TESSST3");
        const error = validateForm();
        if (error) {
            setValidationError(error);
            return;
        }

        const newAlert = {
            name: formData.name,
            observabilityStack: user?.monitoringType,
            scope: "custom",
            severity: formData.severity,
            definition: {
                evaluation: formData.evaluation,
                expression: formData.expression,
                summary: formData.summary
            }
        };
        const response = await saveAlert(newAlert);
        if (response && response.status == 200) {
            onAlertsUpdated();
            setValidationError(""); // Clear any previous validation error
            setAddNewAlert(false);
        }
        else {
            if (response) {
                const responseJson = await response.json();
                console.log(responseJson.message);
                setValidationError(responseJson.message);
            }
            else {
                setValidationError("Error creating alert.");
            }
        }
    };

    const handleCancel = () => {
        setFormData({
            name: "",
            severity: "Information",
            evaluation: "1m",
            expression: "",
            summary: "",
        });
        setValidationError("");
        setAddNewAlert(false);
    };

    function handleEnableAddAlertForm() {
        setAddNewAlert(true);
    }

    const handleDeleteAlert = async (alertId) => {
        console.log(alertId)
        const response = await deleteAlert(alertId);
        onAlertsUpdated();
        if (response && response.status != 200) {
            const body = await response.json()
            console.error("Error deleting alert", body)
        }
    }

    return (
        <div className='col-12 border rounded'>
            <div className="d-flex align-items-center justify-content-between">
                <h2 className="mb-0">Alerts <a href={ApiHelper.getAlertRulesAddress()} target="_blank" rel="noopener noreferrer">
                    <i className="fas fa-external-link-alt"></i></a></h2>
                {!addNewAlert && (<button className="btn-circle btn-green" onClick={handleEnableAddAlertForm}><span>+</span></button>)}
            </div>

            {addNewAlert && (<div className="container mt-5">
                <form onSubmit={handleNewAlertSubmit}>
                    {/* Name Field */}
                    <div className="row mb-3">
                        <label htmlFor="name" className="col-sm-2 col-form-label">
                            Name
                        </label>
                        <div className="col-sm-10">
                            <input
                                type="text"
                                className="form-control"
                                id="name"
                                name="name"
                                value={formData.name}
                                onChange={handleChange}
                                placeholder="Enter name"
                            />
                        </div>
                    </div>

                    {/* Severity Field */}
                    <div className="row mb-3">
                        <label htmlFor="severity" className="col-sm-2 col-form-label">
                            Severity
                        </label>
                        <div className="col-sm-10">
                            <select
                                className="form-select"
                                id="severity"
                                name="severity"
                                value={formData.severity}
                                onChange={handleChange}
                            >
                                <option value="Information">Information</option>
                                <option value="Warning">Warning</option>
                                <option value="Error">Error</option>
                            </select>
                        </div>
                    </div>

                    {/* Evaluation Field */}
                    <div className="row mb-3">
                        <label htmlFor="evaluation" className="col-sm-2 col-form-label">
                            Evaluation
                        </label>
                        <div className="col-sm-10">
                            <select
                                className="form-select"
                                id="evaluation"
                                name="evaluation"
                                value={formData.evaluation}
                                onChange={handleChange}
                            >
                                <option value="1m">1m</option>
                                <option value="2m">2m</option>
                                <option value="3m">3m</option>
                            </select>
                        </div>
                    </div>

                    {/* Expression Field */}
                    <div className="row mb-3">
                        <label htmlFor="expression" className="col-sm-2 col-form-label">
                            Expression
                        </label>
                        <div className="col-sm-10">
                            <textarea
                                className="form-control"
                                id="expression"
                                name="expression"
                                rows="3"
                                style={{ fontFamily: "monospace" }}
                                value={formData.expression}
                                onChange={handleChange}
                                placeholder="Enter expression"
                            />
                        </div>
                    </div>

                    {/* Summary Field */}
                    <div className="row mb-3">
                        <label htmlFor="summary" className="col-sm-2 col-form-label">
                            Summary
                        </label>
                        <div className="col-sm-10">
                            <textarea
                                className="form-control"
                                id="summary"
                                name="summary"
                                rows="3"
                                value={formData.summary}
                                onChange={handleChange}
                                placeholder="Enter summary"
                            />
                        </div>
                    </div>

                    {/* Validation Error Message */}
                    {validationError && (
                        <div className="alert alert-danger" role="alert">
                            {validationError}
                        </div>
                    )}

                    {/* Buttons */}
                    <div className="row">
                        <div className="d-flex justify-content-center">
                            <button type="submit" className="btn btn-primary me-2" onClick={() => console.log("BUTTON CLICKED")}>
                                Submit
                            </button>
                            <button type="button" className="btn btn-secondary" onClick={handleCancel}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </form>
            </div>)}
            <div className='table-responsive'>
                {alerts != null && alerts.length > 0 && (
                    <table className='table w-100'>
                        <thead>
                            <tr>
                                <th></th>
                                <th>Name</th>
                                <th>Severity</th>
                                <th>Type</th>
                                <th>Evaluation</th>
                                <th>PromQL</th>
                                <th>Summary</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.map((item) => (
                                <tr key={item.name}>
                                    <td>
                                        {item.scope == "custom" && (
                                            <button className="btn-circle btn-red"
                                                onClick={() => handleDeleteAlert(item.id)}>
                                                <span>&times;</span>
                                            </button>)}
                                    </td>
                                    <td>{item.name}</td>
                                    <td> <span className={"label label-container label-" + item.severity.toLowerCase()}>{item.severity}</span></td>
                                    <td><span className={"label"}> {item.scope} </span></td>
                                    <td><span className={"label"}>{item.evaluation}</span></td>
                                    <td><code>{item.promQL}</code></td>
                                    <td>{item.summary}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>)

}

export default AlertManagement;