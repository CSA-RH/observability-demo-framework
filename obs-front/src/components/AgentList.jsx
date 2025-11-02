import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'
import { useKeycloak } from "@react-keycloak/web";
import { notifySuccess, notifyError } from '../services/NotificationService';

const AgentList = ({ agents, userId, selectedAgentId, onAgentSelected }) => {

    const [selectedRow, setSelectedRow] = useState(selectedAgentId);
    const { keycloak, initialized } = useKeycloak();

    const handleRowClick = (agentId) => {
        setSelectedRow(agentId); // Set the selected row when clicked
        onAgentSelected(agents.find(a => a.id == agentId))
    };

    useEffect(() => {
        setSelectedRow(selectedAgentId)
    }, [selectedAgentId]);

    //For handling the kick
    
    const handleKick = async (id, dns) => {
        const message = `${new Date().toLocaleString()} - ${id}[${dns}] placed an order!`;
        
        try {
            const kickPayload = {
                dns: dns,
                count: 4 //No tiki-taka
            }
            const response = await fetch(ApiHelper.getKickUrl(userId, id), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${keycloak.token}`
                },
                body: JSON.stringify(kickPayload)
            });
            if (response.status == 200) {
                notifySuccess(message);
            }
            else {
                const responsePayload = await response.json();
                notifyError("Error placing an order. " + responsePayload?.message)
            }
        } catch (error) {
            notifyError('Error:', error);
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
                                    <td><a href={ApiHelper.getPodLogsAddress(item.pod, userId)}
                                           target="_blank" 
                                           rel="noopener noreferrer"> {item.id} <i className="fas fa-external-link-alt"></i></a></td>
                                    <td><span className={'label label-' + item.type}>{item.type}</span></td>
                                    {/* Next hops mapped to labels */}
                                    <td>{item.ip ? (
                                        item.nextHop && item.nextHop.map((hop, index) => (
                                            <span key={index} className="label">{hop}</span>
                                        ))
                                    ) : "n/a"}</td>
                                    <td>{item.ip ? (item.metrics ? item.metrics.length + "/" + item.metrics.reduce((sum, metric) => sum + (metric.alerts?.length || 0), 0) : "0") : "n/a"}</td>
                                    <td>{item.ip && item.type == "customer" && <button className="agent-button" onClick={
                                        () => handleKick(item.id, item.dns)}>Order!
                                    </button>}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>)}
            </div>
        </div>
    );
};

export default AgentList;
