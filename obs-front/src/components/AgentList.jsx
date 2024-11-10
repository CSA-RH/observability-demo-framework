import React, { useState, useEffect } from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'

// Child component that receives data as a prop
const AgentList = ({ agents, selectedAgentId, onAgentSelected }) => {
    
    const [selectedRow, setSelectedRow] = useState(selectedAgentId);

    const handleRowClick = (agentId) => {
        setSelectedRow(agentId); // Set the selected row when clicked
        onAgentSelected(agents.find(a => a.id==agentId))
    };
    
    useEffect(() => {    
        setSelectedRow(selectedAgentId)
      }, [selectedAgentId]);

    //For handling the kick
    const handleKick = async (id, ip) => {
        console.log(`${id}[${ip}] kicked the ball!`);
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
        <div className='table-responsive'>
            {agents != null && agents.length > 0 && (
                <table className='table w-100'>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Technology</th>
                            <th>Next hops</th>
                            <th>#Metrics</th>
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
                                <td>{item.ip ? (item.metrics ? item.metrics.length : "0") : "n/a"}</td>
                                <td>{item.ip && <button className="agent-button" onClick={
                                    () => handleKick(item.id, item.ip)}>Kick!
                                </button>}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>)}
        </div>
    );
};

export default AgentList;
