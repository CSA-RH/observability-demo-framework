import { useKeycloak } from "@react-keycloak/web";
import { Navigate } from 'react-router-dom';
import { hasRealmRole } from '../ApiHelper';

const PrivateRoute = ({ roles, children }) => {
  const { keycloak } = useKeycloak();
  // No roles required, or any of them (a token without realm_access has none).
  const hasRequiredRole = !roles || roles.some((role) => hasRealmRole(keycloak, role));
  return keycloak.authenticated && hasRequiredRole ? children : (<Navigate to="/" replace />);
};

export default PrivateRoute;
