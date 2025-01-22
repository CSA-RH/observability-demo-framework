import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import PrivateRoute from "./PrivateRoute";
import { ReactKeycloakProvider, useKeycloak } from "@react-keycloak/web";
import Keycloak from "keycloak-js";
import Nav from "./Nav";

const AdminPage = () => <h1>Admin Page - Restricted Access</h1>;
const UserPage = () => <h1>User Page</h1>;
const Unauthorized = () => <h1>Unauthorized - Access Denied</h1>;

const keycloakConfig = new Keycloak({
  url: import.meta.env.VITE_KEYCLOAK_URL,
  realm: import.meta.env.VITE_KEYCLOAK_REALM,
  clientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID,
});

const App = () => {
  return (
    <ReactKeycloakProvider authClient={keycloakConfig}
      onEvent={(event, error) => {
        //console.log("Keycloak event:", event);
        console.log(event);
        if (error) console.error("Keycloak error:", error);
      }}
      onTokens={(tokens) => {
        console.log("Keycloak tokens:", tokens);      
      }}
      initOptions={{ onLoad: "login-required", checkLoginIframe: false }}
    >
      <Nav />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<h1>Public Home Page</h1>} />
          <Route path="/unauthorized" element={<Unauthorized />} />
          <Route path="/admin"
            element={<PrivateRoute roles={['admin']}> <AdminPage /></PrivateRoute>}
          />
          <Route path="/user" element={<PrivateRoute> <UserPage /></PrivateRoute>} />          
        </Routes>
      </BrowserRouter>
    </ReactKeycloakProvider>

  );
};

export default App;