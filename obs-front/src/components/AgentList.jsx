import React, { useState } from 'react';
import * as ApiHelper from '../ApiHelper'

// Child component that receives data as a prop
const AgentList = ({ simulation }) => {

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
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {simulation.filter(item => item.group == "nodes").map((item) => (
              <tr key={item.data.id}>
                <td>{item.data.id}</td>
                <td>{item.data.ip}</td>
                <td>{item.data.ip ? [item.nextHop && item.nextHop.join(", ")] : "n/a"}</td>
                <td>{item.data.ip && <button onClick={
                  () => handleKick(item.data.id, item.data.ip)}>Kick!
                </button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>)}
      <div>
        <h3>Data simulation:</h3>
        <div>
          {simulation != null && simulation.length > 0 ? (
            <pre>{JSON.stringify(simulation, null, 2)}</pre>
          ) : (
            <p>No graph elements to display</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentList;
