import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper.js'
import MetricAlertCreator from './MetricAlertCreator.jsx';

const AgentInfo = ({ agent, onAgentUpdated }) => {

    const [metrics, setMetrics] = useState(agent?.metrics || []);
    const [newMetric, setNewMetric] = useState({ name: "", type: "gauge", value: "" });
    const [error, setError] = useState("");
    const [alertEditorEnabled, setAlertEditorEnabled] = useState(false);
    const [metricAlertSelected, setMetricAlertSelected] = useState("")

    useEffect(() => {
        if (agent) {
            setMetrics(agent.metrics || []);
        }
        else {
            setMetrics([])
        }


    }, [agent]);

    const handleMetricChange = (index, field, value) => {
        const updatedMetrics = metrics.map((metric, i) =>
            i === index ? { ...metric, [field]: value } : metric
        );
        setMetrics(updatedMetrics);
    };

    async function setMetricInOpenShift(method, agent, metric) {
        const payload = {
            id: agent.id,
            ip: agent.ip,
            metric: metric
        }
        console.log("**Payload:", payload);
        console.log("**Agent:", agent);
        console.log("**Metric:", metric);

        try {
            const response = await fetch(ApiHelper.getAgentsMetricsUrl(), {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload),
            });
            const result = await response.json();
            console.log(`Set metric ${metric.name} for the agent ${payload.id}`);
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async function setAlertInCluster(agent, metricObject) {
        console.log("Agent: ", agent);
        console.log("Metric: ", metricObject)
        try {
            const response = await fetch(ApiHelper.getClusterAlertDefinitionUrl(), {
                method: "POST", 
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: agent.id, 
                    agent_type: agent.type,
                    metric: metricObject
                })});
            const result = await response.json();
            console.log(`Set alert for the metric ${metricObject.name}`);
        } catch (error) {
            console.error('Error:', error);
        }
        
                    
        
    }

    const handleAddMetric = () => {
        // Validation: Name cannot be empty, must be unique, and value cannot be empty
        if (newMetric.name.trim() === "") {
            setError("Metric name cannot be empty.");
            return;
        }
        if (metrics.some(metric => metric.name === newMetric.name)) {
            setError("Metric name must be unique.");
            return;
        }
        if (newMetric.value.trim() === "") {
            setError("Metric value cannot be empty.");
            return;
        }

        // Clear error and add new metric
        setError("");
        setMetrics([...metrics, newMetric]);
        agent.metrics = [...metrics, newMetric];
        //POST TO THE AGENT WITH NEW VALUE. 
        setMetricInOpenShift("POST", agent, newMetric)
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
        setMetricInOpenShift("PUT", agent, metrics[index])
        onAgentUpdated(agent)
        setMetrics(metrics);
    };

    const handleInputChange = (e) => {
        setNewMetric({
            ...newMetric,
            [e.target.name]: e.target.value,
        });
    };

    const handleEnableAlertCreator = (index) => {
        setAlertEditorEnabled(true);
        setMetricAlertSelected(metrics[index].name);
    }

    const onAlertEditionCancel = (e) => {
        setAlertEditorEnabled(false);
    }

    const onAlertEditionSubmit = (metric, expression, value, severity) => {
        const alert = { expression: expression, severity: severity, value: value };
        const metricObject = agent.metrics.find((m) => m.name == metric);
        metricObject['alert'] = alert;
        //Update alert definition in definition 
        setMetricInOpenShift("PUT", agent, metricObject)
        onAgentUpdated(agent);
        //Create rule in cluster
        setAlertInCluster(agent, metricObject)
        console.log("Added new alert to Agent: ", agent.id, "Metric: ", metric, "Alert", alert);
        setAlertEditorEnabled(false);
    }

    return (
        <div className='container'>
            {agent?.id ? (
                <div>
                    <h5>
                        <span className="value">
                            <a href={ApiHelper.globalRootConsole + '/k8s/ns/' + ApiHelper.globalCurrentNamespace + '/pods/' + agent.pod} target="_blank" rel="noopener noreferrer">{agent.pod}</a>
                        </span> <span className="value">[{agent.ip}] metrics</span>
                    </h5>
                    <div>
                        {error && <p style={{ color: "red" }}>{error}</p>} {/* Show error message if any */}
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
                                        <tr key={index}>
                                            <td>
                                                <span key={index} className="label">{metric.name}</span>
                                            </td>
                                            <td>
                                                <span key={index} className="label">{metric.type || "gauge"}</span> {/* TODO: Gnapa fix */}

                                            </td>
                                            <td>
                                                <input
                                                    type="text"
                                                    value={metric.value}
                                                    onChange={(e) => handleMetricChange(index, "value", e.target.value)}
                                                    style={{ width: "75px", textAlign: 'center' }}
                                                />
                                            </td>
                                            <td>
                                                <button className="agent-button" onClick={() => handleUpdateMetric(index)}>Update</button>
                                            </td>
                                            <td>
                                                {!metric.alert ?
                                                    <button className="agent-button" onClick={() => handleEnableAlertCreator(index)}>Define Alert</button>
                                                    :
                                                    <div className={"label label-" + metric.alert.severity.toLowerCase()}>
                                                        <span>{metric.alert.expression}</span>
                                                        <span>{metric.alert.value}</span>
                                                        <span>[{metric.alert.severity}]</span>
                                                    </div>
                                                }
                                            </td>
                                        </tr>
                                    ))}

                                    <tr>
                                        <td>
                                            <input
                                                type="text"
                                                name="name"
                                                value={newMetric.name}
                                                onChange={handleInputChange}
                                                placeholder="Metric Name"
                                                style={{ width: "120px", textAlign: 'center', margin: '5px' }}
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
                    </div>
                    {alertEditorEnabled && (
                        <MetricAlertCreator
                            metricName={metricAlertSelected}
                            onSubmit={onAlertEditionSubmit}
                            onCancel={onAlertEditionCancel} />
                    )}
                </div>

            ) : (
                <div>
                    No agent selected
                </div>
            )
            }
        </div>
    );
};

export default AgentInfo;