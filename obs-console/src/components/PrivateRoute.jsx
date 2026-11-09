import { useKeycloak } from "@react-keycloak/web";
import { Navigate } from 'react-router-dom';

const PrivateRoute = ({ roles, children }) => {
  const { keycloak } = useKeycloak();
  const userRoles = keycloak.realmAccess?.roles
  const hasRequiredRole = () => {
    if (!roles) return true; // No roles required
    return roles.some((role) => userRoles.includes(role));
  };
  const isLoggedIn = keycloak.authenticated;

  return isLoggedIn && hasRequiredRole() ? children : (<Navigate to="/" replace />);
};

export default PrivateRoute;