import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper.js'

const AgentInfo = ({ agent, onAgentUpdated }) => {

    const [metrics, setMetrics] = useState(agent?.metrics || []);
    const [newMetric, setNewMetric] = useState({ name: "", type: "gauge", value: "" });
    const [error, setError] = useState("");

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
            id: agent.data.id,
            ip: agent.data.ip,
            metric: metric
        }
        console.log(method);
        console.log(payload);
        console.log("-------")
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
        //POST TO THE AGENT WITH UPDATED VALUE. 
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
        //PATCH TO THE AGENT WITH THE NEW METRIC. 
        setMetricInOpenShift("PATCH", agent, metrics[index])
        onAgentUpdated(agent)
        setMetrics(metrics);
    };

    const handleInputChange = (e) => {
        setNewMetric({
            ...newMetric,
            [e.target.name]: e.target.value,
        });
    };

    //console.log(agent)
    console.log(metrics)

    return (
        <div className='container-agent'>
            {agent && agent?.data ? (
                <div>
                    <h3>{agent.data.id}</h3>
                    <div className="key-value-pair">
                        <span className="key">IP:</span>
                        <span className="value">{agent.data.ip}</span>
                    </div>
                    <div className="key-value-pair">
                        <span className="key">Pod:</span>
                        <span className="value"><a href={ApiHelper.globalRootConsole + '/k8s/ns/' + ApiHelper.globalCurrentNamespace + '/pods/' + agent.pod} target="_blank" rel="noopener noreferrer">{agent.pod}</a></span>
                    </div>
                    <div style={{ padding: '15px' }}>

                        <h4>Metrics</h4>
                        {error && <p style={{ color: "red" }}>{error}</p>} {/* Show error message if any */}
                        <div style={{ justifyContent: 'center', display: 'flex' }}>
                            <table style={{ width: '370px', border: '0px' }}>
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Type</th>
                                        <th>Value</th>
                                        <th>Actions</th>
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