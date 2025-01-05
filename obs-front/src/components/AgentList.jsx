import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'

// Child component that receives data as a prop
const AgentList = ({ agents, selectedAgentId, onAgentSelected }) => {

    const [selectedRow, setSelectedRow] = useState(selectedAgentId);
    const [toasts, setToasts] = useState([]);

    const addToast = (message) => {
        const id = Date.now();
        setToasts([...toasts, { id, message }]);

        // Remove the toast after 3 seconds
        setTimeout(() => {
            setToasts((prev) => prev.filter((toast) => toast.id !== id));
        }, 3000);
    };


    const handleRowClick = (agentId) => {
        setSelectedRow(agentId); // Set the selected row when clicked
        onAgentSelected(agents.find(a => a.id == agentId))
    };

    useEffect(() => {
        setSelectedRow(selectedAgentId)
    }, [selectedAgentId]);

    //For handling the kick
    const handleKick = async (id, ip) => {
        console.log(`${id}[${ip}] placed an order!`);
        addToast(`${id}[${ip}] placed an order!`);
        try {
            const kickPayload = {
                ip: ip,
                id: id,
                count: 4 //No tiki-taka
            }
            const response = await fetch(ApiHelper.getKickUrl(ip), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(kickPayload)
            });
            const result = await response.json();
            console.log('Success:', result);  //TODO: wat-error handling
        } catch (error) {
            console.error('Error:', error);
        }
    }

    return (
        <div>
            <div className='table-responsive'>
                {agents != null && agents.length > 0 && (
                    <table className='table w-100'>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Technology</th>
                                <th>Next hops</th>
                                <th>#Metrics / #Alerts</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {agents.map((item) => (
                                <tr key={item.id}
                                    className={`${selectedRow === item.id ? 'table-active' : ''} `}
                                    onClick={() => handleRowClick(item.id)}>

                                    <td><a href={ApiHelper.getPodLogsAddress(item.pod)} target="_blank" rel="noopener noreferrer"> {item.id}</a></td>
                                    <td><span className={'label label-' + item.type}>{item.type}</span></td>
                                    {/* Next hops mapped to labels */}
                                    <td>{item.ip ? (
                                        item.nextHop && item.nextHop.map((hop, index) => (
                                            <span key={index} className="label">{hop}</span>
                                        ))
                                    ) : "n/a"}</td>
                                    <td>{item.ip ? (item.metrics ? item.metrics.length + "/" + item.metrics.filter((c) => c.alert).length : "0") : "n/a"}</td>
                                    <td>{item.ip && item.type == "customer" && <button className="agent-button" onClick={
                                        () => handleKick(item.id, item.ip)}>Order!
                                    </button>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>)}
            </div>

            <div className="position-fixed top-0 start-0 p-3" style={{ zIndex: 1055 }}>
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className="toast show mb-2"
                        role="alert"
                        aria-live="assertive"
                        aria-atomic="true"
                    >
                        <div className="toast-header" style={{ backgroundColor: '#f2d1d1' }}>
                            <strong className="me-auto">Notification</strong>
                            <button
                                type="button"
                                className="btn-close"
                                aria-label="Close"
                                onClick={() =>
                                    setToasts((prev) => prev.filter((t) => t.id !== toast.id))
                                }
                            ></button>
                        </div>
                        <div className="toast-body">{toast.message}</div>
                    </div>
                ))}
            </div>

        </div>

    );
};

export default AgentList;
