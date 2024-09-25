import React from 'react';
import * as ApiHelper from '../ApiHelper'
import '../App.css'

// Child component that receives data as a prop
const AgentList = ({ simulation, agent}) => {

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
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Cluster IP</th>
              <th>Next hops</th>
              <th>#Metrics</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {simulation.filter(item => item.group === "nodes").map((item) => (
              <tr key={item.data.id} className={agent?.data.id === item.data.id ? 'highlight' : ''}>
                <td>{item.data.id}</td>
                <td>{item.data.ip}</td>
                <td>{item.data.ip ? [item.nextHop && item.nextHop.join(", ")] : "n/a"}</td>
                <td>{item.data.ip ? (item.data?.metrics ? item.data.metrics.count: "0") : "n/a"}</td>
                <td>{item.data.ip && <button onClick={
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
