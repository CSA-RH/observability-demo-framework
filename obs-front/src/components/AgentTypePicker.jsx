import React, { useState, useEffect } from 'react';

const AgentTypePicker = ({ nodeTypes, onSelectionChange }) => {

    const [selectedButton, setSelectedButton] = useState(0);

    const handleButtonClick = (index) => {
        setSelectedButton(index);
        onSelectionChange(index);
    }

    return (
        <div style={{ display: 'flex', gap: '10px' }}>
            {nodeTypes?.map((nodeType, index) => (
                <button
                    key={index}
                    disabled={!nodeType.enabled}
                    onClick={() => handleButtonClick(index)}
                    style={{
                        border: selectedButton === index ? '2px solid blue' : '1px solid gray',
                        padding: '5px',
                        margin: '5px',
                        background: 'none',
                        cursor: 'pointer',
                        maxWidth: '85px'
                    }}
                >
                    <img
                        src={nodeType.image}
                        alt={`Button ${index + 1}`}
                        style={{ width: '75px', height: '25px', objectFit: 'contain' }}
                    />
                </button>
            ))}
        </div>
    );
};

export default AgentTypePicker;