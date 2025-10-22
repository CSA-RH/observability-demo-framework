import React, { useState }  from 'react';
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ReactKeycloakProvider } from "@react-keycloak/web";
import keycloakInstance from './helpers/Keycloak';
import PrivateRoute from "./components/PrivateRoute";
import SimulationPage from './pages/SimulationPage';
import AdminPage from './pages/AdminPage';
import HomePage from './pages/HomePage';
import ClusterInfo from './components/ClusterInfo';

const App = () => {
  
  const [selectedUserNamespace, setSelectedUserNamespace] = useState(null);

  const onKeycloakEvent = async (event, error) => {    
    if (event === "onAuthSuccess") {
      // Redirect to /simulation after successful login      
      if (window.location.pathname !== '/simulation' && !sessionStorage.getItem('redirected')) {
        sessionStorage.setItem('redirected', 'true'); // Store the redirect status
        window.location.href = '/simulation'; // Redirect to /simulation after successful login
      }
    } else if (event === 'onTokenExpired') {
      try {
        const refreshed = await keycloakInstance.updateToken(30); // Attempt to refresh the token if it's about to expire.
        if (!refreshed) {
          console.warn('Token refresh failed');
          keycloakInstance.logout(); // Log out if the token cannot be refreshed.
        }
      } catch (err) {
        console.error('Error refreshing token:', err);
        keycloakInstance.logout(); // Log out on any error during token refresh.
      }
    } else if (error) {
      console.error('Keycloak event error:', error);
    }
  };

  return (
    <ReactKeycloakProvider authClient={keycloakInstance}
      onEvent={onKeycloakEvent}      
      initOptions={{ onLoad: "login-required", checkLoginIframe: false }}
      LoadingComponent={<div>Loading...</div>}
    >
      <BrowserRouter>
      <ClusterInfo 
        selectedUserNamespace={selectedUserNamespace}
        setSelectedUserNamespace={setSelectedUserNamespace}/>      
        <Routes>          
          <Route path="/admin" element={<PrivateRoute roles={["obs-admin"]}><AdminPage /></PrivateRoute>} />
          <Route path="/simulation" element={<SimulationPage selectedNamespace={selectedUserNamespace} />} />
          <Route path="/" element={<Navigate to="/simulation" />} />
          <Route path="*" element={<Navigate to="/simulation" />} />
        </Routes>
      </BrowserRouter>
    </ReactKeycloakProvider>);
}

export default App;