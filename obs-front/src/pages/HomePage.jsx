import React from 'react';
import { useNavigate } from 'react-router-dom';

const HomePage = () => {
  const navigate = useNavigate();

  return (
    <div className="homepage-container">      
      
        <button 
          className="custom-button" 
          onClick={() => navigate('/simulation')}
        >
          Simulation
        </button>
        <button 
          className="custom-button" 
          onClick={() => navigate('/admin')}
        >
          Administration
        </button>
      
    </div>
  );
};

export default HomePage;