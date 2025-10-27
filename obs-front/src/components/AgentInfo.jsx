import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper.js'
import MetricAlertCreator from './MetricAlertCreator.jsx';
import { useKeycloak } from "@react-keycloak/web";
import { notifySuccess, notifyError } from '../services/NotificationService';

const AgentInfo = ({ agent, userId, onAgentUpdated }) => {

    const allAlertOperators = ["<", "≤", "=", "≠", "≥", ">"]

    const [metrics, setMetrics] = useState(agent?.metrics || []);
    const [newMetric, setNewMetric] = useState({ name: "", type: "gauge", value: "" });
    const [error, setError] = useState("");
    const [alertEditorEnabled, setAlertEditorEnabled] = useState(false);
    const [metricAlertSelected, setMetricAlertSelected] = useState("");
    const [alertOperatorsAvailable, setAlertOperatorsAvailable] = useState(allAlertOperators);
    const { keycloak, initialized } = useKeycloak();

    useEffect(() => {
        if (agent) {
            setMetrics(agent.metrics || []);
        }
        else {
            setMetrics([])
        }
        setAlertEditorEnabled(false);
        setMetricAlertSelected("");

    }, [agent]);

    const handleMetricChange = (index, field, value) => {
        const updatedMetrics = metrics.map((metric, i) =>
            i === index ? { ...metric, [field]: value } : metric
        );
        setMetrics(updatedMetrics);
    };

    async function saveMetric(method, agent, metric) {
        const payload = {
            id: agent.id,
            ip: agent.ip,
            metric: metric
        }
        try {
            const response = await fetch(ApiHelper.getAgentsMetricsUrl(userId), {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${keycloak.token}` 
                },
                body: JSON.stringify(payload),
            });
            if (response.status == 200){
                notifySuccess("Metric saved.");
            } 
            else
            {
                var msg = "Error saving metrics.";
                const result = await response.json();
                if (result?.message) {
                    msg += `. \n${result.message}`;
                }
                notifyError(msg);
            }
        } catch (error) {
            notifyError("Error saving metric", error);
        }
    }

    const handleAddMetric = () => {
        // Validation: Name cannot be empty, must be unique, and value cannot be empty
        if (newMetric.name.trim() === "") {
            setError("Metric name cannot be empty.");
            return;
        }
        if (metrics.some(metric => metric.name === newMetric.name)) {
            setError("Metric name must be unique within the agent.");
            return;
        }
        if (newMetric.value.trim() === "") {
            setError("Metric value cannot be empty.");
            return;
        }
        //Metric name must comply with the name standard         
        if (!/^[a-zA-Z_:][a-zA-Z0-9_:]*$/.test(newMetric.name.trim())) {
            setError("Metric name not valid. Format [a-zA-Z_:][a-zA-Z0-9_:]*");
            return;
        }

        // Clear error and add new metric
        setError("");
        setMetrics([...metrics, newMetric]);
        agent.metrics = [...metrics, newMetric];
        //POST TO THE AGENT WITH NEW VALUE. 
        saveMetric("POST", agent, newMetric)
        onAgentUpdated(agent)
        setNewMetric({ name: "", type: "gauge", value: "" });
    };

    const handleUpdateMetric = (index) => {
        if (metrics[index].value.trim() === "") {
            setError("Metric value cannot be empty.");
            return;
        }
        setError("");
        agent.metrics = metrics;
        //PUT TO THE AGENT WITH THE NEW value METRIC. 
        saveMetric("PUT", agent, metrics[index])
        onAgentUpdated(agent)
        setMetrics(metrics);
    };

    const handleInputChange = (e) => {
        setNewMetric({
            ...newMetric,
            [e.target.name]: e.target.value,
        });
    };

    function getAvailableOperators(alerts) {
        var opAvailables = allAlertOperators;

        alerts?.map((item) => {
            opAvailables = opAvailables.filter(op => op !== item.definition.expression);
        })

        return opAvailables;
    }

    function handleEnableAlertCreator(index) {
        setAlertEditorEnabled(true);
        setAlertOperatorsAvailable(getAvailableOperators(metrics[index].alerts));
        setMetricAlertSelected(metrics[index].name);
    }

    const handleDeleteAlert = async (metricName, alertIndex) => {
        console.log("Metric:", metricName, ". Alert index:", alertIndex);
        var metricIndex = metrics.findIndex(item => item.name === metricName);
        const alertId = metrics[metricIndex].alerts[alertIndex].id;

        //Remove from the local data model
        metrics[metricIndex].alerts.splice(alertIndex, 1);

        //Remove from the backend
        const result = await deleteAlert(alertId);

        onAgentUpdated(agent);
        setMetrics(metrics);
    }

    const onAlertEditionCancel = (e) => {
        setAlertEditorEnabled(false);
        setMetricAlertSelected("");
    }

    async function saveAlert(alert) {
        try {
            const response = await fetch(ApiHelper.getClusterAlertDefinitionUrl(userId), {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${keycloak.token}`
                },
                body: JSON.stringify(alert)
            });
            const responsePayload = await response.json();
            if (response.status == 200){
                notifySuccess("Alert saved.");
                return responsePayload;
            }
            else {
                notifyError("Error saving alert. " && (responsePayload?.message || ""));
            }
        } catch (error) {
            notifyError('Error saving alert:', error);
        }
    }

    async function deleteAlert(alertName) {
        try {
            const response = await fetch(ApiHelper.getClusterAlertDefinitionUrl(userId, alertName), {
                method: "DELETE",
                headers: {
                    'Content-Type': 'application/json', 
                    Authorization: `Bearer ${keycloak.token}` 
                }
            });
            if (response.status != 204){
                notifySuccess("Alert deleted.");
            }
            else {
                responseContent = response.json();
                notifyError("Error saving alert. " + responseContent?.message);
            }
        } catch (error) {
            notifyError('Error', error);
        }
    }

    const onAlertEditionSubmit = async (metric, expression, value, severity) => {
        const alert = { expression: expression, severity: severity, value: value };
        const metricObject = agent.metrics.find((m) => m.name == metric);
        metricObject['alert'] = alert;

        const newAlertDefinition = {
            scope: "metricAgent",
            severity: severity,
            definition: {
                agent: agent.id,
                metric: metric,
                expression: expression,
                value: value
            }
        };
        (metricObject['alerts'] = metricObject['alerts'] ?? []).push(newAlertDefinition);
        //Update alert definition        
        const alert_info = await saveAlert(newAlertDefinition);
        newAlertDefinition.id = alert_info.id
        newAlertDefinition.name = alert_info.name
        //Notify to upper hierarchy
        onAgentUpdated(agent);
        //Update GUI
        setAlertEditorEnabled(false);
        setMetricAlertSelected("");
    }

    return (
        <div className='container'>
            {agent?.id ? (
                <div>
                    <h6>
                        <span className="value">
                            <a href={ApiHelper.globalRootConsole + '/k8s/ns/' + ApiHelper.globalCurrentNamespace + '/pods/' + agent.pod}
                                target="_blank" rel="noopener noreferrer">{agent.pod} <i className="fas fa-external-link-alt"></i></a>
                        </span> <span className="value">[{agent.ip}] metrics</span>
                    </h6>
                    <div>
                        <div className='table-responsive'>
                            <table className='table w-100'>
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>Value</th>
                                        <th>Actions</th>
                                        <th>Alert</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {metrics.map((metric, index) => (
                                        <tr key={metric.name}
                                            className={`${metricAlertSelected === metric.name ? 'table-active' : ''}`}>
                                            <td>
                                                <a key={index} className="label"
                                                    href={ApiHelper.getObserveLinkForMetric(metric.name, agent.id)}
                                                    target="_blank" rel="noopener noreferrer">{metric.name} <i className="fas fa-external-link-alt"></i></a>
                                            </td>
                                            <td>
                                                <span key={index} className="label">{metric.type || "gauge"}</span> {/* TODO: Gnapa fix */}
                                            </td>
                                            <td>
                                                <input
                                                    type="text"
                                                    value={metric.value}
                                                    onChange={(e) => handleMetricChange(index, "value", e.target.value)}
                                                    className='form-control'
                                                    style={{ width: "75px", textAlign: 'center' }}
                                                />
                                            </td>
                                            <td>
                                                <button className="agent-button" onClick={() => handleUpdateMetric(index)}>Update</button>
                                            </td>
                                            <td>
                                                <div className="container">
                                                    {metric.alerts && metric.alerts.map((alert, alertIndex) => (
                                                        <div key={alertIndex}
                                                            className={"mb-1 label label-container label-" + alert.severity.toLowerCase()}>
                                                            <span>{alert.definition.expression}</span>
                                                            <span>{alert.definition.value}</span>
                                                            <span>[{alert.severity}]</span>
                                                            <button className="btn-circle btn-red"
                                                                onClick={() => handleDeleteAlert(metric.name, alertIndex)}
                                                            >                                                                <span>&times;</span>
                                                            </button>
                                                        </div>
                                                    ))}
                                                    {getAvailableOperators(metric.alerts).length > 0 && (
                                                        <button className="btn-circle btn-green"
                                                            onClick={() => handleEnableAlertCreator(index)}>
                                                            <span>+</span>
                                                        </button>
                                                    )
                                                    }
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                    <tr key="__addedColumn">
                                        <td>
                                            <input
                                                type="text"
                                                name="name"
                                                value={newMetric.name}
                                                onChange={handleInputChange}
                                                placeholder="Metric Name"
                                                className="form-control"
                                                style={{ width: "120px", textAlign: 'center' }}
                                            />
                                        </td>
                                        <td>
                                            <span className="label">{newMetric.type}</span>
                                        </td>
                                        <td>
                                            <input
                                                type="text"
                                                name="value"
                                                value={newMetric.value}
                                                onChange={handleInputChange}
                                                placeholder="Value"
                                                className="form-control"
                                                style={{ width: "75px", textAlign: 'center' }}
                                            />
                                        </td>
                                        <td>
                                            <button className="agent-button" onClick={handleAddMetric}>Add Metric</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        {/* Validation Error Message */}
                        {error && (
                            <div className="alert alert-danger" role="alert">
                                {error}
                            </div>
                        )}
                    </div>
                    {alertEditorEnabled && (                        
                        <MetricAlertCreator
                            metricName={metricAlertSelected}
                            availableOperators={alertOperatorsAvailable}
                            onSubmit={onAlertEditionSubmit}
                            onCancel={onAlertEditionCancel} />
                    )}
                </div>

            ) : (
                <div className="alert alert-light text-center p-3 m-3">
                    No agent selected
                </div>
            )
            }
        </div>
    );
};

export default AgentInfo;