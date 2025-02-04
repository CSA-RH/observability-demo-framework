import { useKeycloak } from "@react-keycloak/web";

const PrivateRoute = ({ roles, children }) => {
  const { keycloak } = useKeycloak();
  const userRoles = keycloak.realmAccess?.roles
  const hasRequiredRole = () => {
    if (!roles) return true; // No roles required
    return roles.some((role) => userRoles.includes(role));
  };
  const isLoggedIn = keycloak.authenticated;

  return isLoggedIn && hasRequiredRole() ? children : (<div>No Access</div>);
};

export default PrivateRoute;