import React from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'

// Child component that receives data as a prop
const AgentList = ({ simulation, agent }) => {

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
    <div>
      {simulation != null && simulation.length > 0 && (
        <table style={{width: '590px'}}>
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
            {simulation.filter(item => item.group === "nodes").map((item) => (
              <tr key={item.data.id} className={agent?.data.id === item.data.id ? 'highlight' : ''}>
                <td><a href={ApiHelper.getPodLogsAddress(item.pod)} target="_blank"  rel="noopener noreferrer"> {item.data.id}</a></td>
                <td><span className='label label-nodejs'>nodejs</span></td>
                {/* Next hops mapped to labels */}
                <td>{item.data.ip ? (
                  item.nextHop && item.nextHop.map((hop, index) => (
                    <span key={index} className="label">{hop}</span>
                  ))
                ) : "n/a"}</td>
                <td>{item.data.ip ? (item.metrics ? item.metrics.length : "0") : "n/a"}</td>
                <td>{item.data.ip && <button className="agent-button" onClick={
                  () => handleKick(item.data.id, item.data.ip)}>Kick!
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
