import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ReactKeycloakProvider } from "@react-keycloak/web";
import keycloakInstance from './helpers/Keycloak';
import PrivateRoute from "./components/PrivateRoute";
import SimulationPage from './pages/SimulationPage';
import AdminPage from './pages/AdminPage';
import ClusterInfo from './components/ClusterInfo';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { LoadingProvider } from './context/LoadingContext';

const App = () => {

  const [selectedUser, setSelectedUser] = useState(null);

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
      <LoadingProvider>
        <BrowserRouter>
          <ClusterInfo
            selectedUser={selectedUser}
            setSelectedUser={setSelectedUser} />
          <Routes>
            <Route path="/admin" element={<PrivateRoute roles={["obs-admin"]}><AdminPage /></PrivateRoute>} />
            <Route
              path="/simulation"
              element={selectedUser
                ? <SimulationPage selectedUser={selectedUser} />
                : <div>Loading user data...</div>
              }
            />
            <Route path="/" element={<Navigate to="/simulation" />} />
            <Route path="*" element={<Navigate to="/simulation" />} />
          </Routes>
          <ToastContainer
            position="top-right"
            autoClose={4000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light" // o "dark"
          />
        </BrowserRouter>
      </LoadingProvider>
    </ReactKeycloakProvider>
  );
}

export default App;