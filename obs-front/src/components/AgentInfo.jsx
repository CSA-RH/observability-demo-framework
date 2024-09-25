import React, { useState, useEffect } from 'react';

const AgentInfo = ({ agent, onAgentUpdated }) => {

    const [metrics, setMetrics] = useState(agent?.metrics || []);
    const [newMetric, setNewMetric] = useState({ name: "", type: "gauge", value: "" });
    const [error, setError] = useState("");

    useEffect(() => {
        if (agent) {          
          setMetrics(agent.metrics || []);
        }
      }, [agent]); 

    const handleMetricChange = (index, field, value) => {
        const updatedMetrics = metrics.map((metric, i) =>
            i === index ? { ...metric, [field]: value } : metric
        );
        setMetrics(updatedMetrics);
    };

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
        console.log([...metrics, newMetric]);
        agent.metrics = [...metrics, newMetric];
        //POST TO THE AGENT WITH UPDATED VALUE. 
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
        onAgentUpdated(agent)
        setMetrics(metrics);
    };

    const handleInputChange = (e) => {
        setNewMetric({
            ...newMetric,
            [e.target.name]: e.target.value,
        });
    };

    return (
        <div>
            {agent && agent?.data ? (
                <div>
                    <h3>{agent.data.id}</h3>
                    <p>IP: {agent.data.ip}</p>

                    <h4>Metrics</h4>
                    {error && <p style={{ color: "red" }}>{error}</p>} {/* Show error message if any */}

                    <table>
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
                                        {metric.name}
                                    </td>
                                    <td>
                                        {metric.type}
                                    </td>
                                    <td>
                                        <input
                                            type="text"
                                            value={metric.value}
                                            onChange={(e) => handleMetricChange(index, "value", e.target.value)}
                                        />
                                    </td>
                                    <td>
                                        <button onClick={() => handleUpdateMetric(index)}>Update</button>
                                    </td>
                                </tr>
                            ))}

                            {/* Row to add new metric */}
                            <tr>
                                <td>
                                    <input
                                        type="text"
                                        name="name"
                                        value={newMetric.name}
                                        onChange={handleInputChange}
                                        placeholder="Metric Name"
                                    />
                                </td>
                                <td>
                                    {newMetric.type}
                                </td>
                                <td>
                                    <input
                                        type="text"
                                        name="value"
                                        value={newMetric.value}
                                        onChange={handleInputChange}
                                        placeholder="Value"
                                    />
                                </td>
                                <td>
                                    <button onClick={handleAddMetric}>Add Metric</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
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