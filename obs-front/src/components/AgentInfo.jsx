import React from 'react';

const AgentInfo = ({ agent }) => {

    return (
        <div>            
            {agent ? (
                <div>
                    <p>ID: {agent.id}</p>                   
                </div>
            ) : (
                <p>No element selected</p>
            )}
        </div>

    );
};

export default AgentInfo;